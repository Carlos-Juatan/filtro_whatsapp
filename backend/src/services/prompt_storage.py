import json
import os
from pathlib import Path
from typing import List, Optional

from src.models.schemas import ModeloOpenAI, PromptConfig, PromptConfigCreate, TipoFerramenta, TipoPrompt

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
    "Além disso, identifique e extraia fatos úteis, regras de negócio, preços, horários e informações "
    "relevantes que NÃO estejam estruturadas na forma de pergunta e resposta, mas que sirvam para "
    "enriquecer uma base de conhecimento. "
    "Retorne SOMENTE um objeto JSON válido com as chaves 'qna_pairs' e 'uncategorized_database_content', "
    "sem nenhum texto adicional. "
    "Cada item em 'qna_pairs' deve ter os campos: "
    "'question' (string com a pergunta do cliente), 'answer' (string com a resposta do suporte), "
    "'frequency' (integer, mínimo 1), "
    "'metadata' (string com categoria da dúvida), 'category' (string 'FAQ' por padrão). "
    "O campo 'uncategorized_database_content' deve ser uma lista de strings, onde cada string é uma "
    "afirmação ou fato útil extraído da conversa (uma afirmação por item)."
)

# ──────────────────────────────────────────────────────────────────────────────
# Default system prompt text for the Question Generator (003-gerador-perguntas)
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_GENERATOR_PROMPT_TEXT = (
    "Você é um especialista em geração de bases de conhecimento e perguntas de FAQ. "
    "Sua tarefa é analisar o conteúdo declarativo, fatos, regras de negócio ou instruções "
    "fornecidas e gerar uma pergunta pertinente para cada fato útil encontrado. "
    "A afirmação original contendo o fato deve ser tratada como a resposta correta e associada "
    "à pergunta gerada. "
    "Regras de Geração: "
    "1. Extraia afirmações factuais e claras e crie perguntas diretas para elas. "
    "2. Cada item gerado deve ser mapeado em um par contendo 'question' (a pergunta formulada) e "
    "'answer' (a afirmação/fato original correspondente). "
    "3. Classifique cada par em uma categoria temática lógica (ex: 'Financeiro', 'Horários', 'Serviços') "
    "e retorne no campo 'metadata'. "
    "4. Defina o campo 'category' como 'FAQ' por padrão para todos os itens. "
    "5. Ignore frases soltas ou sem sentido coerente (ex: 'ok', 'teste', 'olá'). "
    "6. Retorne SOMENTE um objeto JSON válido com a chave 'qna_pairs', sem nenhum texto adicional "
    "ou markdown de bloco de código. "
    "Estrutura JSON esperada: "
    '{"qna_pairs": [{"question": "Pergunta formulada a partir do fato", "answer": "Fato ou afirmação declarativa original na íntegra", "frequency": 1, "metadata": "Categoria temática do fato", "category": "FAQ"}]}'
)

# ──────────────────────────────────────────────────────────────────────────────
# Default system prompt text for the Consolidador (005-separate-tool-prompts)
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_CONSOLIDATOR_PROMPT_TEXT = (
    "Você é um especialista em consolidação e deduplicação de bases de conhecimento de P&R. "
    "Sua tarefa é receber uma lista de pares de perguntas e respostas extraídas de diferentes fontes "
    "e consolidá-los em um conjunto único e coerente, eliminando duplicatas e agrupando semânticas similares. "
    "Regras de Consolidação: "
    "1. Identifique perguntas semanticamente equivalentes e agrupe-as sob uma pergunta padronizada única. "
    "2. Consolide as respostas correspondentes em uma resposta abrangente e precisa. "
    "3. Some as frequências dos itens agrupados para refletir a relevância total. "
    "4. Mantenha ou melhore a categorização temática dos pares consolidados. "
    "5. Elimine informações redundantes ou conflitantes, priorizando a resposta mais completa e precisa. "
    "6. Retorne SOMENTE um objeto JSON válido com a chave 'qna_pairs', sem nenhum texto adicional "
    "ou markdown de bloco de código. "
    "Estrutura JSON esperada: "
    '{"qna_pairs": [{"question": "Pergunta padronizada consolidada", "answer": "Resposta consolidada e abrangente", "frequency": 3, "metadata": "Categoria temática", "category": "FAQ"}]}'
)

# Fixed UUIDs for built-in default prompts — stable across restarts
_DEFAULT_PROMPT_ID = "00000000-0000-0000-0000-000000000001"
_DEFAULT_GENERATOR_PROMPT_ID = "00000000-0000-0000-0000-000000000002"
_DEFAULT_CONSOLIDATOR_PROMPT_ID = "00000000-0000-0000-0000-000000000003"

# Set of all protected system prompt IDs (cannot be deleted)
_PROTECTED_PROMPT_IDS = {_DEFAULT_PROMPT_ID, _DEFAULT_GENERATOR_PROMPT_ID, _DEFAULT_CONSOLIDATOR_PROMPT_ID}


class PromptStorageService:
    def __init__(self):
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROMPTS_FILE.exists():
            with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        prompts = self._read_raw()
        prompts = self._migrate_ferramenta_field(prompts)
        prompts = self._ensure_extrator_default(prompts)
        prompts = self._ensure_generator_default(prompts)
        prompts = self._ensure_consolidator_default(prompts)
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)

    def _migrate_ferramenta_field(self, prompts: list) -> list:
        """In-memory migration: add ferramenta='extrator' to any prompt missing the field."""
        changed = False
        for p in prompts:
            if "ferramenta" not in p:
                p["ferramenta"] = TipoFerramenta.EXTRATOR.value
                changed = True
        if changed:
            pass  # caller handles the write
        return prompts

    def _ensure_extrator_default(self, prompts: list) -> list:
        """Guarantee the built-in 'Padrão do Sistema' (extrator) prompt always exists."""
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
                ferramenta=TipoFerramenta.EXTRATOR,
            )
            prompts.insert(0, default_prompt.model_dump())
        return prompts

    def _ensure_generator_default(self, prompts: list) -> list:
        """Guarantee the built-in 'Gerador de Perguntas Padrão' prompt always exists."""
        exists = any(p.get("id") == _DEFAULT_GENERATOR_PROMPT_ID for p in prompts)
        if not exists:
            generator_prompt = PromptConfig(
                id=_DEFAULT_GENERATOR_PROMPT_ID,
                nome="Gerador de Perguntas Padrão",
                tipo=TipoPrompt.FIXO,
                textoInstrucao=DEFAULT_GENERATOR_PROMPT_TEXT,
                palavrasChave=[],
                idiomaModelo="pt-br",
                modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
                ferramenta=TipoFerramenta.GERADOR,
            )
            prompts.append(generator_prompt.model_dump())
        return prompts

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

    def _ensure_consolidator_default(self, prompts: list) -> list:
        """Guarantee the built-in 'Consolidador de P&R Padrão' prompt always exists."""
        exists = any(p.get("id") == _DEFAULT_CONSOLIDATOR_PROMPT_ID for p in prompts)
        if not exists:
            consolidator_prompt = PromptConfig(
                id=_DEFAULT_CONSOLIDATOR_PROMPT_ID,
                nome="Consolidador de P&R Padrão",
                tipo=TipoPrompt.FIXO,
                textoInstrucao=DEFAULT_CONSOLIDATOR_PROMPT_TEXT,
                palavrasChave=[],
                idiomaModelo="pt-br",
                modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
                ferramenta=TipoFerramenta.CONSOLIDADOR,
            )
            prompts.append(consolidator_prompt.model_dump())
        return prompts

    def get_default_prompt_text(self, ferramenta: Optional[TipoFerramenta] = None) -> str:
        """Return the raw text of the default system prompt for UI pre-filling.

        Args:
            ferramenta: Optional tool filter. Returns the default prompt text for the
                        specified tool. Defaults to EXTRATOR for backward compatibility.
        """
        if ferramenta == TipoFerramenta.GERADOR:
            return DEFAULT_GENERATOR_PROMPT_TEXT
        if ferramenta == TipoFerramenta.CONSOLIDADOR:
            return DEFAULT_CONSOLIDATOR_PROMPT_TEXT
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
            ValueError: If attempting to delete any built-in system prompt.
        """
        if prompt_id in _PROTECTED_PROMPT_IDS:
            raise ValueError("O prompt padrão do sistema não pode ser excluído.")

        prompts = self._read_prompts()
        original_len = len(prompts)
        prompts = [p for p in prompts if p.id != prompt_id]
        if len(prompts) == original_len:
            return False
        self._write_prompts(prompts)
        return True


prompt_storage = PromptStorageService()
