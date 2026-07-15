import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models.schemas import ResultadoParPR, ModeloOpenAI
from src.services.consolidator import consolidate_qna_pairs

@pytest.fixture
def mock_pairs():
    return [
        ResultadoParPR(
            perguntaPadronizada="Qual o horário de funcionamento?",
            respostaConsolidada="Das 8h às 18h.",
            frequencia=1,
            metadata="horario",
            category="Atendimento"
        ),
        ResultadoParPR(
            perguntaPadronizada="Qual o horário de funcionamento?",
            respostaConsolidada="Das 8h às 18h.",
            frequencia=2,
            metadata="loja",
            category="Atendimento"
        ),
        ResultadoParPR(
            perguntaPadronizada="Vocês entregam?",
            respostaConsolidada="Sim, entregamos em todo Brasil.",
            frequencia=1,
            metadata="frete",
            category="Logística"
        )
    ]

@pytest.mark.anyio
async def test_consolidate_qna_pairs_local_reduction(mock_pairs):
    # Test local exact match reduction when LLM call fails
    with patch("src.services.consolidator.AsyncOpenAI") as mock_openai:
        # Mock the client to raise an Exception
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        result = await consolidate_qna_pairs(mock_pairs, api_key="test-key")
        
        assert len(result) == 2
        # Verify the first two are merged (they have exact same question/answer)
        horario = next(p for p in result if "horário" in p.perguntaPadronizada)
        assert horario.frequencia == 3
        assert "horario" in horario.metadata
        assert "loja" in horario.metadata

@pytest.mark.anyio
async def test_consolidate_qna_pairs_llm_success(mock_pairs):
    # Test successful LLM consolidation
    with patch("src.services.consolidator.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        
        # Mock response payload
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"qna_pairs": [{"question": "Horário de funcionamento unificado?", "answer": "8 as 18", "frequency": 5, "metadata": "tudo", "category": "Geral"}]}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        result = await consolidate_qna_pairs(mock_pairs, api_key="test-key")
        
        assert len(result) == 1
        assert result[0].perguntaPadronizada == "Horário de funcionamento unificado?"
        assert result[0].frequencia == 5

@pytest.mark.anyio
async def test_consolidate_empty_or_single():
    assert await consolidate_qna_pairs([], "test") == []
    
    single = [
        ResultadoParPR(
            perguntaPadronizada="Q",
            respostaConsolidada="A",
            frequencia=1,
            category="C"
        )
    ]
    assert await consolidate_qna_pairs(single, "test") == single


# ─────────────────────────────────────────────────────────────────────────────
# T008: Tests for deduplicate_uncategorized helper (US1 / FR-004)
# ─────────────────────────────────────────────────────────────────────────────


class TestDeduplicateUncategorized:
    """Tests for the deduplicate_uncategorized utility in consolidator.py."""

    def test_empty_list_returns_empty_list(self):
        from src.services.consolidator import deduplicate_uncategorized
        assert deduplicate_uncategorized([]) == []

    def test_single_item_list_returned_unchanged(self):
        from src.services.consolidator import deduplicate_uncategorized
        result = deduplicate_uncategorized(["Fato único."])
        assert result == ["Fato único."]

    def test_exact_duplicates_removed(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["Fato A.", "Fato B.", "Fato A."]
        result = deduplicate_uncategorized(items)
        assert len(result) == 2
        assert "Fato A." in result
        assert "Fato B." in result

    def test_case_insensitive_deduplication(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["Entregamos de segunda a sexta.", "entregamos de segunda a sexta.", "ENTREGAMOS DE SEGUNDA A SEXTA."]
        result = deduplicate_uncategorized(items)
        assert len(result) == 1

    def test_original_casing_of_first_occurrence_preserved(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["Horário: 8h às 18h.", "horário: 8h às 18h."]
        result = deduplicate_uncategorized(items)
        assert result == ["Horário: 8h às 18h."]

    def test_leading_trailing_whitespace_stripped(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["  Fato com espaços.  ", "Fato com espaços.", "\tFato com espaços.\n"]
        result = deduplicate_uncategorized(items)
        assert len(result) == 1
        assert result[0] == "Fato com espaços."

    def test_whitespace_only_items_are_excluded(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["Fato real.", "   ", "\t", ""]
        result = deduplicate_uncategorized(items)
        assert result == ["Fato real."]

    def test_order_of_first_occurrence_preserved(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["Terceiro.", "Primeiro.", "Segundo.", "Primeiro.", "Terceiro."]
        result = deduplicate_uncategorized(items)
        assert result == ["Terceiro.", "Primeiro.", "Segundo."]

    def test_large_list_with_many_duplicates(self):
        from src.services.consolidator import deduplicate_uncategorized
        items = ["Fato único."] * 100 + ["Outro fato."] * 50
        result = deduplicate_uncategorized(items)
        assert result == ["Fato único.", "Outro fato."]
