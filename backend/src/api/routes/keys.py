from typing import List
from fastapi import APIRouter, HTTPException, status

from src.models.schemas import ChaveAPI, ChaveAPICreate, ErrorDetail
from src.services.key_storage import key_storage

router = APIRouter()

@router.get("", response_model=List[ChaveAPI])
def get_keys():
    """Get all saved API keys."""
    return key_storage.get_all()

@router.post("", response_model=ChaveAPI, status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorDetail}})
def create_key(key_create: ChaveAPICreate):
    """Add a new API key."""
    try:
        return key_storage.add(key_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"model": ErrorDetail}})
def delete_key(key_id: str):
    """Delete an API key by ID."""
    success = key_storage.delete(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found.")
    return None
