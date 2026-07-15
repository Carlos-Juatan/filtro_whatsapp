"""
Unit tests for the chunker, parsers, and WebSocket processor (User Story 1).

Test coverage:
  - parsers.py: TxtParser and ParserFactory
  - chunker.py: split_text, count_tokens, edge cases
  - websocket.py: _parse_qna_response (via openai_client), helper functions

Run with:
    cd backend && pytest tests/test_processing.py -v
"""

from __future__ import annotations

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Parsers tests
# ──────────────────────────────────────────────────────────────────────────────


class TestTxtParser:
    """Tests for TxtParser."""

    def test_parse_utf8_bytes_returns_string(self):
        from src.services.parsers import TxtParser

        parser = TxtParser()
        content = "Olá, mundo!".encode("utf-8")
        result = parser.parse(content)
        assert isinstance(result, str)
        assert result == "Olá, mundo!"

    def test_parse_normalises_crlf(self):
        from src.services.parsers import TxtParser

        parser = TxtParser()
        content = b"linha 1\r\nlinha 2\r\nlinha 3"
        result = parser.parse(content)
        assert "\r" not in result
        assert result == "linha 1\nlinha 2\nlinha 3"

    def test_parse_handles_invalid_utf8_gracefully(self):
        from src.services.parsers import TxtParser

        parser = TxtParser()
        # Embed an invalid byte sequence
        content = b"texto v\xe1lido"  # \xe1 alone is invalid in UTF-8
        result = parser.parse(content)
        assert isinstance(result, str)
        # Invalid bytes should be silently replaced
        assert "texto v" in result

    def test_parse_empty_bytes(self):
        from src.services.parsers import TxtParser

        parser = TxtParser()
        assert parser.parse(b"") == ""


class TestParserFactory:
    """Tests for ParserFactory."""

    def test_get_parser_txt_lowercase(self):
        from src.services.parsers import ParserFactory, TxtParser

        parser = ParserFactory.get_parser(".txt")
        assert isinstance(parser, TxtParser)

    def test_get_parser_txt_uppercase(self):
        from src.services.parsers import ParserFactory, TxtParser

        parser = ParserFactory.get_parser(".TXT")
        assert isinstance(parser, TxtParser)

    def test_get_parser_unsupported_raises_value_error(self):
        from src.services.parsers import ParserFactory

        with pytest.raises(ValueError, match="Unsupported file format"):
            ParserFactory.get_parser(".pdf")

    def test_supported_extensions_contains_txt(self):
        from src.services.parsers import ParserFactory

        exts = ParserFactory.supported_extensions()
        assert ".txt" in exts

    def test_get_parser_with_spaces(self):
        from src.services.parsers import ParserFactory, TxtParser

        # Leading/trailing whitespace should be stripped
        parser = ParserFactory.get_parser("  .txt  ")
        assert isinstance(parser, TxtParser)


# ──────────────────────────────────────────────────────────────────────────────
# Chunker tests
# ──────────────────────────────────────────────────────────────────────────────


class TestCountTokens:
    """Tests for the count_tokens helper."""

    def test_empty_string_is_zero(self):
        from src.services.chunker import count_tokens

        assert count_tokens("") == 0

    def test_simple_ascii_word(self):
        from src.services.chunker import count_tokens

        # "hello" is 1 token in cl100k_base
        count = count_tokens("hello")
        assert count >= 1

    def test_longer_text_more_tokens(self):
        from src.services.chunker import count_tokens

        short = count_tokens("hello")
        long = count_tokens("hello world this is a longer sentence with more tokens")
        assert long > short


class TestSplitText:
    """Tests for split_text."""

    def test_empty_string_returns_empty_list(self):
        from src.services.chunker import split_text

        assert split_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        from src.services.chunker import split_text

        assert split_text("   \n\n  ") == []

    def test_short_text_returns_single_chunk(self):
        from src.services.chunker import split_text

        text = "Qual o horário de atendimento? Das 8h às 18h."
        chunks = split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text.strip()

    def test_large_text_splits_into_multiple_chunks(self):
        from src.services.chunker import count_tokens, split_text

        # Generate a text that is definitely > 8000 tokens
        sentence = "Esta é uma frase de teste para verificar o fatiamento de texto. "
        # Each sentence is ~15 tokens; 1000 repetitions ≈ 15k tokens
        text = sentence * 1000
        chunks = split_text(text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert count_tokens(chunk) <= 8000

    def test_all_chunks_non_empty(self):
        from src.services.chunker import split_text

        text = "linha 1\n\nlinha 2\n\nlinha 3"
        chunks = split_text(text)
        assert all(c.strip() for c in chunks)

    def test_max_tokens_respected(self):
        from src.services.chunker import count_tokens, split_text

        # Use a very small max_tokens to force splitting
        text = "Um dois três quatro cinco seis sete oito nove dez " * 50
        chunks = split_text(text, max_tokens=20)
        for chunk in chunks:
            assert count_tokens(chunk) <= 20

    def test_invalid_max_tokens_raises(self):
        from src.services.chunker import split_text

        with pytest.raises(ValueError):
            split_text("texto qualquer", max_tokens=0)

    def test_paragraph_split_preserves_content(self):
        from src.services.chunker import split_text

        paragraphs = ["Parágrafo " + str(i) + " " + ("x " * 50) for i in range(20)]
        text = "\n\n".join(paragraphs)
        chunks = split_text(text, max_tokens=100)
        # All paragraph content should be present across chunks
        full = " ".join(chunks)
        for i in range(20):
            assert f"Parágrafo {i}" in full


# ──────────────────────────────────────────────────────────────────────────────
# OpenAI client – response parser tests (no network required)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseQnaResponse:
    """Tests for _parse_qna_response (internal, imported directly for testing)."""

    def test_valid_json_returns_list(self):
        from src.services.openai_client import _parse_qna_response

        raw = '{"qna_pairs": [{"question": "Qual o horário?", "answer": "8h às 18h.", "frequency": 2, "metadata": "horário", "category": "Suporte"}]}'
        result = _parse_qna_response(raw)
        assert len(result) == 1
        assert result[0].perguntaPadronizada == "Qual o horário?"
        assert result[0].respostaConsolidada == "8h às 18h."
        assert result[0].frequencia == 2
        assert result[0].category == "Suporte"

    def test_markdown_fences_stripped(self):
        from src.services.openai_client import _parse_qna_response

        raw = '```json\n{"qna_pairs": [{"question": "P?", "answer": "R.", "frequency": 1, "metadata": null, "category": "Geral"}]}\n```'
        result = _parse_qna_response(raw)
        assert len(result) == 1

    def test_empty_qna_pairs_returns_empty_list(self):
        from src.services.openai_client import _parse_qna_response

        result = _parse_qna_response('{"qna_pairs": []}')
        assert result == []

    def test_missing_qna_pairs_key_raises_value_error(self):
        from src.services.openai_client import _parse_qna_response

        with pytest.raises(ValueError, match="qna_pairs"):
            _parse_qna_response('{"something_else": []}')

    def test_invalid_json_raises_value_error(self):
        from src.services.openai_client import _parse_qna_response

        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_qna_response("not json at all")

    def test_frequency_clamped_to_minimum_1(self):
        from src.services.openai_client import _parse_qna_response

        raw = '{"qna_pairs": [{"question": "Q?", "answer": "A.", "frequency": -5, "metadata": null, "category": "X"}]}'
        result = _parse_qna_response(raw)
        assert result[0].frequencia == 1

    def test_missing_category_defaults_to_geral(self):
        from src.services.openai_client import _parse_qna_response

        raw = '{"qna_pairs": [{"question": "Q?", "answer": "A.", "frequency": 1, "metadata": null}]}'
        result = _parse_qna_response(raw)
        assert result[0].category == "Geral"

    def test_multiple_pairs(self):
        from src.services.openai_client import _parse_qna_response

        raw = """{"qna_pairs": [
            {"question": "Q1?", "answer": "A1.", "frequency": 1, "metadata": null, "category": "Cat1"},
            {"question": "Q2?", "answer": "A2.", "frequency": 3, "metadata": "tag", "category": "Cat2"}
        ]}"""
        result = _parse_qna_response(raw)
        assert len(result) == 2
        assert result[1].frequencia == 3
