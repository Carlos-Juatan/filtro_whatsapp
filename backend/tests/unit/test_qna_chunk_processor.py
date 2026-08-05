"""
Unit tests for QnaChunkProcessor (T032 / FR-013 / FR-014 / SC-005).

Coverage:
- Small batches (<30 pairs, no chunking required)
- Large batches (300+ pairs across multiple chunks)
- Duplicate merging within a single chunk
- Duplicate merging across chunk boundaries
- Configurable CHUNK_SIZE and BATCH_SIZE
- Residual pair handling (no matches → append to result)
- Empty main_pairs and/or new_pairs edge cases
- on_event callback integration (log event emission)
"""

import pytest
from unittest.mock import MagicMock

from src.models.merger import MergerLogEvent, MergerLogEventType, QnAPair
from src.services.qna_chunk_processor import QnaChunkProcessor, _normalize


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _pair(q: str, a: str, freq: int = 1, meta: str | None = None) -> QnAPair:
    return QnAPair(perguntaPadronizada=q, respostaConsolidada=a, frequencia=freq, metadata=meta)


def _unique_questions(pairs: list[QnAPair]) -> list[str]:
    """Return list of all normalized perguntaPadronizada values (for duplicate checks)."""
    return [_normalize(p.perguntaPadronizada) for p in pairs]


# ──────────────────────────────────────────────────────────────────────────────
# Normalization helper tests
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalize:
    def test_lowercases(self):
        assert _normalize("ABC") == "abc"

    def test_strips_trailing_punctuation(self):
        assert _normalize("Qual o preço?") == "qual o preço"

    def test_collapses_internal_whitespace(self):
        assert _normalize("como   funciona  isso") == "como funciona isso"

    def test_combined(self):
        assert _normalize("  Como Funciona?  ") == "como funciona"


# ──────────────────────────────────────────────────────────────────────────────
# Small batch tests (<30 pairs, no chunking needed)
# ──────────────────────────────────────────────────────────────────────────────

class TestSmallBatch:
    def test_no_main_no_new_returns_empty(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        result = proc.process([], [])
        assert result == []

    def test_empty_main_with_new_returns_new(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        new = [_pair("Q1?", "A1"), _pair("Q2?", "A2")]
        result = proc.process([], new)
        assert len(result) == 2

    def test_no_new_returns_main_unchanged(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = [_pair("Q1?", "A1")]
        result = proc.process(main, [])
        assert len(result) == 1
        assert result[0].perguntaPadronizada == "Q1?"

    def test_unique_new_appended_to_main(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = [_pair("Q1?", "A1")]
        new = [_pair("Q2?", "A2")]
        result = proc.process(main, new)
        assert len(result) == 2

    def test_duplicate_in_new_against_main_merged(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = [_pair("Como funciona?", "Funciona assim.", freq=2)]
        new = [_pair("como funciona", "Funciona de outro jeito.", freq=3)]
        result = proc.process(main, new)
        assert len(result) == 1
        assert result[0].frequencia == 5
        assert "jeito" in result[0].respostaConsolidada  # longer answer selected

    def test_case_and_punctuation_deduplication(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = [_pair("Qual o preço?!", "R$ 50,00.", freq=1)]
        new = [_pair("QUAL O PREÇO", "O preço é cinquenta reais.", freq=2)]
        result = proc.process(main, new)
        assert len(result) == 1
        assert result[0].frequencia == 3

    def test_residuals_deduplicated_against_each_other(self):
        """Two new pairs with the same question but no match in main → should merge into 1."""
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        new = [
            _pair("Pergunta Nova?", "Resposta curta.", freq=1),
            _pair("pergunta nova", "Resposta bem mais detalhada.", freq=2),
        ]
        result = proc.process([], new)
        assert len(result) == 1
        assert result[0].frequencia == 3

    def test_metadata_union_on_merge(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = [_pair("Q?", "A", meta="tag1")]
        new = [_pair("Q?", "B", meta="tag2")]
        result = proc.process(main, new)
        assert result[0].metadata is not None
        assert "tag1" in result[0].metadata
        assert "tag2" in result[0].metadata


# ──────────────────────────────────────────────────────────────────────────────
# Large batch tests (300+ pairs across multiple chunks, SC-005)
# ──────────────────────────────────────────────────────────────────────────────

class TestLargeBatch:
    def _make_pairs(self, n: int, prefix: str = "Q") -> list[QnAPair]:
        return [_pair(f"{prefix}{i}?", f"Resposta {i}", freq=1) for i in range(n)]

    def test_300_unique_pairs_all_present(self):
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        new = self._make_pairs(300)
        result = proc.process([], new)
        assert len(result) == 300
        # All normalized questions must be unique (SC-001)
        norms = _unique_questions(result)
        assert len(norms) == len(set(norms)), "Duplicate questions found in output"

    def test_300_pairs_with_50_duplicates(self):
        """50 of the 300 new pairs duplicate entries in the main document."""
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = self._make_pairs(50, prefix="Q")     # Q0..Q49 in main
        new = self._make_pairs(300, prefix="Q")     # Q0..Q299 in new (Q0..Q49 are dups)
        result = proc.process(main, new)
        # Expect 300 unique questions: Q0..Q299
        # Q0..Q49 merged (freq 2), Q50..Q299 appended (freq 1)
        assert len(result) == 300
        norms = _unique_questions(result)
        assert len(norms) == len(set(norms)), "Duplicate questions found in large merge output"

    def test_all_duplicates_reduces_to_main_size(self):
        """If all new pairs are duplicates of main, no growth in output size."""
        proc = QnaChunkProcessor(chunk_size=30, batch_size=30)
        main = self._make_pairs(60, prefix="X")
        new = self._make_pairs(60, prefix="X")     # All duplicates
        result = proc.process(main, new)
        assert len(result) == 60
        # Frequencies should all be 2
        assert all(p.frequencia == 2 for p in result)

    def test_large_batch_no_duplicates_with_small_chunks(self):
        """250 unique new pairs against a main with CHUNK_SIZE=10 → all appended correctly."""
        proc = QnaChunkProcessor(chunk_size=10, batch_size=20)
        main = self._make_pairs(10, prefix="M")
        new = self._make_pairs(250, prefix="N")   # All unique vs main
        result = proc.process(main, new)
        assert len(result) == 260   # 10 main + 250 new
        norms = _unique_questions(result)
        assert len(norms) == len(set(norms))


# ──────────────────────────────────────────────────────────────────────────────
# Cross-chunk boundary duplicate merging
# ──────────────────────────────────────────────────────────────────────────────

class TestCrossChunkBoundary:
    def test_duplicate_found_in_second_chunk(self):
        """New pair matches a question in the 2nd chunk (not the 1st)."""
        # Build a main doc where q_target is in the 2nd chunk
        main = [_pair(f"Main{i}?", f"A{i}") for i in range(10)]
        main.append(_pair("Target?", "Original answer.", freq=2))
        # chunk_size=5 → chunk0=[Main0..Main4], chunk1=[Main5..Main9], chunk2=[Target]
        proc = QnaChunkProcessor(chunk_size=5, batch_size=10)
        new = [_pair("target", "Improved answer that is definitely longer.", freq=1)]
        result = proc.process(main, new)
        # Total: 11 unique (Main0..Main9, Target)
        assert len(result) == 11
        target_pair = next(p for p in result if "target" in _normalize(p.perguntaPadronizada))
        assert target_pair.frequencia == 3
        assert "Improved" in target_pair.respostaConsolidada


# ──────────────────────────────────────────────────────────────────────────────
# Configurable CHUNK_SIZE and BATCH_SIZE
# ──────────────────────────────────────────────────────────────────────────────

class TestConfigurableParameters:
    def test_chunk_size_1_processes_all_pairs(self):
        """Extreme chunk_size=1 still produces correct results."""
        proc = QnaChunkProcessor(chunk_size=1, batch_size=5)
        main = [_pair(f"Q{i}?", f"A{i}") for i in range(5)]
        new = [_pair(f"Q{i}?", f"Better A{i}", freq=2) for i in range(5)]
        result = proc.process(main, new)
        assert len(result) == 5
        assert all(p.frequencia == 3 for p in result)

    def test_batch_size_1_processes_all_pairs(self):
        """batch_size=1 (one pair per batch) still merges correctly."""
        proc = QnaChunkProcessor(chunk_size=10, batch_size=1)
        main = [_pair("Solo?", "Base answer.")]
        new = [_pair("solo", "Improved and longer base answer.", freq=4)]
        result = proc.process(main, new)
        assert len(result) == 1
        assert result[0].frequencia == 5

    def test_chunk_size_larger_than_main(self):
        """chunk_size > len(main_pairs) → single chunk; still works."""
        proc = QnaChunkProcessor(chunk_size=1000, batch_size=30)
        main = [_pair(f"Q{i}?", f"A{i}") for i in range(15)]
        new = [_pair(f"Q{i}?", f"Better A{i}", freq=2) for i in range(15)]
        result = proc.process(main, new)
        assert len(result) == 15
        assert all(p.frequencia == 3 for p in result)


# ──────────────────────────────────────────────────────────────────────────────
# on_event callback / log emission
# ──────────────────────────────────────────────────────────────────────────────

class TestLogEventEmission:
    def test_on_event_called_during_processing(self):
        captured: list[MergerLogEvent] = []
        proc = QnaChunkProcessor(
            chunk_size=5,
            batch_size=5,
            on_event=lambda ev: captured.append(ev),
        )
        main = [_pair(f"Q{i}?", f"A{i}") for i in range(5)]
        new = [_pair("Q0?", "Longer answer for Q0."), _pair("NEW?", "Brand new.")]
        proc.process(main, new)

        event_types = [ev.event_type for ev in captured]
        assert MergerLogEventType.DEDUP_START in event_types
        assert MergerLogEventType.CHUNK_PROGRESS in event_types
        assert MergerLogEventType.DEDUP_END in event_types

    def test_no_callback_does_not_raise(self):
        """When on_event is None, processing must complete silently."""
        proc = QnaChunkProcessor(chunk_size=5, batch_size=5, on_event=None)
        result = proc.process([_pair("A?", "ans")], [_pair("B?", "ans2")])
        assert len(result) == 2

    def test_event_metadata_contains_chunk_info(self):
        captured: list[MergerLogEvent] = []
        proc = QnaChunkProcessor(
            chunk_size=3,
            batch_size=3,
            on_event=lambda ev: captured.append(ev),
        )
        main = [_pair(f"Q{i}?", f"A{i}") for i in range(6)]  # 2 chunks of 3
        new = [_pair(f"Q{i}?", f"Better A{i}") for i in range(3)]
        proc.process(main, new)

        chunk_events = [ev for ev in captured if ev.event_type == MergerLogEventType.CHUNK_PROGRESS]
        assert len(chunk_events) >= 1
        for ev in chunk_events:
            assert ev.metadata is not None
            assert "batch" in ev.metadata
            assert "total_batches" in ev.metadata
