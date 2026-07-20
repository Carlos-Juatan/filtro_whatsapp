import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.models.schemas import PromptConfigCreate, TipoPrompt, ModeloOpenAI
from src.services.prompt_storage import PromptStorageService

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

    # Retrieve all — note: storage now seeds 2 built-in defaults (extrator + generator)
    # so total count is at least 3 (2 defaults + the prompt we just added).
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
