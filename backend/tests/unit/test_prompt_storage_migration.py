"""
Unit tests for PromptStorageService migration logic.

Covers:
- T020: CONSOLIDADOR default prompt is seeded on startup
- _ensure_consolidador_default idempotency (no duplicates on repeated calls)
- CONSOLIDADOR prompt ID is protected (cannot be deleted)
- ferramenta field migration still adds 'extrator' to legacy prompts
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch


@pytest.fixture()
def isolated_storage(tmp_path):
    """
    Provides a PromptStorageService instance backed by a fresh temp directory.
    Patches DATA_DIR and PROMPTS_FILE so the real data file is not touched.
    """
    import src.services.prompt_storage as ps_module

    orig_data_dir = ps_module.DATA_DIR
    orig_prompts_file = ps_module.PROMPTS_FILE

    temp_data = tmp_path / "data"
    temp_data.mkdir()
    temp_prompts = temp_data / "prompts.json"

    ps_module.DATA_DIR = temp_data
    ps_module.PROMPTS_FILE = temp_prompts

    from src.services.prompt_storage import PromptStorageService
    service = PromptStorageService()

    yield service

    # Restore originals
    ps_module.DATA_DIR = orig_data_dir
    ps_module.PROMPTS_FILE = orig_prompts_file


# ──────────────────────────────────────────────────────────────────────────────
# T020: CONSOLIDADOR seeding tests
# ──────────────────────────────────────────────────────────────────────────────

def test_consolidador_default_prompt_is_seeded(isolated_storage):
    """CONSOLIDADOR default prompt must be present after storage initialisation."""
    from src.models.schemas import TipoFerramenta
    prompts = isolated_storage.get_all()
    consolidador_prompts = [p for p in prompts if p.ferramenta == TipoFerramenta.CONSOLIDADOR]
    assert len(consolidador_prompts) == 1, (
        "Exactly one CONSOLIDADOR default prompt should be seeded."
    )


def test_consolidador_default_prompt_has_fixed_id(isolated_storage):
    """CONSOLIDADOR prompt must use the stable UUID 00000000-0000-0000-0000-000000000003."""
    from src.services.prompt_storage import _DEFAULT_CONSOLIDADOR_PROMPT_ID
    prompts = isolated_storage.get_all()
    ids = [p.id for p in prompts]
    assert _DEFAULT_CONSOLIDADOR_PROMPT_ID in ids, (
        f"Expected fixed ID {_DEFAULT_CONSOLIDADOR_PROMPT_ID} to be present in prompt list."
    )


def test_consolidador_seeding_is_idempotent(isolated_storage):
    """Calling _ensure_consolidador_default twice must not create duplicate prompts."""
    import src.services.prompt_storage as ps_module
    raw = isolated_storage._read_raw()
    raw_after = isolated_storage._ensure_consolidador_default(raw)
    raw_after = isolated_storage._ensure_consolidador_default(raw_after)  # second call
    from src.services.prompt_storage import _DEFAULT_CONSOLIDADOR_PROMPT_ID
    count = sum(1 for p in raw_after if p.get("id") == _DEFAULT_CONSOLIDADOR_PROMPT_ID)
    assert count == 1, "Seeding twice must not create duplicate CONSOLIDADOR prompts."


def test_consolidador_prompt_is_protected(isolated_storage):
    """Attempting to delete the CONSOLIDADOR system prompt must raise ValueError."""
    from src.services.prompt_storage import _DEFAULT_CONSOLIDADOR_PROMPT_ID
    with pytest.raises(ValueError, match="padrão do sistema"):
        isolated_storage.delete(_DEFAULT_CONSOLIDADOR_PROMPT_ID)


def test_consolidador_prompt_text_is_non_empty(isolated_storage):
    """The CONSOLIDADOR prompt textoInstrucao must be a non-empty string."""
    from src.services.prompt_storage import _DEFAULT_CONSOLIDADOR_PROMPT_ID
    prompt = isolated_storage.get_by_id(_DEFAULT_CONSOLIDADOR_PROMPT_ID)
    assert prompt is not None
    assert prompt.textoInstrucao is not None
    assert len(prompt.textoInstrucao) > 50, "CONSOLIDADOR prompt text must be substantive."


def test_all_three_default_prompts_are_seeded(isolated_storage):
    """Extrator, Gerador, and Consolidador defaults must all be present after init."""
    from src.models.schemas import TipoFerramenta
    prompts = isolated_storage.get_all()
    ferramentas = {p.ferramenta for p in prompts}
    assert TipoFerramenta.EXTRATOR in ferramentas
    assert TipoFerramenta.GERADOR in ferramentas
    assert TipoFerramenta.CONSOLIDADOR in ferramentas


# ──────────────────────────────────────────────────────────────────────────────
# Legacy migration: ferramenta field backfill
# ──────────────────────────────────────────────────────────────────────────────

def test_ferramenta_migration_adds_extrator_to_legacy_prompts(isolated_storage):
    """Legacy prompts without 'ferramenta' field must be migrated to 'extrator'."""
    legacy = [
        {
            "id": "legacy-001",
            "nome": "Old Prompt",
            "tipo": "CUSTOMIZADO",
            "textoInstrucao": "Extraia perguntas e respostas.",
            "palavrasChave": [],
            "idiomaModelo": "pt-br",
            "modeloOpenAI": "gpt-4o-mini",
        }
    ]
    migrated = isolated_storage._migrate_ferramenta_field(legacy)
    assert migrated[0]["ferramenta"] == "extrator", (
        "Legacy prompts must have ferramenta backfilled to 'extrator'."
    )
