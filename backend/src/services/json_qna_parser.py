import json
from typing import IO, Any, List
from src.models.merger import QnAPair
from src.services.qna_parser_factory import QnAParser

class JSONQnAParser(QnAParser):
    def parse(self, file: IO[Any]) -> List[QnAPair]:
        try:
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            if not content.strip():
                return []
                
            data = json.loads(content)
            
            pairs_data = data.get("qna_pairs", []) if isinstance(data, dict) else data
            if not isinstance(pairs_data, list):
                raise ValueError("JSON must contain a list of QnA pairs or a 'qna_pairs' key with a list.")
                
            qna_pairs = []
            for item in pairs_data:
                try:
                    if isinstance(item, dict):
                        # Attempt to parse QnAPair. It will validate fields.
                        pair = QnAPair(**item)
                        qna_pairs.append(pair)
                except Exception:
                    # Malformed individual pair, ignore gracefully
                    pass
                    
            return qna_pairs
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {e}")
