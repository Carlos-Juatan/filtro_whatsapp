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
