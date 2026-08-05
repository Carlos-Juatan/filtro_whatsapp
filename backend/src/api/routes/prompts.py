from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.models.schemas import ErrorDetail, PromptConfig, PromptConfigCreate, TipoFerramenta
from src.services.prompt_storage import prompt_storage

router = APIRouter()


@router.get("", response_model=List[PromptConfig])
def get_prompts(
    ferramenta: Optional[TipoFerramenta] = Query(
        default=None,
        description="Filter prompts by tool: 'extrator', 'gerador', or 'consolidador'. Returns all if omitted.",
    )
):
    """Get all saved Prompt Configs, optionally filtered by tool type."""
    prompts = prompt_storage.get_all()
    if ferramenta is not None:
        prompts = [p for p in prompts if p.ferramenta == ferramenta]
    return prompts


@router.get("/default", response_model=dict, summary="Get default system prompt text")
def get_default_prompt(
    ferramenta: Optional[TipoFerramenta] = Query(
        default=None,
        description="Tool whose default prompt text should be returned ('extrator', 'gerador', or 'consolidador'). Defaults to 'extrator'.",
    )
):
    """Return the built-in default system prompt text for the specified tool so the UI can pre-fill a custom copy."""
    return {"textoInstrucao": prompt_storage.get_default_prompt_text(ferramenta)}



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

