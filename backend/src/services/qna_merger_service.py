import re
from typing import List, Dict, Optional
from src.models.merger import QnAPair

class QnAMergerService:
    @staticmethod
    def normalize_question(question: str) -> str:
        """
        Normalize a question string for matching:
        - Convert to lowercase
        - Strip outer whitespace
        - Remove trailing punctuation (e.g., '?')
        - Collapse internal whitespace sequences into a single space
        """
        # Convert to lower and strip outer whitespace
        normalized = question.lower().strip()
        
        # Remove trailing punctuation (e.g. ?)
        normalized = re.sub(r'[?.,;!]+$', '', normalized).strip()
        
        # Collapse internal whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized

    @staticmethod
    def merge_qna_pairs(pairs: List[QnAPair]) -> List[QnAPair]:
        """
        Deduplicates and merges a list of QnAPair objects.
        """
        merged_dict: Dict[str, QnAPair] = {}
        
        for pair in pairs:
            normalized_q = QnAMergerService.normalize_question(pair.perguntaPadronizada)
            
            if normalized_q in merged_dict:
                existing_pair = merged_dict[normalized_q]
                
                # Sum frequency
                new_frequencia = existing_pair.frequencia + pair.frequencia
                
                # Select longest answer
                ans1 = existing_pair.respostaConsolidada
                ans2 = pair.respostaConsolidada
                if len(ans2.strip()) > len(ans1.strip()):
                    best_answer = ans2
                else:
                    best_answer = ans1
                    
                # Merge metadata
                merged_meta = existing_pair.metadata
                if pair.metadata:
                    if merged_meta:
                        meta1_tags = {t.strip() for t in merged_meta.split(',') if t.strip()}
                        meta2_tags = {t.strip() for t in pair.metadata.split(',') if t.strip()}
                        combined_meta_tags = meta1_tags.union(meta2_tags)
                        merged_meta = ", ".join(sorted(list(combined_meta_tags))) if combined_meta_tags else None
                    else:
                        merged_meta = pair.metadata
                        
                # Merge category
                merged_category = existing_pair.category
                if pair.category:
                    if merged_category:
                        cat1_tags = {t.strip() for t in merged_category.split(',') if t.strip()}
                        cat2_tags = {t.strip() for t in pair.category.split(',') if t.strip()}
                        combined_cat_tags = cat1_tags.union(cat2_tags)
                        merged_category = ", ".join(sorted(list(combined_cat_tags))) if combined_cat_tags else None
                    else:
                        merged_category = pair.category
                        
                # Keep the original perguntaPadronizada from the first encountered instance
                merged_dict[normalized_q] = QnAPair(
                    perguntaPadronizada=existing_pair.perguntaPadronizada,
                    respostaConsolidada=best_answer,
                    frequencia=new_frequencia,
                    metadata=merged_meta,
                    category=merged_category
                )
            else:
                # Store the original pair
                merged_dict[normalized_q] = QnAPair(
                    perguntaPadronizada=pair.perguntaPadronizada,
                    respostaConsolidada=pair.respostaConsolidada,
                    frequencia=pair.frequencia,
                    metadata=pair.metadata,
                    category=pair.category
                )
                
        return list(merged_dict.values())
