from typing import List
from fastapi import APIRouter, HTTPException, status

from src.models.schemas import PromptConfig, PromptConfigCreate, ErrorDetail
from src.services.prompt_storage import prompt_storage

router = APIRouter()

@router.get("", response_model=List[PromptConfig])
def get_prompts():
    """Get all saved Prompt Configs."""
    return prompt_storage.get_all()

@router.post("", response_model=PromptConfig, status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorDetail}})
def create_prompt(prompt_create: PromptConfigCreate):
    """Add a new Prompt Config."""
    try:
        return prompt_storage.add(prompt_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
