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
