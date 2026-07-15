import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.models.schemas import ChaveAPICreate
from src.services.key_storage import KeyStorageService

@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Patch DATA_DIR in key_storage
        with patch("src.services.key_storage.DATA_DIR", Path(tmpdirname)), \
             patch("src.services.key_storage.KEYS_FILE", Path(tmpdirname) / "keys.json"):
            storage = KeyStorageService()
            yield storage

def test_key_serialization_and_retrieval(temp_storage):
    # Add key
    key_create = ChaveAPICreate(nomeIdentificacao="Test Key", chave="sk-test-123")
    added_key = temp_storage.add(key_create)
    
    assert added_key.nomeIdentificacao == "Test Key"
    assert added_key.chave == "sk-test-123"
    assert added_key.id is not None

    # Retrieve all
    keys = temp_storage.get_all()
    assert len(keys) == 1
    assert keys[0].id == added_key.id

    # Retrieve by id
    retrieved = temp_storage.get_by_id(added_key.id)
    assert retrieved is not None
    assert retrieved.id == added_key.id

def test_unique_constraint(temp_storage):
    key_create1 = ChaveAPICreate(nomeIdentificacao="Unique Key", chave="sk-test-1")
    temp_storage.add(key_create1)
    
    # Try adding same name
    key_create2 = ChaveAPICreate(nomeIdentificacao="Unique Key", chave="sk-test-2")
    with pytest.raises(ValueError, match="Key with name 'Unique Key' already exists."):
        temp_storage.add(key_create2)
        
    # Case insensitive check
    key_create3 = ChaveAPICreate(nomeIdentificacao="unique key", chave="sk-test-3")
    with pytest.raises(ValueError, match="Key with name 'unique key' already exists."):
        temp_storage.add(key_create3)

def test_delete_key(temp_storage):
    key_create = ChaveAPICreate(nomeIdentificacao="Delete Me", chave="sk-test-1")
    added_key = temp_storage.add(key_create)
    
    assert len(temp_storage.get_all()) == 1
    
    success = temp_storage.delete(added_key.id)
    assert success is True
    assert len(temp_storage.get_all()) == 0
    
    # Try deleting again
    success = temp_storage.delete(added_key.id)
    assert success is False
