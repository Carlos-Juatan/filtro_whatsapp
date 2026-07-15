"""
OpenAI API client manager for the Extrator e Filtro de P&R (Local) tool.

Responsibilities:
  - Wrap the official `openai` Python SDK for async usage.
  - Implement exponential backoff retry logic for HTTP 429 (rate-limit) errors.
  - Build the extraction prompt that instructs the model to return a structured
    JSON array of Q&A pairs (qna_pairs) from a text chunk.
  - Expose a single public coroutine `extract_qna_from_chunk()` consumed by
    the WebSocket processor (src/api/websocket.py).

Design decisions (research.md §4 – Semantic Deduplication):
  - Per-chunk extraction: each chunk is sent independently in a single API call.
  - The model is instructed to return ONLY valid JSON matching the QnAOutput schema.
  - Backoff: up to MAX_RETRIES attempts, with a base delay of INITIAL_BACKOFF_S
    seconds, doubling on each retry (capped at MAX_BACKOFF_S).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI, RateLimitError

from src.models.schemas import ModeloOpenAI, PromptConfig, ResultadoParPR
from src.services.prompt_storage import DEFAULT_SYSTEM_PROMPT_TEXT as _DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Retry configuration
# ──────────────────────────────────────────────────────────────────────────────

MAX_RETRIES: int = 3
INITIAL_BACKOFF_S: float = 2.0
MAX_BACKOFF_S: float = 60.0

# ──────────────────────────────────────────────────────────────────────────────
# Extraction prompt builder
# ──────────────────────────────────────────────────────────────────────────────



def _build_system_prompt(prompt_config: PromptConfig | None) -> str:
    """
    Construct the LLM system prompt from *prompt_config*.

    - None → use the built-in default prompt text.
    - FIXO with textoInstrucao → use its textoInstrucao (the seeded default).
    - FIXO without textoInstrucao → use the built-in default prompt text.
    - CUSTOMIZADO with textoInstrucao → use it as-is (user is responsible for
      the full instruction; a keyword hint is appended when keywords are present).
    """
    if prompt_config is None:
        return _DEFAULT_SYSTEM_PROMPT

    from src.models.schemas import TipoPrompt

    # For FIXO prompts that carry the system textoInstrucao, use it directly.
    if prompt_config.tipo == TipoPrompt.FIXO:
        return prompt_config.textoInstrucao if prompt_config.textoInstrucao else _DEFAULT_SYSTEM_PROMPT

    # CUSTOMIZADO: use user-provided instruction, appending keyword hint only.
    if prompt_config.textoInstrucao:
        kw_hint = ""
        if prompt_config.palavrasChave:
            kw_list = ", ".join(f"'{k}'" for k in prompt_config.palavrasChave)
            kw_hint = f"\nPriorize perguntas relacionadas aos seguintes temas: {kw_list}."
        return prompt_config.textoInstrucao + kw_hint

    return _DEFAULT_SYSTEM_PROMPT



def _build_user_message(chunk_text: str, language: str = "pt-br") -> str:
    """Build the user-role message containing the chunk and the language directive."""
    return (
        f"Idioma de saída: {language}\n\n"
        "Texto para análise:\n"
        "---\n"
        f"{chunk_text}\n"
        "---\n\n"
        "Extraia todos os pares de pergunta e resposta e retorne como JSON."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Response parser
# ──────────────────────────────────────────────────────────────────────────────


def _parse_qna_response(raw_content: str) -> list[ResultadoParPR]:
    """
    Parse the model's raw text response into a list of ResultadoParPR objects.

    The model is instructed to return pure JSON, but we defensively strip any
    markdown code fences before attempting to parse.

    Args:
        raw_content: Raw string returned by the model.

    Returns:
        A (possibly empty) list of ResultadoParPR instances.

    Raises:
        ValueError: If the JSON cannot be parsed or lacks the 'qna_pairs' key.
    """
    # Strip optional markdown code fences: ```json ... ``` or ``` ... ```
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        # Remove first line (```json or ```) and last line (```)
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object with 'qna_pairs' key, got: {type(data).__name__}"
        )

    # Primary key
    raw_pairs = data.get("qna_pairs")

    # Fallback: if 'qna_pairs' is missing, look for any list-valued key in the dict.
    # The model sometimes returns {"pairs": [...]} or {"results": [...]} instead.
    if raw_pairs is None:
        list_keys = [k for k, v in data.items() if isinstance(v, list)]
        if list_keys:
            fallback_key = list_keys[0]
            logger.warning(
                "'qna_pairs' key not found in model response. "
                "Falling back to first list-valued key: '%s'. "
                "Full keys returned: %s",
                fallback_key,
                list(data.keys()),
            )
            raw_pairs = data[fallback_key]
        else:
            logger.warning(
                "Model returned a dict with no list values and no 'qna_pairs' key. "
                "Keys returned: %s. Returning empty result for this chunk.",
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping malformed qna item %s: %s", item, exc)

    return pairs


# ──────────────────────────────────────────────────────────────────────────────
# Public extraction coroutine
# ──────────────────────────────────────────────────────────────────────────────


async def extract_qna_from_chunk(
    chunk_text: str,
    api_key: str,
    model: ModeloOpenAI = ModeloOpenAI.GPT_4O_MINI,
    prompt_config: PromptConfig | None = None,
) -> list[ResultadoParPR]:
    """
    Send *chunk_text* to the OpenAI Chat Completions API and return extracted
    Q&A pairs as a list of ResultadoParPR objects.

    Retries up to MAX_RETRIES times on HTTP 429 (RateLimitError), applying
    exponential backoff between attempts.

    Args:
        chunk_text:    The text chunk to analyse.
        api_key:       OpenAI API key string (sk-...).
        model:         Which OpenAI model to call (default: gpt-4o-mini).
        prompt_config: Optional prompt configuration; uses default if None.

    Returns:
        List of extracted Q&A pairs (may be empty if the chunk yielded nothing).

    Raises:
        RuntimeError: If all retries are exhausted due to rate-limiting.
        ValueError:   If the model returns malformed JSON.
        Exception:    Any other unexpected API error is re-raised.
    """
    client = AsyncOpenAI(api_key=api_key)

    language = prompt_config.idiomaModelo if prompt_config else "pt-br"
    system_prompt = _build_system_prompt(prompt_config)
    user_message = _build_user_message(chunk_text, language)
    model_id: str = model.value if hasattr(model, "value") else str(model)

    backoff = INITIAL_BACKOFF_S
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "OpenAI call attempt %d/%d (model=%s, tokens≈%d chars)",
                attempt,
                MAX_RETRIES,
                model_id,
                len(chunk_text),
            )
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,  # low temperature for deterministic JSON extraction
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or ""
            pairs = _parse_qna_response(raw_content)
            logger.info(
                "OpenAI extraction succeeded: %d Q&A pairs extracted.", len(pairs)
            )
            return pairs

        except RateLimitError as exc:
            last_exc = exc
            if attempt == MAX_RETRIES:
                break
            wait = min(backoff, MAX_BACKOFF_S)
            logger.warning(
                "Rate limit hit (attempt %d/%d). Retrying in %.1fs…",
                attempt,
                MAX_RETRIES,
                wait,
            )
            await asyncio.sleep(wait)
            backoff *= 2

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected OpenAI error on attempt %d: %s", attempt, exc, exc_info=True
            )
            raise

    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    raise RuntimeError(
        f"Limite de taxa atingido (429) após {MAX_RETRIES} tentativas de backoff. "
        f"Último erro: {last_exc}"
    )
