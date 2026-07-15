import json
import os
from pathlib import Path
from typing import List, Optional

from src.models.schemas import ModeloOpenAI, PromptConfig, PromptConfigCreate, TipoPrompt

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PROMPTS_FILE = DATA_DIR / "prompts.json"

# ──────────────────────────────────────────────────────────────────────────────
# Default system prompt text (mirrors openai_client._DEFAULT_SYSTEM_PROMPT)
# Exposed here so the API can return it to the frontend for pre-filling.
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT_TEXT = (
    "Você é um especialista em extração e análise de conversas de atendimento ao cliente. "
    "Sua tarefa é identificar TODAS as perguntas feitas pelos clientes e suas respectivas respostas "
    "dadas pelo suporte no texto de conversa fornecido (exportado do WhatsApp). "
    "Ignore mensagens do sistema, notificações de grupo, arquivos não revelados e mensagens eliminadas. "
    "Foque em pares onde um participante faz uma pergunta ou relata um problema e outro responde com "
    "uma solução, explicação ou encaminhamento. "
    "Retorne SOMENTE um objeto JSON válido com a chave 'qna_pairs', sem nenhum texto adicional. "
    "Cada item em 'qna_pairs' deve ter os campos: "
    "'question' (string com a pergunta do cliente), 'answer' (string com a resposta do suporte), "
    "'frequency' (integer, mínimo 1), "
    "'metadata' (string com categoria da dúvida), 'category' (string 'FAQ' por padrão)."
)

# Fixed UUID for the built-in default prompt — stable across restarts
_DEFAULT_PROMPT_ID = "00000000-0000-0000-0000-000000000001"


class PromptStorageService:
    def __init__(self):
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROMPTS_FILE.exists():
            with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        self._ensure_default_prompt()

    def _ensure_default_prompt(self):
        """Guarantee the built-in 'Padrão do Sistema' prompt always exists."""
        prompts = self._read_raw()
        exists = any(p.get("id") == _DEFAULT_PROMPT_ID for p in prompts)
        if not exists:
            default_prompt = PromptConfig(
                id=_DEFAULT_PROMPT_ID,
                nome="Padrão do Sistema",
                tipo=TipoPrompt.FIXO,
                textoInstrucao=DEFAULT_SYSTEM_PROMPT_TEXT,
                palavrasChave=[],
                idiomaModelo="pt-br",
                modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
            )
            # Prepend so it always appears first
            prompts.insert(0, default_prompt.model_dump())
            with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=2, ensure_ascii=False)

    def _read_raw(self) -> list:
        """Read raw JSON list without Pydantic validation."""
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _read_prompts(self) -> List[PromptConfig]:
        try:
            data = self._read_raw()
            return [PromptConfig.model_validate(item) for item in data]
        except Exception:
            return []

    def _write_prompts(self, prompts: List[PromptConfig]):
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump([prompt.model_dump() for prompt in prompts], f, indent=2, ensure_ascii=False)

    def get_all(self) -> List[PromptConfig]:
        return self._read_prompts()

    def get_by_id(self, prompt_id: str) -> Optional[PromptConfig]:
        prompts = self._read_prompts()
        for prompt in prompts:
            if prompt.id == prompt_id:
                return prompt
        return None

    def get_default_prompt_text(self) -> str:
        """Return the raw text of the default system prompt for UI pre-filling."""
        return DEFAULT_SYSTEM_PROMPT_TEXT

    def add(self, prompt_create: PromptConfigCreate) -> PromptConfig:
        if prompt_create.tipo == TipoPrompt.CUSTOMIZADO and not prompt_create.textoInstrucao:
            raise ValueError("textoInstrucao is required for CUSTOMIZADO prompts.")

        prompts = self._read_prompts()

        # Check for unique name constraint
        for p in prompts:
            if p.nome.lower() == prompt_create.nome.lower():
                raise ValueError(f"Prompt with name '{prompt_create.nome}' already exists.")

        new_prompt = PromptConfig(**prompt_create.model_dump())
        prompts.append(new_prompt)
        self._write_prompts(prompts)
        return new_prompt

    def delete(self, prompt_id: str) -> bool:
        """Delete a prompt by ID. Returns True if deleted, False if not found.

        Raises:
            ValueError: If attempting to delete the built-in default prompt.
        """
        if prompt_id == _DEFAULT_PROMPT_ID:
            raise ValueError("O prompt padrão do sistema não pode ser excluído.")

        prompts = self._read_prompts()
        original_len = len(prompts)
        prompts = [p for p in prompts if p.id != prompt_id]
        if len(prompts) == original_len:
            return False
        self._write_prompts(prompts)
        return True


prompt_storage = PromptStorageService()
