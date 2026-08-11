import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.models.schemas import PromptConfigCreate, TipoPrompt, TipoFerramenta, ModeloOpenAI
from src.services.prompt_storage import (
    PromptStorageService,
    DEFAULT_SYSTEM_PROMPT_TEXT,
    DEFAULT_GENERATOR_PROMPT_TEXT,
    DEFAULT_CONSOLIDATOR_PROMPT_TEXT,
    _DEFAULT_PROMPT_ID,
    _DEFAULT_GENERATOR_PROMPT_ID,
    _DEFAULT_CONSOLIDATOR_PROMPT_ID,
)

@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Patch DATA_DIR in prompt_storage
        with patch("src.services.prompt_storage.DATA_DIR", Path(tmpdirname)), \
             patch("src.services.prompt_storage.PROMPTS_FILE", Path(tmpdirname) / "prompts.json"):
            storage = PromptStorageService()
            yield storage

def test_prompt_serialization_and_retrieval(temp_storage):
    # Add prompt
    prompt_create = PromptConfigCreate(
        nome="Test Prompt",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Extract all questions and answers from the given text.",
        palavrasChave=["q&a", "faq"],
        idiomaModelo="en-us",
        modeloOpenAI=ModeloOpenAI.GPT_4O_MINI
    )
    added_prompt = temp_storage.add(prompt_create)
    
    assert added_prompt.nome == "Test Prompt"
    assert added_prompt.tipo == TipoPrompt.CUSTOMIZADO
    assert added_prompt.textoInstrucao == "Extract all questions and answers from the given text."
    assert added_prompt.palavrasChave == ["q&a", "faq"]
    assert added_prompt.idiomaModelo == "en-us"
    assert added_prompt.modeloOpenAI == ModeloOpenAI.GPT_4O_MINI
    assert added_prompt.id is not None

    # Retrieve all — storage seeds 3 built-in defaults (extrator + gerador + consolidador)
    # so total count is at least 4 (3 defaults + the prompt we just added).
    prompts = temp_storage.get_all()
    ids = [p.id for p in prompts]
    assert added_prompt.id in ids, "User-created prompt must appear in get_all() result"

    # Retrieve by id
    retrieved = temp_storage.get_by_id(added_prompt.id)
    assert retrieved is not None
    assert retrieved.id == added_prompt.id

def test_customizado_requires_texto_instrucao(temp_storage):
    prompt_create = PromptConfigCreate(
        nome="Invalid Custom",
        tipo=TipoPrompt.CUSTOMIZADO,
        # textoInstrucao is intentionally missing/None
    )
    with pytest.raises(ValueError, match="textoInstrucao is required for CUSTOMIZADO prompts."):
        temp_storage.add(prompt_create)

def test_unique_constraint(temp_storage):
    prompt_create1 = PromptConfigCreate(
        nome="Unique Prompt",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Some text long enough"
    )
    temp_storage.add(prompt_create1)
    
    # Try adding same name
    prompt_create2 = PromptConfigCreate(
        nome="Unique Prompt",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Different text long enough"
    )
    with pytest.raises(ValueError, match="Prompt with name 'Unique Prompt' already exists."):
        temp_storage.add(prompt_create2)
        
    # Case insensitive check
    prompt_create3 = PromptConfigCreate(
        nome="unique prompt",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Different text 2 long enough"
    )
    with pytest.raises(ValueError, match="Prompt with name 'unique prompt' already exists."):
        temp_storage.add(prompt_create3)


# ─── New tests for feature 005-separate-tool-prompts ──────────────────────────


def test_three_default_prompts_initialized(temp_storage):
    """Storage must seed exactly 3 built-in FIXO prompts, one per tool."""
    all_prompts = temp_storage.get_all()
    fixo_prompts = [p for p in all_prompts if p.tipo == TipoPrompt.FIXO]
    assert len(fixo_prompts) == 3, "Expected exactly 3 built-in FIXO prompts"

    tool_values = {p.ferramenta for p in fixo_prompts}
    assert TipoFerramenta.EXTRATOR in tool_values
    assert TipoFerramenta.GERADOR in tool_values
    assert TipoFerramenta.CONSOLIDADOR in tool_values

    ids = {p.id for p in fixo_prompts}
    assert _DEFAULT_PROMPT_ID in ids
    assert _DEFAULT_GENERATOR_PROMPT_ID in ids
    assert _DEFAULT_CONSOLIDATOR_PROMPT_ID in ids


def test_get_default_prompt_text_per_tool(temp_storage):
    """get_default_prompt_text returns the correct text for each tool."""
    assert temp_storage.get_default_prompt_text() == DEFAULT_SYSTEM_PROMPT_TEXT
    assert temp_storage.get_default_prompt_text(TipoFerramenta.EXTRATOR) == DEFAULT_SYSTEM_PROMPT_TEXT
    assert temp_storage.get_default_prompt_text(TipoFerramenta.GERADOR) == DEFAULT_GENERATOR_PROMPT_TEXT
    assert temp_storage.get_default_prompt_text(TipoFerramenta.CONSOLIDADOR) == DEFAULT_CONSOLIDATOR_PROMPT_TEXT


def test_tool_association_persistence(temp_storage):
    """Prompts created for a specific tool must be persisted with the correct ferramenta value (FR-006)."""
    prompt_extrator = PromptConfigCreate(
        nome="Custom Extrator",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Custom extraction instruction for testing purposes.",
        ferramenta=TipoFerramenta.EXTRATOR,
    )
    prompt_gerador = PromptConfigCreate(
        nome="Custom Gerador",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Custom generation instruction for testing purposes.",
        ferramenta=TipoFerramenta.GERADOR,
    )
    prompt_consolidador = PromptConfigCreate(
        nome="Custom Consolidador",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Custom consolidation instruction for testing purposes.",
        ferramenta=TipoFerramenta.CONSOLIDADOR,
    )

    added_ext = temp_storage.add(prompt_extrator)
    added_gen = temp_storage.add(prompt_gerador)
    added_con = temp_storage.add(prompt_consolidador)

    # Verify ferramenta persisted correctly
    retrieved_ext = temp_storage.get_by_id(added_ext.id)
    retrieved_gen = temp_storage.get_by_id(added_gen.id)
    retrieved_con = temp_storage.get_by_id(added_con.id)

    assert retrieved_ext.ferramenta == TipoFerramenta.EXTRATOR
    assert retrieved_gen.ferramenta == TipoFerramenta.GERADOR
    assert retrieved_con.ferramenta == TipoFerramenta.CONSOLIDADOR


def test_tool_scoped_filtering(temp_storage):
    """get_all() results can be filtered by tool; each filter returns only prompts of that tool."""
    temp_storage.add(PromptConfigCreate(
        nome="Extrator Custom",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Extraction instruction for filtering test.",
        ferramenta=TipoFerramenta.EXTRATOR,
    ))
    temp_storage.add(PromptConfigCreate(
        nome="Gerador Custom",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Generation instruction for filtering test.",
        ferramenta=TipoFerramenta.GERADOR,
    ))

    all_prompts = temp_storage.get_all()
    extrator_prompts = [p for p in all_prompts if p.ferramenta == TipoFerramenta.EXTRATOR]
    gerador_prompts = [p for p in all_prompts if p.ferramenta == TipoFerramenta.GERADOR]
    consolidador_prompts = [p for p in all_prompts if p.ferramenta == TipoFerramenta.CONSOLIDADOR]

    # Each group must include the FIXO default + any custom prompts created
    assert any(p.tipo == TipoPrompt.FIXO for p in extrator_prompts), "Extrator must have its FIXO default"
    assert any(p.tipo == TipoPrompt.FIXO for p in gerador_prompts), "Gerador must have its FIXO default"
    assert any(p.tipo == TipoPrompt.FIXO for p in consolidador_prompts), "Consolidador must have its FIXO default"

    # Custom prompts must appear only in their respective tool's list
    extrator_names = {p.nome for p in extrator_prompts}
    gerador_names = {p.nome for p in gerador_prompts}
    assert "Extrator Custom" in extrator_names
    assert "Gerador Custom" not in extrator_names
    assert "Gerador Custom" in gerador_names
    assert "Extrator Custom" not in gerador_names


def test_deletion_protection_all_defaults(temp_storage):
    """All 3 built-in FIXO prompts must raise ValueError when deletion is attempted."""
    for prompt_id in [_DEFAULT_PROMPT_ID, _DEFAULT_GENERATOR_PROMPT_ID, _DEFAULT_CONSOLIDATOR_PROMPT_ID]:
        with pytest.raises(ValueError, match="O prompt padrão do sistema não pode ser excluído."):
            temp_storage.delete(prompt_id)


def test_delete_custom_prompt_and_fallback_to_default(temp_storage):
    """Deleting a custom prompt must succeed and not affect the tool's default FIXO prompt."""
    custom = temp_storage.add(PromptConfigCreate(
        nome="Temp Custom",
        tipo=TipoPrompt.CUSTOMIZADO,
        textoInstrucao="Temporary instruction for deletion test.",
        ferramenta=TipoFerramenta.EXTRATOR,
    ))

    deleted = temp_storage.delete(custom.id)
    assert deleted is True, "Custom prompt deletion must return True"

    all_prompts = temp_storage.get_all()
    ids = [p.id for p in all_prompts]
    assert custom.id not in ids, "Deleted custom prompt must not appear in list"
    # Extrator default must still exist
    assert _DEFAULT_PROMPT_ID in ids, "Extrator default (FIXO) must remain after custom deletion"

