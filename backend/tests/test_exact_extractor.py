"""
Tests for exact_extractor.py

Covers (T007):
  - Chunk splitting with overlap (_build_chunks)
  - Deduplication of pairs from overlapping chunks
  - Resilience to malformed/truncated LLM JSON (via mocked client)
  - reconstruct_pairs: exact text fidelity
  - reconstruct_pairs: skipping invalid IDs
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.exact_qa import (
    ChunkConfig,
    LLMQAPairMapping,
    RawMessage,
)
from src.services.exact_extractor import (
    ExactExtractorService,
    _build_chunks,
    _format_chunk_for_llm,
    MEDIA_PLACEHOLDER_PATTERNS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_messages(n: int) -> list[RawMessage]:
    return [
        RawMessage(id=f"MSG-{i:04d}", sender=f"User{i}", content=f"Mensagem número {i}")
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# _build_chunks — chunk splitting with overlap (T002)
# ---------------------------------------------------------------------------

class TestBuildChunks:
    def test_single_chunk_when_messages_fit(self):
        msgs = make_messages(50)
        cfg = ChunkConfig(chunk_size=100, overlap=20)
        chunks = _build_chunks(msgs, cfg)
        assert len(chunks) == 1
        assert len(chunks[0]) == 50

    def test_exact_chunk_boundary(self):
        msgs = make_messages(100)
        cfg = ChunkConfig(chunk_size=100, overlap=20)
        chunks = _build_chunks(msgs, cfg)
        assert len(chunks) == 1
        assert len(chunks[0]) == 100

    def test_two_chunks_with_overlap(self):
        msgs = make_messages(110)
        cfg = ChunkConfig(chunk_size=100, overlap=20)
        chunks = _build_chunks(msgs, cfg)
        # step = 100 - 20 = 80 → chunk 1: [0..99], chunk 2: [80..109]
        assert len(chunks) == 2
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 30

    def test_overlap_produces_shared_messages(self):
        msgs = make_messages(110)
        cfg = ChunkConfig(chunk_size=100, overlap=20)
        chunks = _build_chunks(msgs, cfg)
        # The last 20 messages of chunk 1 should be the first 20 messages of chunk 2
        overlap_ids_from_chunk1 = {m.id for m in chunks[0][-20:]}
        overlap_ids_from_chunk2 = {m.id for m in chunks[1][:20]}
        assert overlap_ids_from_chunk1 == overlap_ids_from_chunk2

    def test_many_chunks(self):
        msgs = make_messages(300)
        cfg = ChunkConfig(chunk_size=100, overlap=20)
        chunks = _build_chunks(msgs, cfg)
        # step=80: 0, 80, 160, 240 → 4 chunks
        assert len(chunks) == 4

    def test_empty_messages(self):
        chunks = _build_chunks([], ChunkConfig())
        assert chunks == []

    def test_no_overlap(self):
        msgs = make_messages(200)
        cfg = ChunkConfig(chunk_size=100, overlap=0)
        chunks = _build_chunks(msgs, cfg)
        assert len(chunks) == 2


# ---------------------------------------------------------------------------
# _format_chunk_for_llm — serialization
# ---------------------------------------------------------------------------

class TestFormatChunk:
    def test_format_with_sender(self):
        msgs = [RawMessage(id="MSG-0001", sender="Ana", content="Qual o horário?")]
        result = _format_chunk_for_llm(msgs)
        assert result == "[MSG-0001] Ana: Qual o horário?"

    def test_format_without_sender(self):
        msgs = [RawMessage(id="MSG-0001", sender=None, content="Olá!")]
        result = _format_chunk_for_llm(msgs)
        assert result == "[MSG-0001] Olá!"

    def test_format_multiple_messages(self):
        msgs = [
            RawMessage(id="MSG-0001", sender="A", content="Pergunta"),
            RawMessage(id="MSG-0002", sender="B", content="Resposta"),
        ]
        result = _format_chunk_for_llm(msgs)
        assert "[MSG-0001] A: Pergunta" in result
        assert "[MSG-0002] B: Resposta" in result


# ---------------------------------------------------------------------------
# reconstruct_pairs
# ---------------------------------------------------------------------------

class TestReconstructPairs:
    def setup_method(self):
        self.service = ExactExtractorService()
        self.messages = [
            RawMessage(id="MSG-0001", timestamp="10:00", sender="Joao", content="Qual o valor? 🐶"),
            RawMessage(id="MSG-0002", timestamp="10:01", sender="Clinica", content="R$ 120,00."),
            RawMessage(id="MSG-0003", timestamp="10:02", sender="Joao", content="Aceitam cartão?"),
            RawMessage(id="MSG-0004", timestamp="10:03", sender="Clinica", content="Sim, todos."),
        ]

    def test_exact_text_fidelity(self):
        mappings = [LLMQAPairMapping(question_id="MSG-0001", answer_id="MSG-0002")]
        pairs = self.service.reconstruct_pairs(self.messages, mappings)
        assert len(pairs) == 1
        assert pairs[0].question_text == "Qual o valor? 🐶"
        assert pairs[0].answer_text == "R$ 120,00."

    def test_metadata_populated(self):
        mappings = [LLMQAPairMapping(question_id="MSG-0001", answer_id="MSG-0002")]
        pairs = self.service.reconstruct_pairs(self.messages, mappings)
        assert pairs[0].metadata["question_sender"] == "Joao"
        assert pairs[0].metadata["answer_sender"] == "Clinica"
        assert pairs[0].metadata["question_timestamp"] == "10:00"

    def test_pair_ids_sequential(self):
        mappings = [
            LLMQAPairMapping(question_id="MSG-0001", answer_id="MSG-0002"),
            LLMQAPairMapping(question_id="MSG-0003", answer_id="MSG-0004"),
        ]
        pairs = self.service.reconstruct_pairs(self.messages, mappings)
        assert pairs[0].id == "PAIR-0001"
        assert pairs[1].id == "PAIR-0002"

    def test_invalid_id_skipped(self):
        mappings = [
            LLMQAPairMapping(question_id="MSG-9999", answer_id="MSG-0002"),  # invalid question
        ]
        pairs = self.service.reconstruct_pairs(self.messages, mappings)
        assert len(pairs) == 0

    def test_empty_mappings(self):
        pairs = self.service.reconstruct_pairs(self.messages, [])
        assert pairs == []

    def test_empty_messages(self):
        pairs = self.service.reconstruct_pairs([], [LLMQAPairMapping(question_id="MSG-0001", answer_id="MSG-0002")])
        assert pairs == []


# ---------------------------------------------------------------------------
# Deduplication across chunks (T005)
# ---------------------------------------------------------------------------

class TestDeduplication:
    """
    Tests that pairs appearing in the overlap region of adjacent chunks
    are deduped deterministically (only the first occurrence is kept).
    """

    def setup_method(self):
        self.service = ExactExtractorService()

    def _make_mock_client(self, responses: list[dict]) -> AsyncMock:
        """Creates an AsyncOpenAI mock that returns responses in sequence."""
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            resp_data = responses[call_count % len(responses)]
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.choices[0].message.content = json.dumps(resp_data)
            return mock_resp

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = fake_create
        return mock_client

    @pytest.mark.asyncio
    async def test_deduplication_of_overlap_pairs(self):
        """Pair (MSG-0080, MSG-0081) appears in chunk 1 and chunk 2 due to overlap — must appear only once."""
        msgs = make_messages(110)  # step=80 → chunks: [0..99], [80..109]

        # chunk 1 returns a pair that is also in the overlap zone
        chunk1_response = {"pairs": [{"question_id": "MSG-0080", "answer_id": "MSG-0081"}]}
        # chunk 2 sees the same pair in its overlap region
        chunk2_response = {"pairs": [
            {"question_id": "MSG-0080", "answer_id": "MSG-0081"},  # duplicate
            {"question_id": "MSG-0090", "answer_id": "MSG-0091"},  # new pair
        ]}

        with patch("src.services.exact_extractor.AsyncOpenAI") as MockOpenAI:
            mock_instance = self._make_mock_client([chunk1_response, chunk2_response])
            MockOpenAI.return_value = mock_instance

            result = await self.service.extract_mappings_with_llm(
                raw_messages=msgs,
                api_key="fake-key",
                chunk_config=ChunkConfig(chunk_size=100, overlap=20),
            )

        ids = [(m.question_id, m.answer_id) for m in result]
        assert ("MSG-0080", "MSG-0081") in ids
        assert ("MSG-0090", "MSG-0091") in ids
        # Ensure no duplicates
        assert len(ids) == len(set(ids))
        assert len(ids) == 2


# ---------------------------------------------------------------------------
# Resilience to malformed LLM JSON (T003)
# ---------------------------------------------------------------------------

class TestLLMResilience:
    def setup_method(self):
        self.service = ExactExtractorService()

    def _make_sequential_client(self, side_effects: list) -> MagicMock:
        """
        Creates a mock OpenAI client where completions.create raises or returns
        based on side_effects list (each element is either an Exception or a dict).
        """
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            effect = side_effects[min(call_count, len(side_effects) - 1)]
            call_count += 1
            if isinstance(effect, Exception):
                raise effect
            mock_resp = MagicMock()
            mock_resp.choices[0].message.content = json.dumps(effect)
            return mock_resp

        mock_client = MagicMock()
        mock_client.chat.completions.create = fake_create
        return mock_client

    @pytest.mark.asyncio
    async def test_json_decode_error_retries_and_recovers(self):
        """After a JSONDecodeError, the service retries and returns the valid result on 2nd attempt."""
        msgs = make_messages(5)
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            if call_count == 1:
                # First call returns truncated/invalid JSON
                mock_resp.choices[0].message.content = '{"pairs": [{"question_id": "MSG-0001"'  # truncated
            else:
                mock_resp.choices[0].message.content = json.dumps(
                    {"pairs": [{"question_id": "MSG-0001", "answer_id": "MSG-0002"}]}
                )
            return mock_resp

        with patch("src.services.exact_extractor.AsyncOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = fake_create
            MockOpenAI.return_value = mock_instance

            result = await self.service._call_llm_for_chunk(
                chunk=msgs,
                client=mock_instance,
                model="gpt-4o-mini",
                max_retries=2,
                retry_delay=0.0,
            )

        assert len(result) == 1
        assert result[0].question_id == "MSG-0001"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_json_decode_error_exhausts_retries_returns_empty(self):
        """After exhausting all retries, the service returns an empty list (no crash)."""
        msgs = make_messages(5)
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.choices[0].message.content = '{"pairs": [INVALID'  # always broken
            return mock_resp

        with patch("src.services.exact_extractor.AsyncOpenAI") as MockOpenAI:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create = fake_create
            MockOpenAI.return_value = mock_instance

            result = await self.service._call_llm_for_chunk(
                chunk=msgs,
                client=mock_instance,
                model="gpt-4o-mini",
                max_retries=2,
                retry_delay=0.0,
            )

        assert result == []
        assert call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty(self):
        result = await self.service.extract_mappings_with_llm(
            raw_messages=[], api_key="fake"
        )
        assert result == []


# ---------------------------------------------------------------------------
# Media placeholder filter constants
# ---------------------------------------------------------------------------

class TestPlaceholderPatterns:
    def test_known_placeholders_in_set(self):
        assert "<mídia omitida>" in MEDIA_PLACEHOLDER_PATTERNS
        assert "<ficheiro não revelado>" in MEDIA_PLACEHOLDER_PATTERNS
        assert "<media omitted>" in MEDIA_PLACEHOLDER_PATTERNS

    def test_case_insensitive_matching(self):
        content = "<Mídia Omitida>"
        assert content.lower() in MEDIA_PLACEHOLDER_PATTERNS
