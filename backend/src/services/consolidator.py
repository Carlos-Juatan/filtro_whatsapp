"""
Consolidation service for extracted Q&A pairs.

Implements the second stage of the two-stage semantic deduplication logic.
Groups and merges semantically identical or highly similar questions using the LLM,
accumulating their frequencies and merging metadata.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from src.models.schemas import ModeloOpenAI, PromptConfig, ResultadoParPR

logger = logging.getLogger(__name__)


def deduplicate_uncategorized(items: list[str]) -> list[str]:
    """
    Deduplicate a list of uncategorized content strings.

    Deduplication is case-insensitive and ignores leading/trailing whitespace.
    The first occurrence casing is preserved. Empty/whitespace-only strings
    are excluded from the result (FR-004).

    Args:
        items: Raw list of uncategorized content strings, possibly with duplicates.

    Returns:
        Ordered, deduplicated list of non-empty strings.
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        stripped = item.strip()
        if not stripped:
            continue  # skip whitespace-only items
        normalized = stripped.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(stripped)
    return result



_CONSOLIDATION_SYSTEM_PROMPT = (
    "Você é um especialista em consolidação de base de conhecimento. "
    "Sua tarefa é analisar uma lista de pares de perguntas e respostas e mesclar "
    "aquelas que são semanticamente idênticas ou muito similares em intenção. "
    "Siga as seguintes regras:\n"
    "1. Some a frequência (frequency) dos itens que forem mesclados.\n"
    "2. Escolha ou formule a pergunta e a resposta mais claras e completas para representar o grupo.\n"
    "3. Combine os metadados se houver (separe por vírgula), e escolha a categoria mais adequada.\n"
    "4. Retorne SOMENTE um objeto JSON válido com a chave 'qna_pairs' contendo a lista consolidada.\n"
    "Cada item na lista final deve seguir estritamente os campos: "
    "'question' (string), 'answer' (string), 'frequency' (integer), "
    "'metadata' (string ou null) e 'category' (string)."
)

def _parse_consolidation_response(raw_content: str) -> list[ResultadoParPR]:
    """Parse the consolidated JSON response from the LLM."""
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON for consolidation: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object with 'qna_pairs' key, got: {type(data).__name__}")

    raw_pairs = data.get("qna_pairs")

    if raw_pairs is None:
        list_keys = [k for k, v in data.items() if isinstance(v, list)]
        if list_keys:
            fallback_key = list_keys[0]
            logger.warning(
                "'qna_pairs' key not found in consolidation response. "
                "Falling back to first list-valued key: '%s'. Keys: %s",
                fallback_key,
                list(data.keys()),
            )
            raw_pairs = data[fallback_key]
        else:
            logger.warning(
                "Consolidation response has no list values and no 'qna_pairs' key. "
                "Keys: %s. Returning empty list.",
                list(data.keys()),
            )
            return []

    pairs: list[ResultadoParPR] = []
    for item in raw_pairs:
        try:
            pairs.append(
                ResultadoParPR(
                    perguntaPadronizada=str(item.get("question", "")).strip(),
                    respostaConsolidada=str(item.get("answer", "")).strip(),
                    frequencia=max(1, int(item.get("frequency", 1))),
                    metadata=item.get("metadata") or None,
                    category=str(item.get("category", "Geral")).strip() or "Geral",
                )
            )
        except Exception as exc:
            logger.warning("Skipping malformed consolidated qna item %s: %s", item, exc)

    return pairs

async def consolidate_qna_pairs(
    pairs: list[ResultadoParPR],
    api_key: str,
    model: ModeloOpenAI = ModeloOpenAI.GPT_4O_MINI,
    prompt_config: PromptConfig | None = None,
) -> list[ResultadoParPR]:
    """
    Consolidate a list of Q&A pairs semantically using the OpenAI API.
    
    If the list is empty or has only 1 item, it returns immediately.
    We convert the input pairs to JSON, send them to the LLM to merge duplicates,
    and parse the result back.
    """
    if not pairs or len(pairs) <= 1:
        return pairs

    # To avoid exceeding context window, if there are too many pairs, we might need
    # to chunk them. For this MVP, we will try to consolidate them all in one request,
    # or just pre-consolidate exact matches locally to reduce payload size.
    
    # 1. Local Exact Consolidation
    local_map: dict[str, ResultadoParPR] = {}
    for p in pairs:
        key = (p.perguntaPadronizada.lower().strip(), p.respostaConsolidada.lower().strip())
        if key in local_map:
            local_map[key].frequencia += p.frequencia
            if p.metadata:
                if local_map[key].metadata:
                    if p.metadata not in local_map[key].metadata:
                        local_map[key].metadata = f"{local_map[key].metadata}, {p.metadata}"
                else:
                    local_map[key].metadata = p.metadata
        else:
            # create a copy to avoid mutating original
            local_map[key] = ResultadoParPR(
                perguntaPadronizada=p.perguntaPadronizada,
                respostaConsolidada=p.respostaConsolidada,
                frequencia=p.frequencia,
                metadata=p.metadata,
                category=p.category
            )
            
    reduced_pairs = list(local_map.values())
    if len(reduced_pairs) <= 1:
        return reduced_pairs
        
    client = AsyncOpenAI(api_key=api_key)
    model_id: str = model.value if hasattr(model, "value") else str(model)

    # Convert to simple JSON for LLM
    input_json = json.dumps(
        [
            {
                "question": p.perguntaPadronizada,
                "answer": p.respostaConsolidada,
                "frequency": p.frequencia,
                "metadata": p.metadata,
                "category": p.category,
            }
            for p in reduced_pairs
        ],
        ensure_ascii=False,
    )

    user_message = (
        "Aqui está a lista de pares P&R extraídos para consolidação:\n"
        "---\n"
        f"{input_json}\n"
        "---\n\n"
        "Mescle itens semanticamente idênticos, somando suas frequências, e retorne o resultado final em JSON."
    )

    logger.info("Starting LLM consolidation for %d pairs", len(reduced_pairs))

    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": _CONSOLIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content or ""
        consolidated = _parse_consolidation_response(raw_content)
        logger.info("Consolidation succeeded: %d merged into %d pairs", len(pairs), len(consolidated))
        
        # fallback to reduced_pairs if LLM returns empty list (which is unexpected)
        return consolidated if consolidated else reduced_pairs
    except Exception as exc:
        logger.error("LLM consolidation failed: %s. Returning locally deduplicated pairs.", exc, exc_info=True)
        return reduced_pairs
