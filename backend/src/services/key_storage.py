import json
import os
from pathlib import Path
from typing import List, Optional

from src.models.schemas import ChaveAPI, ChaveAPICreate

# Try to get data directory from env, default to local 'data' dir.
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
KEYS_FILE = DATA_DIR / "keys.json"

class KeyStorageService:
    def __init__(self):
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not KEYS_FILE.exists():
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _read_keys(self) -> List[ChaveAPI]:
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [ChaveAPI.model_validate(item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_keys(self, keys: List[ChaveAPI]):
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            # Output dict, convert models
            json.dump([key.model_dump() for key in keys], f, indent=2, ensure_ascii=False)

    def get_all(self) -> List[ChaveAPI]:
        return self._read_keys()

    def get_by_id(self, key_id: str) -> Optional[ChaveAPI]:
        keys = self._read_keys()
        for key in keys:
            if key.id == key_id:
                return key
        return None

    def add(self, key_create: ChaveAPICreate) -> ChaveAPI:
        keys = self._read_keys()
        
        # Check for unique name constraint
        for k in keys:
            if k.nomeIdentificacao.lower() == key_create.nomeIdentificacao.lower():
                raise ValueError(f"Key with name '{key_create.nomeIdentificacao}' already exists.")

        new_key = ChaveAPI(**key_create.model_dump())
        keys.append(new_key)
        self._write_keys(keys)
        return new_key

    def delete(self, key_id: str) -> bool:
        keys = self._read_keys()
        new_keys = [k for k in keys if k.id != key_id]
        if len(keys) == len(new_keys):
            return False
        self._write_keys(new_keys)
        return True

key_storage = KeyStorageService()
