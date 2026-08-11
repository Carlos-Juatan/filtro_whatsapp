import pytest
from src.models.exact_qa import RawMessage, LLMQAPairMapping
from src.services.exact_extractor import ExactExtractorService


def test_reconstruct_exact_qa_pairs():
    raw_messages = [
        RawMessage(id="MSG-0001", timestamp="10/05/2023 14:30", sender="Joao", content="Qual o valor da vacina? 🐶"),
        RawMessage(id="MSG-0002", timestamp="10/05/2023 14:31", sender="Clinica", content="A vacina V10 custa R$ 120,00."),
        RawMessage(id="MSG-0003", timestamp="10/05/2023 14:32", sender="Joao", content="Voces aceitam cartão?"),
        RawMessage(id="MSG-0004", timestamp="10/05/2023 14:33", sender="Clinica", content="Sim! Aceitamos credito e debito.")
    ]

    llm_mappings = [
        LLMQAPairMapping(question_id="MSG-0001", answer_id="MSG-0002"),
        LLMQAPairMapping(question_id="MSG-0003", answer_id="MSG-0004")
    ]

    service = ExactExtractorService()
    reconstructed_pairs = service.reconstruct_pairs(raw_messages, llm_mappings)

    assert len(reconstructed_pairs) == 2
    assert reconstructed_pairs[0].id == "PAIR-0001"
    assert reconstructed_pairs[0].question_id == "MSG-0001"
    assert reconstructed_pairs[0].question_text == "Qual o valor da vacina? 🐶"
    assert reconstructed_pairs[0].answer_id == "MSG-0002"
    assert reconstructed_pairs[0].answer_text == "A vacina V10 custa R$ 120,00."
    assert reconstructed_pairs[0].metadata["question_sender"] == "Joao"

    assert reconstructed_pairs[1].id == "PAIR-0002"
    assert reconstructed_pairs[1].question_id == "MSG-0003"
    assert reconstructed_pairs[1].question_text == "Voces aceitam cartão?"
    assert reconstructed_pairs[1].answer_id == "MSG-0004"
    assert reconstructed_pairs[1].answer_text == "Sim! Aceitamos credito e debito."
