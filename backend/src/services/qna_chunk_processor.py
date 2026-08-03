"""
Chunked batch processing engine for Q&A pair consolidation (FR-013, FR-014, SC-005).

Architecture
------------
The ``QnaChunkProcessor`` class implements a memory-bounded merging strategy
that avoids loading the entire main document and all incoming pairs into a
single LLM context window at once.

Algorithm
---------
Given:
  - ``main_pairs``    — the accumulated Q&A document (may be empty on first run)
  - ``new_pairs``     — the freshly parsed Q&A pairs from the uploaded files
  - ``CHUNK_SIZE``    — max pairs per chunk of the main document (env: CHUNK_SIZE, default 30)
  - ``BATCH_SIZE``    — max pairs per incoming batch (env: BATCH_SIZE, default 30)

Steps:
  1. Split ``main_pairs`` into chunks of ``CHUNK_SIZE``.
  2. Split ``new_pairs`` into batches of ``BATCH_SIZE``.
  3. For each batch:
     a. For each chunk of the main document:
        - Identify new pairs whose normalised question matches an existing pair in the chunk.
        - Merge duplicates inline (sum frequencies, keep longest answer, union metadata).
        - Remove matched pairs from the current batch.
     b. Append any *unmatched* pairs from the batch to a residual list.
  4. Reconstruct the updated main document from the mutated chunks + residuals.
  5. Return the final list ready for optional AI refinement.

Configuration
-------------
Read ``CHUNK_SIZE`` and ``BATCH_SIZE`` from environment variables.
Fallback defaults: both 30.
"""

import os
import re
import logging
from typing import Callable, List, Optional

from src.models.merger import MergerLogEvent, MergerLogEventType, QnAPair

logger = logging.getLogger(__name__)

_ENV_CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "30"))
_ENV_BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "30"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize(question: str) -> str:
    """Normalise a question string for duplicate detection."""
    normalized = question.lower().strip()
    normalized = re.sub(r"[?.,;!]+$", "", normalized).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _merge_two_pairs(existing: QnAPair, incoming: QnAPair) -> QnAPair:
    """
    Merge *incoming* into *existing* using local algorithmic rules:
    - Sum frequencies
    - Keep the longest (most detailed) answer
    - Union metadata and category tags
    - Preserve the original ``perguntaPadronizada`` text
    """
    new_freq = existing.frequencia + incoming.frequencia

    ans_existing = existing.respostaConsolidada
    ans_incoming = incoming.respostaConsolidada
    best_answer = ans_incoming if len(ans_incoming.strip()) > len(ans_existing.strip()) else ans_existing

    def _union_tags(a: Optional[str], b: Optional[str]) -> Optional[str]:
        if not a and not b:
            return None
        tags = set()
        if a:
            tags.update(t.strip() for t in a.split(",") if t.strip())
        if b:
            tags.update(t.strip() for t in b.split(",") if t.strip())
        return ", ".join(sorted(tags)) if tags else None

    return QnAPair(
        perguntaPadronizada=existing.perguntaPadronizada,
        respostaConsolidada=best_answer,
        frequencia=new_freq,
        metadata=_union_tags(existing.metadata, incoming.metadata),
        category=_union_tags(existing.category, incoming.category),
    )


# ---------------------------------------------------------------------------
# Public processor class
# ---------------------------------------------------------------------------

class QnaChunkProcessor:
    """
    Chunk-aware Q&A pair processor.

    Args:
        chunk_size: Max pairs per chunk of the main document.
                    Defaults to the ``CHUNK_SIZE`` env var (fallback: 30).
        batch_size: Max pairs per incoming batch.
                    Defaults to the ``BATCH_SIZE`` env var (fallback: 30).
        on_event:   Optional callback invoked with each ``MergerLogEvent``
                    during processing (used by the pipeline to emit SSE events).
    """

    def __init__(
        self,
        chunk_size: int = _ENV_CHUNK_SIZE,
        batch_size: int = _ENV_BATCH_SIZE,
        on_event: Optional[Callable[[MergerLogEvent], None]] = None,
    ) -> None:
        self.chunk_size = max(1, chunk_size)
        self.batch_size = max(1, batch_size)
        self._on_event = on_event

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: MergerLogEventType, message: str, meta: Optional[dict] = None) -> None:
        if self._on_event:
            self._on_event(MergerLogEvent(event_type=event_type, message=message, metadata=meta))

    def _split_into_chunks(self, pairs: List[QnAPair]) -> List[List[QnAPair]]:
        """Split *pairs* into sub-lists of at most ``self.chunk_size`` items."""
        return [pairs[i: i + self.chunk_size] for i in range(0, max(1, len(pairs)), self.chunk_size)]

    def _split_into_batches(self, pairs: List[QnAPair]) -> List[List[QnAPair]]:
        """Split *pairs* into sub-lists of at most ``self.batch_size`` items."""
        if not pairs:
            return []
        return [pairs[i: i + self.batch_size] for i in range(0, len(pairs), self.batch_size)]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        main_pairs: List[QnAPair],
        new_pairs: List[QnAPair],
    ) -> List[QnAPair]:
        """
        Merge *new_pairs* into *main_pairs* using the chunked batch strategy.

        Returns the updated, fully-merged list of ``QnAPair`` objects.

        Complexity: O(B * C) where B = ceil(|new| / batch_size) and
                    C = ceil(|main| / chunk_size).  Suitable for datasets
                    with hundreds of pairs without LLM context overflow.
        """
        if not new_pairs:
            self._emit(
                MergerLogEventType.CHUNK_PROGRESS,
                "Nenhum par novo fornecido — documento principal inalterado.",
            )
            return list(main_pairs)

        # ── 1. Split main document into chunks ──────────────────────────────
        chunks: List[List[QnAPair]] = self._split_into_chunks(list(main_pairs))
        total_chunks = len(chunks)

        # ── 2. Build lookup dicts for each chunk (normalized_q → index) ─────
        chunk_lookups: List[dict] = []
        for chunk in chunks:
            chunk_lookups.append({_normalize(p.perguntaPadronizada): idx for idx, p in enumerate(chunk)})

        # ── 3. Split new pairs into batches ──────────────────────────────────
        batches = self._split_into_batches(new_pairs)
        total_batches = len(batches)
        residuals: List[QnAPair] = []

        self._emit(
            MergerLogEventType.DEDUP_START,
            f"Iniciando mesclagem em chunks: {total_chunks} chunk(s) × {total_batches} lote(s).",
            {"total_chunks": total_chunks, "total_batches": total_batches},
        )

        # ── 4. For each batch, iterate over all chunks ────────────────────
        for b_idx, batch in enumerate(batches):
            unmatched: List[QnAPair] = []

            for pair in batch:
                norm_q = _normalize(pair.perguntaPadronizada)
                matched = False

                for c_idx, (chunk, lookup) in enumerate(zip(chunks, chunk_lookups)):
                    if norm_q in lookup:
                        existing_idx = lookup[norm_q]
                        chunk[existing_idx] = _merge_two_pairs(chunk[existing_idx], pair)
                        matched = True
                        break  # only merge into the first matching chunk

                if not matched:
                    unmatched.append(pair)

            residuals.extend(unmatched)

            self._emit(
                MergerLogEventType.CHUNK_PROGRESS,
                (
                    f"Lote {b_idx + 1}/{total_batches} processado — "
                    f"{len(unmatched)} par(es) sem correspondência."
                ),
                {
                    "batch": b_idx + 1,
                    "total_batches": total_batches,
                    "unmatched": len(unmatched),
                },
            )

        # ── 5. Append residuals that didn't match any existing chunk ────────
        # Deduplicate residuals against each other before appending
        residuals = self._dedup_residuals(residuals)

        # ── 6. Reconstruct the final document from mutated chunks + residuals
        result: List[QnAPair] = []
        for chunk in chunks:
            result.extend(chunk)
        result.extend(residuals)

        self._emit(
            MergerLogEventType.DEDUP_END,
            (
                f"Mesclagem em chunks concluída: {len(result)} par(es) únicos "
                f"({len(residuals)} novo(s) adicionado(s))."
            ),
            {"total_unique": len(result), "new_appended": len(residuals)},
        )

        return result

    def _dedup_residuals(self, residuals: List[QnAPair]) -> List[QnAPair]:
        """Deduplicate the residual list against itself (no cross-chunk duplicates)."""
        seen: dict = {}
        for pair in residuals:
            norm_q = _normalize(pair.perguntaPadronizada)
            if norm_q in seen:
                seen[norm_q] = _merge_two_pairs(seen[norm_q], pair)
            else:
                seen[norm_q] = QnAPair(
                    perguntaPadronizada=pair.perguntaPadronizada,
                    respostaConsolidada=pair.respostaConsolidada,
                    frequencia=pair.frequencia,
                    metadata=pair.metadata,
                    category=pair.category,
                )
        return list(seen.values())
