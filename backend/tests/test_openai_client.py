"""
Unit tests for openai_client – prompt construction and response parsing
of the new uncategorized_database_content field (T006 / US1).

Tests are pure in-memory: no network calls, no OpenAI API required.
"""

import json
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# _parse_qna_response — new uncategorized_database_content parsing
# ─────────────────────────────────────────────────────────────────────────────


class TestParseQnaResponseWithUncategorized:
    """Tests for parsing uncategorized_database_content from LLM JSON responses."""

    def test_valid_json_with_uncategorized_returns_both(self):
        """When the model returns both qna_pairs and uncategorized_database_content,
        both should be parsed correctly."""
        from src.services.openai_client import _parse_qna_response

        raw = json.dumps({
            "qna_pairs": [
                {"question": "Qual o horário?", "answer": "8h às 18h.", "frequency": 1, "metadata": "horário", "category": "FAQ"},
            ],
            "uncategorized_database_content": [
                "O frete é gratuito para compras acima de R$ 100,00.",
                "Não realizamos entregas aos domingos.",
            ],
        })
        pairs, uncategorized = _parse_qna_response(raw)
        assert len(pairs) == 1
        assert len(uncategorized) == 2
        assert "O frete é gratuito para compras acima de R$ 100,00." in uncategorized
        assert "Não realizamos entregas aos domingos." in uncategorized

    def test_missing_uncategorized_key_returns_empty_list(self):
        """When the model omits uncategorized_database_content, parsing should
        return an empty list for it (backward-compatible)."""
        from src.services.openai_client import _parse_qna_response

        raw = json.dumps({
            "qna_pairs": [
                {"question": "Q?", "answer": "A.", "frequency": 1, "metadata": None, "category": "Geral"},
            ],
        })
        pairs, uncategorized = _parse_qna_response(raw)
        assert len(pairs) == 1
        assert uncategorized == []

    def test_empty_uncategorized_returns_empty_list(self):
        """An explicit empty list for uncategorized_database_content is valid."""
        from src.services.openai_client import _parse_qna_response

        raw = json.dumps({
            "qna_pairs": [],
            "uncategorized_database_content": [],
        })
        pairs, uncategorized = _parse_qna_response(raw)
        assert pairs == []
        assert uncategorized == []

    def test_non_string_items_in_uncategorized_are_cast_to_str(self):
        """Non-string items in uncategorized_database_content should be safely cast."""
        from src.services.openai_client import _parse_qna_response

        raw = json.dumps({
            "qna_pairs": [],
            "uncategorized_database_content": ["Texto válido", 42, None],
        })
        pairs, uncategorized = _parse_qna_response(raw)
        # '42' and 'None' should be cast/filtered gracefully
        assert "Texto válido" in uncategorized
        # None should be filtered out or cast; test just confirms no crash
        assert isinstance(uncategorized, list)

    def test_markdown_fences_stripped_with_uncategorized(self):
        """Markdown code fences should still be stripped when uncategorized is present."""
        from src.services.openai_client import _parse_qna_response

        inner = json.dumps({
            "qna_pairs": [{"question": "P?", "answer": "R.", "frequency": 1, "metadata": None, "category": "Geral"}],
            "uncategorized_database_content": ["Afirmação importante."],
        })
        raw = f"```json\n{inner}\n```"
        pairs, uncategorized = _parse_qna_response(raw)
        assert len(pairs) == 1
        assert uncategorized == ["Afirmação importante."]

    def test_invalid_json_still_raises(self):
        """Invalid JSON should still raise a ValueError."""
        from src.services.openai_client import _parse_qna_response

        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_qna_response("not json at all")

    def test_uncategorized_items_are_stripped(self):
        """Whitespace around uncategorized items should be stripped."""
        from src.services.openai_client import _parse_qna_response

        raw = json.dumps({
            "qna_pairs": [],
            "uncategorized_database_content": ["  Afirmação com espaços  ", "\tTabulação\n"],
        })
        _, uncategorized = _parse_qna_response(raw)
        assert "Afirmação com espaços" in uncategorized
        assert "Tabulação" in uncategorized


# ─────────────────────────────────────────────────────────────────────────────
# _build_system_prompt — CUSTOMIZADO suffix injection
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildSystemPromptCustomizado:
    """Tests for _build_system_prompt to verify the uncategorized suffix is appended
    to CUSTOMIZADO prompts (FR-001)."""

    def _make_custom_prompt(self, texto: str, palavras_chave=None):
        from src.models.schemas import ModeloOpenAI, PromptConfig, TipoPrompt

        return PromptConfig(
            id="test-id",
            nome="Test Custom",
            tipo=TipoPrompt.CUSTOMIZADO,
            textoInstrucao=texto,
            palavrasChave=palavras_chave or [],
            idiomaModelo="pt-br",
            modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
        )

    def test_custom_prompt_includes_uncategorized_suffix(self):
        """CUSTOMIZADO prompts must have the uncategorized extraction instruction appended."""
        from src.services.openai_client import _build_system_prompt

        config = self._make_custom_prompt("Extraia perguntas e respostas do texto.")
        result = _build_system_prompt(config)
        assert "uncategorized_database_content" in result

    def test_custom_prompt_preserves_original_text(self):
        """The original user instruction text should still be present."""
        from src.services.openai_client import _build_system_prompt

        original = "Meu prompt personalizado de extração."
        config = self._make_custom_prompt(original)
        result = _build_system_prompt(config)
        assert original in result

    def test_fixo_prompt_does_not_duplicate_suffix(self):
        """FIXO prompts already include the uncategorized instruction — no double appending."""
        from src.models.schemas import ModeloOpenAI, PromptConfig, TipoPrompt
        from src.services.openai_client import _build_system_prompt

        config = PromptConfig(
            id="fixo-id",
            nome="Padrão do Sistema",
            tipo=TipoPrompt.FIXO,
            textoInstrucao="Instrução padrão já completa.",
            palavrasChave=[],
            idiomaModelo="pt-br",
            modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
        )
        result = _build_system_prompt(config)
        # The FIXO prompt should use its textoInstrucao as-is
        assert result == "Instrução padrão já completa."

    def test_none_config_uses_default_prompt(self):
        """When no config is given, the default system prompt is used (which now includes uncategorized instruction)."""
        from src.services.openai_client import _build_system_prompt
        from src.services.prompt_storage import DEFAULT_SYSTEM_PROMPT_TEXT

        result = _build_system_prompt(None)
        assert result == DEFAULT_SYSTEM_PROMPT_TEXT
        assert "uncategorized_database_content" in result
