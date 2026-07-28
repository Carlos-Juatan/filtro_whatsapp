import json
import logging
import re
from typing import List, Dict, Optional, Tuple

from src.models.merger import QnAPair
from src.services.key_storage import key_storage
from src.services.prompt_storage import (
    prompt_storage,
    _DEFAULT_CONSOLIDADOR_PROMPT_ID,
    DEFAULT_CONSOLIDADOR_PROMPT_TEXT,
)

try:
    from openai import AsyncOpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment,misc]
    _OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# ChatGPT response parser (mirrors openai_client._parse_qna_response for
# the consolidador JSON schema: perguntaPadronizada / respostaConsolidada)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_consolidador_response(raw_content: str) -> List[QnAPair]:
    """
    Parse a ChatGPT JSON response that follows the CONSOLIDADOR prompt schema.

    Expected JSON shape::

        {
            "qna_pairs": [
                {
                    "perguntaPadronizada": "...",
                    "respostaConsolidada": "...",
                    "frequencia": 3,
                    "metadata": "...",
                    "category": "..."
                }
            ]
        }

    Returns an empty list if the response cannot be parsed.
    """
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("CONSOLIDADOR: invalid JSON from ChatGPT — %s", exc)
        return []

    if not isinstance(data, dict):
        logger.warning("CONSOLIDADOR: expected JSON object, got %s", type(data).__name__)
        return []

    raw_pairs = data.get("qna_pairs", [])
    if not isinstance(raw_pairs, list):
        logger.warning("CONSOLIDADOR: 'qna_pairs' is not a list — skipping AI result")
        return []

    pairs: List[QnAPair] = []
    for item in raw_pairs:
        try:
            pairs.append(
                QnAPair(
                    perguntaPadronizada=str(item.get("perguntaPadronizada", "")).strip(),
                    respostaConsolidada=str(item.get("respostaConsolidada", "")).strip(),
                    frequencia=max(1, int(item.get("frequencia", 1))),
                    metadata=item.get("metadata") or None,
                    category=item.get("category") or None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("CONSOLIDADOR: skipping malformed item %s — %s", item, exc)

    return pairs


class QnAMergerService:
    @staticmethod
    def normalize_question(question: str) -> str:
        """
        Normalize a question string for matching:
        - Convert to lowercase
        - Strip outer whitespace
        - Remove trailing punctuation (e.g., '?')
        - Collapse internal whitespace sequences into a single space
        """
        # Convert to lower and strip outer whitespace
        normalized = question.lower().strip()

        # Remove trailing punctuation (e.g. ?)
        normalized = re.sub(r'[?.,;!]+$', '', normalized).strip()

        # Collapse internal whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    @staticmethod
    def merge_qna_pairs(pairs: List[QnAPair]) -> List[QnAPair]:
        """
        Deduplicates and merges a list of QnAPair objects using local
        algorithmic rules:
        - Normalize questions for matching (case-insensitive, punctuation-stripped)
        - Sum frequencies for duplicates
        - Retain the longest answer
        - Union metadata and category tags
        """
        merged_dict: Dict[str, QnAPair] = {}

        for pair in pairs:
            normalized_q = QnAMergerService.normalize_question(pair.perguntaPadronizada)

            if normalized_q in merged_dict:
                existing_pair = merged_dict[normalized_q]

                # Sum frequency
                new_frequencia = existing_pair.frequencia + pair.frequencia

                # Select longest answer
                ans1 = existing_pair.respostaConsolidada
                ans2 = pair.respostaConsolidada
                best_answer = ans2 if len(ans2.strip()) > len(ans1.strip()) else ans1

                # Merge metadata
                merged_meta = existing_pair.metadata
                if pair.metadata:
                    if merged_meta:
                        meta1_tags = {t.strip() for t in merged_meta.split(',') if t.strip()}
                        meta2_tags = {t.strip() for t in pair.metadata.split(',') if t.strip()}
                        combined = meta1_tags.union(meta2_tags)
                        merged_meta = ", ".join(sorted(combined)) if combined else None
                    else:
                        merged_meta = pair.metadata

                # Merge category
                merged_category = existing_pair.category
                if pair.category:
                    if merged_category:
                        cat1_tags = {t.strip() for t in merged_category.split(',') if t.strip()}
                        cat2_tags = {t.strip() for t in pair.category.split(',') if t.strip()}
                        combined_cats = cat1_tags.union(cat2_tags)
                        merged_category = ", ".join(sorted(combined_cats)) if combined_cats else None
                    else:
                        merged_category = pair.category

                # Keep the original perguntaPadronizada from the first encountered instance
                merged_dict[normalized_q] = QnAPair(
                    perguntaPadronizada=existing_pair.perguntaPadronizada,
                    respostaConsolidada=best_answer,
                    frequencia=new_frequencia,
                    metadata=merged_meta,
                    category=merged_category,
                )
            else:
                # Store the original pair
                merged_dict[normalized_q] = QnAPair(
                    perguntaPadronizada=pair.perguntaPadronizada,
                    respostaConsolidada=pair.respostaConsolidada,
                    frequencia=pair.frequencia,
                    metadata=pair.metadata,
                    category=pair.category,
                )

        return list(merged_dict.values())

    @staticmethod
    async def consolidate_with_ai(
        pairs: List[QnAPair],
        batch_size: int = 50,
    ) -> Tuple[List[QnAPair], Optional[str]]:
        """
        FR-011: Consolidate pre-grouped Q&A pairs via ChatGPT using the
        CONSOLIDADOR system prompt.

        Algorithm:
        1. Check for an active OpenAI API key via KeyStorageService.
        2. If no key → return local merge result + warning message.
        3. Retrieve the active CONSOLIDADOR prompt from PromptStorageService.
        4. Send pairs in batches to the OpenAI API (JSON mode).
        5. Parse the CONSOLIDADOR response format (perguntaPadronizada / respostaConsolidada).
        6. If the AI call fails → fall back to local merge + warning.

        Args:
            pairs:      Pre-grouped Q&A pairs (output of merge_qna_pairs).
            batch_size: Maximum pairs per OpenAI request to respect context limits.

        Returns:
            Tuple of (consolidated_pairs, optional_warning_string).
            Warning is None when AI consolidation succeeded.
        """
        # ── 1. Check for active API key ──────────────────────────────────────────
        try:
            all_keys = key_storage.get_all()
        except Exception as exc:
            logger.warning("CONSOLIDADOR: could not load API keys — %s", exc)
            all_keys = []

        if not all_keys:
            warning = (
                "Consolidação via IA ignorada: nenhuma chave OpenAI configurada. "
                "Aplicando mesclagem algorítmica local."
            )
            logger.info("CONSOLIDADOR: fallback — %s", warning)
            return QnAMergerService.merge_qna_pairs(pairs), warning

        active_key = all_keys[0]  # Use first registered key (most recently added)

        # ── 2. Retrieve CONSOLIDADOR prompt ────────────────────────────────────────
        try:
            consolidador_prompt = prompt_storage.get_by_id(_DEFAULT_CONSOLIDADOR_PROMPT_ID)
            system_text = (
                consolidador_prompt.textoInstrucao
                if consolidador_prompt and consolidador_prompt.textoInstrucao
                else None
            )
        except Exception as exc:
            logger.warning("CONSOLIDADOR: could not load prompt — %s", exc)
            system_text = None

        if system_text is None:
            system_text = DEFAULT_CONSOLIDADOR_PROMPT_TEXT

        # ── 3. Send batches to OpenAI ──────────────────────────────────────────
        if not _OPENAI_AVAILABLE or AsyncOpenAI is None:
            warning = (
                "Consolidação via IA ignorada: biblioteca OpenAI não instalada. "
                "Aplicando mesclagem algorítmica local."
            )
            return QnAMergerService.merge_qna_pairs(pairs), warning

        client = AsyncOpenAI(api_key=active_key.chave)
        all_consolidated: List[QnAPair] = []

        try:
            for i in range(0, max(1, len(pairs)), batch_size):
                batch = pairs[i: i + batch_size]
                batch_payload = [
                    {
                        "perguntaPadronizada": p.perguntaPadronizada,
                        "respostaConsolidada": p.respostaConsolidada,
                        "frequencia": p.frequencia,
                        "metadata": p.metadata,
                        "category": p.category,
                    }
                    for p in batch
                ]
                user_message = (
                    "Consolide o seguinte grupo de P&R:\n\n"
                    f"{json.dumps({'qna_pairs': batch_payload}, ensure_ascii=False, indent=2)}"
                )

                logger.info(
                    "CONSOLIDADOR: sending batch %d/%d (%d pairs) to ChatGPT",
                    i // batch_size + 1,
                    (len(pairs) + batch_size - 1) // batch_size,
                    len(batch),
                )

                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_text},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )

                raw = response.choices[0].message.content or ""
                consolidated_batch = _parse_consolidador_response(raw)

                if consolidated_batch:
                    all_consolidated.extend(consolidated_batch)
                else:
                    # If AI returned nothing useful, keep the local-merged batch
                    logger.warning(
                        "CONSOLIDADOR: empty AI response for batch %d — keeping local merge",
                        i // batch_size + 1,
                    )
                    all_consolidated.extend(batch)

        except Exception as exc:
            warning = (
                f"Consolidação via IA falhou ({exc}). "
                "Aplicando mesclagem algorítmica local como fallback."
            )
            logger.warning("CONSOLIDADOR: AI error — %s", exc, exc_info=True)
            return QnAMergerService.merge_qna_pairs(pairs), warning

        return all_consolidated, None
