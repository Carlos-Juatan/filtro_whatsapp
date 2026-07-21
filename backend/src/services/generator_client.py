"""
OpenAI API client for the Question Generator feature (003-gerador-perguntas).

Responsibilities:
  - Wrap the official `openai` Python SDK for async usage.
  - Implement exponential backoff retry logic for HTTP 429 (rate-limit) errors.
  - Build the generation prompt that instructs the model to return a structured
    JSON object with `qna_pairs`, where each pair has a question generated from
    a factual statement (the answer).
  - Expose a single public coroutine `generate_qna_from_chunk()` consumed by
    the WebSocket generator processor (src/api/websocket_generator.py).

Design notes (research.md §3 – Dedicated WebSocket Endpoint):
  - Reuses the same retry/backoff constants as openai_client.py.
  - The generator prompt instructs the model to create *questions* from facts,
    the inverse operation from extraction.
  - The generator never produces `uncategorized_database_content`; always returns
    an empty list to maintain schema compatibility with the frontend parser.
  - Response format is identical to extraction: `qna_pairs` list with fields
    `question`, `answer`, `frequency`, `metadata`, `category`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from openai import AsyncOpenAI, RateLimitError

from src.models.schemas import ModeloOpenAI, PromptConfig, ResultadoParPR
from src.services.prompt_storage import DEFAULT_GENERATOR_PROMPT_TEXT as _DEFAULT_GENERATOR_PROMPT

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Retry configuration (mirrors openai_client.py for consistency)
# ──────────────────────────────────────────────────────────────────────────────

MAX_RETRIES: int = 3
INITIAL_BACKOFF_S: float = 2.0
MAX_BACKOFF_S: float = 60.0


# ──────────────────────────────────────────────────────────────────────────────
# System prompt builder
# ──────────────────────────────────────────────────────────────────────────────


def _build_generator_system_prompt(prompt_config: PromptConfig | None) -> str:
    """
    Construct the LLM system prompt from *prompt_config* for question generation.

    - None → use the built-in default generator prompt text.
    - FIXO with textoInstrucao → use its textoInstrucao directly.
    - FIXO without textoInstrucao → use the built-in default generator prompt.
    - CUSTOMIZADO with textoInstrucao → use it, appending keyword hint if present.
    """
    if prompt_config is None:
        return _DEFAULT_GENERATOR_PROMPT

    from src.models.schemas import TipoPrompt

    if prompt_config.tipo == TipoPrompt.FIXO:
        return (
            prompt_config.textoInstrucao
            if prompt_config.textoInstrucao
            else _DEFAULT_GENERATOR_PROMPT
        )

    # CUSTOMIZADO: append keyword hint if configured.
    if prompt_config.textoInstrucao:
        kw_hint = ""
        if prompt_config.palavrasChave:
            kw_list = ", ".join(f"'{k}'" for k in prompt_config.palavrasChave)
            kw_hint = f"\nPriorize a geração de perguntas relacionadas aos seguintes temas: {kw_list}."
        return prompt_config.textoInstrucao + kw_hint

    return _DEFAULT_GENERATOR_PROMPT


def _build_generator_user_message(chunk_text: str, language: str = "pt-br") -> str:
    """Build the user-role message containing the unstructured content chunk."""
    return (
        f"Idioma de saída: {language}\n\n"
        "Conteúdo para análise:\n"
        "---\n"
        f"{chunk_text}\n"
        "---\n\n"
        "Gere perguntas para cada fato ou afirmação útil e retorne como JSON."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Response parser
# ──────────────────────────────────────────────────────────────────────────────


def _parse_generator_response(raw_content: str) -> list[ResultadoParPR]:
    """
    Parse the model's raw text response into a list of ResultadoParPR.

    The model is instructed to return pure JSON with a `qna_pairs` key.
    Defensively strips markdown code fences before parsing.

    Args:
        raw_content: Raw string returned by the model.

    Returns:
        List of ResultadoParPR pairs — may be empty.

    Raises:
        ValueError: If the JSON cannot be parsed.
    """
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object with 'qna_pairs' key, got: {type(data).__name__}"
        )

    raw_pairs = data.get("qna_pairs")

    # Fallback: if 'qna_pairs' is missing, look for any list-valued key.
    if raw_pairs is None:
        list_keys = [k for k, v in data.items() if isinstance(v, list)]
        if list_keys:
            fallback_key = list_keys[0]
            logger.warning(
                "'qna_pairs' key not found in generator response. "
                "Falling back to first list-valued key: '%s'. "
                "Full keys returned: %s",
                fallback_key,
                list(data.keys()),
            )
            raw_pairs = data[fallback_key]
        else:
            logger.warning(
                "Generator model returned a dict with no list values and no 'qna_pairs' key. "
                "Keys returned: %s. Returning empty result for this chunk.",
                list(data.keys()),
            )
            raw_pairs = []

    pairs: list[ResultadoParPR] = []
    for item in raw_pairs:
        try:
            pairs.append(
                ResultadoParPR(
                    perguntaPadronizada=str(item.get("question", "")).strip(),
                    respostaConsolidada=str(item.get("answer", "")).strip(),
                    frequencia=max(1, int(item.get("frequency", 1))),
                    metadata=item.get("metadata") or None,
                    category=str(item.get("category", "FAQ")).strip() or "FAQ",
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping malformed generator qna item %s: %s", item, exc)

    return pairs


# ──────────────────────────────────────────────────────────────────────────────
# Public generation coroutine
# ──────────────────────────────────────────────────────────────────────────────


async def generate_qna_from_chunk(
    chunk_text: str,
    api_key: str,
    model: ModeloOpenAI = ModeloOpenAI.GPT_4O_MINI,
    prompt_config: PromptConfig | None = None,
) -> tuple[list[ResultadoParPR], list[str]]:
    """
    Send *chunk_text* to the OpenAI Chat Completions API and return generated
    Q&A pairs as a tuple of (pairs, uncategorized).

    The generator always returns an empty uncategorized list to maintain
    contract compatibility with the frontend parser and WebSocket contract.

    Retries up to MAX_RETRIES times on HTTP 429 (RateLimitError), applying
    exponential backoff between attempts.

    Args:
        chunk_text:    The unstructured text chunk to generate questions from.
        api_key:       OpenAI API key string (sk-...).
        model:         Which OpenAI model to call (default: gpt-4o-mini).
        prompt_config: Optional prompt configuration; uses default if None.

    Returns:
        Tuple of (pairs, uncategorized) — uncategorized is always [].

    Raises:
        RuntimeError: If all retries are exhausted due to rate-limiting.
        ValueError:   If the model returns malformed JSON.
        Exception:    Any other unexpected API error is re-raised.
    """
    client = AsyncOpenAI(api_key=api_key)

    language = prompt_config.idiomaModelo if prompt_config else "pt-br"
    system_prompt = _build_generator_system_prompt(prompt_config)
    user_message = _build_generator_user_message(chunk_text, language)
    model_id: str = model.value if hasattr(model, "value") else str(model)

    backoff = INITIAL_BACKOFF_S
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Generator OpenAI call attempt %d/%d (model=%s, tokens≈%d chars)",
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
                temperature=0.1,  # low temperature for deterministic JSON generation
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content or ""
            pairs = _parse_generator_response(raw_content)
            logger.info(
                "Generator succeeded: %d Q&A pairs generated.",
                len(pairs),
            )
            # Always return empty uncategorized list (contract compatibility)
            return pairs, []

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
                "Unexpected OpenAI error on generator attempt %d: %s", attempt, exc, exc_info=True
            )
            raise

    raise RuntimeError(
        f"Limite de taxa atingido (429) após {MAX_RETRIES} tentativas de backoff. "
        f"Último erro: {last_exc}"
    )
