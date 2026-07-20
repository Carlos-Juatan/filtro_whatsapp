"""
Tests for PromptStorageService migration and tool-specific filtering.

Covers:
  - Backward-compat migration: legacy prompts without 'ferramenta' get 'extrator'.
  - Dual default seeding: both extrator and gerador defaults are seeded on init.
  - Tool filtering via get_all() + the ferramenta field.
  - Deletion guard: both protected IDs (_DEFAULT_PROMPT_ID, _DEFAULT_GENERATOR_PROMPT_ID).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.schemas import ModeloOpenAI, PromptConfigCreate, TipoFerramenta, TipoPrompt
from src.services.prompt_storage import (
    PromptStorageService,
    _DEFAULT_GENERATOR_PROMPT_ID,
    _DEFAULT_PROMPT_ID,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def make_storage(tmpdir: str, initial_data: list | None = None) -> PromptStorageService:
    """
    Instantiate a PromptStorageService backed by a temp directory.
    If `initial_data` is provided, write it to prompts.json before initialising
    the service (simulates an existing file from a previous version).
    """
    tmp_path = Path(tmpdir)
    prompts_file = tmp_path / "prompts.json"

    if initial_data is not None:
        prompts_file.write_text(json.dumps(initial_data, ensure_ascii=False), encoding="utf-8")

    with (
        patch("src.services.prompt_storage.DATA_DIR", tmp_path),
        patch("src.services.prompt_storage.PROMPTS_FILE", prompts_file),
    ):
        service = PromptStorageService()
        # Yield the service while patches are still active so subsequent calls work
        return service, tmp_path, prompts_file


@pytest.fixture
def empty_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        service, tmp_path, prompts_file = make_storage(tmpdir)
        with (
            patch("src.services.prompt_storage.DATA_DIR", tmp_path),
            patch("src.services.prompt_storage.PROMPTS_FILE", prompts_file),
        ):
            yield service


@pytest.fixture
def legacy_storage():
    """Storage initialised from a prompts.json file WITHOUT the 'ferramenta' field."""
    legacy_data = [
        {
            "id": "legacy-id-001",
            "nome": "Prompt Legado",
            "tipo": "CUSTOMIZADO",
            "textoInstrucao": "Extrai perguntas e respostas do texto de conversa.",
            "palavrasChave": [],
            "idiomaModelo": "pt-br",
            "modeloOpenAI": "gpt-4o-mini",
            # 'ferramenta' field intentionally absent
        }
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        service, tmp_path, prompts_file = make_storage(tmpdir, initial_data=legacy_data)
        with (
            patch("src.services.prompt_storage.DATA_DIR", tmp_path),
            patch("src.services.prompt_storage.PROMPTS_FILE", prompts_file),
        ):
            yield service, prompts_file


# ─────────────────────────────────────────────────────────────────────────────
# Migration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFeramentaMigration:
    def test_legacy_prompt_gets_extrator_ferramenta(self, legacy_storage):
        """Prompts without 'ferramenta' must be migrated to TipoFerramenta.EXTRATOR."""
        service, prompts_file = legacy_storage
        prompts = service.get_all()

        legacy = next((p for p in prompts if p.id == "legacy-id-001"), None)
        assert legacy is not None, "Legacy prompt should still be present after migration"
        assert legacy.ferramenta == TipoFerramenta.EXTRATOR

    def test_migration_persisted_to_disk(self, legacy_storage):
        """Migration result must be written back to the JSON file on disk."""
        service, prompts_file = legacy_storage
        raw = json.loads(prompts_file.read_text(encoding="utf-8"))
        legacy_raw = next((p for p in raw if p["id"] == "legacy-id-001"), None)
        assert legacy_raw is not None
        assert legacy_raw["ferramenta"] == "extrator"

    def test_migration_is_idempotent(self, legacy_storage):
        """Re-reading an already-migrated file must not duplicate or alter prompts."""
        service, prompts_file = legacy_storage
        prompts_before = service.get_all()

        # Reload service from same file to simulate a restart
        with (
            patch("src.services.prompt_storage.DATA_DIR", prompts_file.parent),
            patch("src.services.prompt_storage.PROMPTS_FILE", prompts_file),
        ):
            service2 = PromptStorageService()
            prompts_after = service2.get_all()

        # IDs should be identical (no duplicates)
        ids_before = {p.id for p in prompts_before}
        ids_after = {p.id for p in prompts_after}
        assert ids_before == ids_after


# ─────────────────────────────────────────────────────────────────────────────
# Default Seeding Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDefaultSeeding:
    def test_extrator_default_seeded(self, empty_storage):
        """'Padrão do Sistema' prompt (extrator) must be seeded on fresh init."""
        prompts = empty_storage.get_all()
        extrator_default = next((p for p in prompts if p.id == _DEFAULT_PROMPT_ID), None)
        assert extrator_default is not None
        assert extrator_default.ferramenta == TipoFerramenta.EXTRATOR
        assert extrator_default.tipo == TipoPrompt.FIXO

    def test_generator_default_seeded(self, empty_storage):
        """'Gerador de Perguntas Padrão' prompt must be seeded on fresh init."""
        prompts = empty_storage.get_all()
        generator_default = next(
            (p for p in prompts if p.id == _DEFAULT_GENERATOR_PROMPT_ID), None
        )
        assert generator_default is not None
        assert generator_default.ferramenta == TipoFerramenta.GERADOR
        assert generator_default.tipo == TipoPrompt.FIXO

    def test_both_defaults_have_distinct_ferramentas(self, empty_storage):
        """The two defaults must have distinct ferramenta values."""
        prompts = empty_storage.get_all()
        default_ferramentas = {
            p.ferramenta
            for p in prompts
            if p.id in {_DEFAULT_PROMPT_ID, _DEFAULT_GENERATOR_PROMPT_ID}
        }
        assert TipoFerramenta.EXTRATOR in default_ferramentas
        assert TipoFerramenta.GERADOR in default_ferramentas


# ─────────────────────────────────────────────────────────────────────────────
# Filtering Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFeramentaFiltering:
    def test_get_all_returns_both_tools(self, empty_storage):
        """get_all() with no filter must return prompts from both tools."""
        prompts = empty_storage.get_all()
        ferramentas = {p.ferramenta for p in prompts}
        assert TipoFerramenta.EXTRATOR in ferramentas
        assert TipoFerramenta.GERADOR in ferramentas

    def test_filter_extrator_excludes_gerador(self, empty_storage):
        """get_all() filtered by EXTRATOR must not include GERADOR prompts."""
        # Add a user-created extrator prompt
        empty_storage.add(
            PromptConfigCreate(
                nome="Custom Extrator Prompt",
                textoInstrucao="Extrai perguntas e respostas do texto fornecido.",
                ferramenta=TipoFerramenta.EXTRATOR,
            )
        )

        all_prompts = empty_storage.get_all()
        extrator_prompts = [p for p in all_prompts if p.ferramenta == TipoFerramenta.EXTRATOR]
        assert all(p.ferramenta == TipoFerramenta.EXTRATOR for p in extrator_prompts)
        assert len(extrator_prompts) >= 1  # at least the default + user custom

    def test_filter_gerador_excludes_extrator(self, empty_storage):
        """get_all() filtered by GERADOR must not include EXTRATOR prompts."""
        all_prompts = empty_storage.get_all()
        gerador_prompts = [p for p in all_prompts if p.ferramenta == TipoFerramenta.GERADOR]
        assert all(p.ferramenta == TipoFerramenta.GERADOR for p in gerador_prompts)
        assert len(gerador_prompts) >= 1  # at least the seeded generator default

    def test_new_prompt_defaults_ferramenta_to_extrator(self, empty_storage):
        """A new prompt created without explicit ferramenta must default to EXTRATOR."""
        new = empty_storage.add(
            PromptConfigCreate(
                nome="Sem Ferramenta Explicita",
                textoInstrucao="Instrução de teste sem campo ferramenta.",
                # ferramenta not set — relies on schema default
            )
        )
        assert new.ferramenta == TipoFerramenta.EXTRATOR

    def test_new_gerador_prompt_has_correct_ferramenta(self, empty_storage):
        """A new prompt explicitly created for GERADOR must persist that value."""
        new = empty_storage.add(
            PromptConfigCreate(
                nome="Gerador Customizado",
                textoInstrucao="Gere perguntas relevantes a partir das afirmações fornecidas.",
                ferramenta=TipoFerramenta.GERADOR,
            )
        )
        assert new.ferramenta == TipoFerramenta.GERADOR

        # Reload and verify persistence
        retrieved = empty_storage.get_by_id(new.id)
        assert retrieved is not None
        assert retrieved.ferramenta == TipoFerramenta.GERADOR


# ─────────────────────────────────────────────────────────────────────────────
# Deletion Guard Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeletionGuard:
    def test_cannot_delete_extrator_default(self, empty_storage):
        """Attempting to delete the extrator default prompt must raise ValueError."""
        with pytest.raises(ValueError, match="não pode ser excluído"):
            empty_storage.delete(_DEFAULT_PROMPT_ID)

    def test_cannot_delete_generator_default(self, empty_storage):
        """Attempting to delete the generator default prompt must raise ValueError."""
        with pytest.raises(ValueError, match="não pode ser excluído"):
            empty_storage.delete(_DEFAULT_GENERATOR_PROMPT_ID)

    def test_can_delete_custom_prompt(self, empty_storage):
        """User-created prompts must be deletable normally."""
        new = empty_storage.add(
            PromptConfigCreate(
                nome="Temporário",
                textoInstrucao="Prompt que será deletado no teste.",
            )
        )
        result = empty_storage.delete(new.id)
        assert result is True
        assert empty_storage.get_by_id(new.id) is None
