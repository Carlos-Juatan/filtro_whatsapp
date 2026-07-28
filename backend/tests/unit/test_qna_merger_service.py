import pytest
from models.merger import QnAPair
from services.qna_merger_service import QnAMergerService

def test_normalize_question():
    service = QnAMergerService()
    
    # Test case conversion and whitespace trimming
    assert service.normalize_question("  What is this?  ") == "what is this"
    
    # Test trailing punctuation removal
    assert service.normalize_question("How much?!.") == "how much"
    
    # Test internal whitespace collapsing
    assert service.normalize_question("Why    is   this  happening?") == "why is this happening"
    
def test_merge_qna_pairs_deduplication():
    service = QnAMergerService()
    
    pairs = [
        QnAPair(perguntaPadronizada="What is X?", respostaConsolidada="Short ans", frequencia=1, metadata="tag1"),
        QnAPair(perguntaPadronizada="  what is x  ", respostaConsolidada="Longer answer here", frequencia=2, metadata="tag2", category="cat1"),
        QnAPair(perguntaPadronizada="what is x!?", respostaConsolidada="Mid ans", frequencia=3, category="cat2")
    ]
    
    merged = service.merge_qna_pairs(pairs)
    
    assert len(merged) == 1
    result = merged[0]
    
    # Check that original formatting is preserved from first encountered
    assert result.perguntaPadronizada == "What is X?"
    
    # Frequencies should be summed: 1 + 2 + 3 = 6
    assert result.frequencia == 6
    
    # Longest answer should be selected ("Longer answer here")
    assert result.respostaConsolidada == "Longer answer here"
    
    # Metadata should be merged
    assert result.metadata == "tag1, tag2"
    
    # Categories should be merged
    assert result.category == "cat1, cat2"
    
def test_merge_qna_pairs_unique_questions():
    service = QnAMergerService()
    
    pairs = [
        QnAPair(perguntaPadronizada="Question A?", respostaConsolidada="Ans A", frequencia=1),
        QnAPair(perguntaPadronizada="Question B?", respostaConsolidada="Ans B", frequencia=1)
    ]
    
    merged = service.merge_qna_pairs(pairs)
    
    assert len(merged) == 2
    
def test_merge_qna_pairs_empty_list():
    service = QnAMergerService()
    assert service.merge_qna_pairs([]) == []


# ──────────────────────────────────────────────────────────────────────────────
# T023: consolidate_with_ai() — ChatGPT integration & fallback tests
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


def run(coro):
    """Helper: run an async coroutine in tests (Python 3.12 compatible)."""
    return asyncio.run(coro)


_SAMPLE_PAIRS = [
    QnAPair(perguntaPadronizada="O que é X?", respostaConsolidada="X é algo.", frequencia=2),
    QnAPair(perguntaPadronizada="Como fazer Y?", respostaConsolidada="Fazendo assim.", frequencia=1),
]


def test_consolidate_with_ai_fallback_no_key():
    """When no API key is registered, consolidate_with_ai must return local merge + warning."""
    with patch("services.qna_merger_service.key_storage.get_all", return_value=[]):
        result, warning = run(QnAMergerService.consolidate_with_ai(_SAMPLE_PAIRS))

    assert warning is not None, "Should return a warning string when no key is set."
    assert "ignorada" in warning.lower() or "nenhuma" in warning.lower()
    assert len(result) == len(_SAMPLE_PAIRS)


def test_consolidate_with_ai_success():
    """When an API key exists and OpenAI responds correctly, pairs must be consolidated."""
    from models.schemas import ChaveAPI

    fake_key = ChaveAPI(id="k1", nomeIdentificacao="Test", chave="sk-test")

    ai_response_payload = {
        "qna_pairs": [
            {
                "perguntaPadronizada": "O que é X?",
                "respostaConsolidada": "X é algo consolidado.",
                "frequencia": 3,
                "metadata": None,
                "category": None,
            }
        ]
    }
    raw_json = json.dumps(ai_response_payload)

    mock_choice = MagicMock()
    mock_choice.message.content = raw_json
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_completion)

    with (
        patch("services.qna_merger_service.key_storage.get_all", return_value=[fake_key]),
        patch("services.qna_merger_service.AsyncOpenAI", return_value=mock_openai),
    ):
        result, warning = run(QnAMergerService.consolidate_with_ai(_SAMPLE_PAIRS))

    assert warning is None, "No warning should be returned on successful AI consolidation."
    assert len(result) >= 1
    questions = [p.perguntaPadronizada for p in result]
    assert any("X" in q for q in questions)


def test_consolidate_with_ai_malformed_json_fallback():
    """When ChatGPT returns invalid JSON, service must keep local batch."""
    from models.schemas import ChaveAPI

    fake_key = ChaveAPI(id="k2", nomeIdentificacao="Test2", chave="sk-test2")

    mock_choice = MagicMock()
    mock_choice.message.content = "INVALID JSON {{{"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_completion)

    with (
        patch("services.qna_merger_service.key_storage.get_all", return_value=[fake_key]),
        patch("services.qna_merger_service.AsyncOpenAI", return_value=mock_openai),
    ):
        result, warning = run(QnAMergerService.consolidate_with_ai(_SAMPLE_PAIRS))

    # Malformed JSON returns empty from parser; service keeps local batch as fallback
    assert result is not None
    assert len(result) > 0


def test_consolidate_with_ai_exception_fallback():
    """When the OpenAI API raises an exception, service falls back to local merge + warning."""
    from models.schemas import ChaveAPI

    fake_key = ChaveAPI(id="k3", nomeIdentificacao="Test3", chave="sk-test3")

    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))

    with (
        patch("services.qna_merger_service.key_storage.get_all", return_value=[fake_key]),
        patch("services.qna_merger_service.AsyncOpenAI", return_value=mock_openai),
    ):
        result, warning = run(QnAMergerService.consolidate_with_ai(_SAMPLE_PAIRS))

    assert warning is not None, "Must return a warning when API call fails."
    assert "fallback" in warning.lower() or "falhou" in warning.lower()
    assert len(result) == len(_SAMPLE_PAIRS)


def test_consolidate_with_ai_empty_pairs():
    """Passing an empty pair list should return empty results with no crash."""
    with patch("services.qna_merger_service.key_storage.get_all", return_value=[]):
        result, warning = run(QnAMergerService.consolidate_with_ai([]))

    assert result == []
