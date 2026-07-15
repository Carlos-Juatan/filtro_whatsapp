from typing import List

from fastapi import APIRouter, HTTPException, status

from src.models.schemas import ErrorDetail, PromptConfig, PromptConfigCreate
from src.services.prompt_storage import prompt_storage

router = APIRouter()


@router.get("", response_model=List[PromptConfig])
def get_prompts():
    """Get all saved Prompt Configs."""
    return prompt_storage.get_all()


@router.get("/default", response_model=dict, summary="Get default system prompt text")
def get_default_prompt():
    """Return the built-in default system prompt text so the UI can pre-fill a custom copy."""
    return {"textoInstrucao": prompt_storage.get_default_prompt_text()}


@router.post(
    "",
    response_model=PromptConfig,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorDetail}},
)
def create_prompt(prompt_create: PromptConfigCreate):
    """Add a new Prompt Config."""
    try:
        return prompt_storage.add(prompt_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"model": ErrorDetail}, 404: {"model": ErrorDetail}},
)
def delete_prompt(prompt_id: str):
    """Delete a custom Prompt Config. The system default prompt cannot be deleted."""
    try:
        deleted = prompt_storage.delete(prompt_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' não encontrado.")

