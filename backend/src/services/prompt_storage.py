import json
import os
from pathlib import Path
from typing import List, Optional

from src.models.schemas import PromptConfig, PromptConfigCreate, TipoPrompt

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PROMPTS_FILE = DATA_DIR / "prompts.json"

class PromptStorageService:
    def __init__(self):
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROMPTS_FILE.exists():
            with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read_prompts(self) -> List[PromptConfig]:
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [PromptConfig.model_validate(item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
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

prompt_storage = PromptStorageService()
