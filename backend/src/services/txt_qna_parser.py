import re
from typing import IO, Any, List
from src.models.merger import QnAPair
from src.services.qna_parser_factory import QnAParser

class TXTQnAParser(QnAParser):
    def parse(self, file: IO[Any]) -> List[QnAPair]:
        try:
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
                
            qna_pairs = []
            lines = content.splitlines()
            
            current_metadata = None
            current_frequencia = 1
            current_q = None
            current_a = None
            
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    if current_q and current_a:
                        try:
                            qna_pairs.append(QnAPair(
                                perguntaPadronizada=current_q.strip(),
                                respostaConsolidada=current_a.strip(),
                                frequencia=current_frequencia,
                                metadata=current_metadata
                            ))
                        except Exception:
                            pass
                        current_q = None
                        current_a = None
                        current_metadata = None
                        current_frequencia = 1
                    continue
                
                if line_stripped.startswith("[") and "]" in line_stripped and current_q is None:
                    meta_match = re.search(r'\[(.*?)\]', line_stripped)
                    if meta_match:
                        current_metadata = meta_match.group(1).strip()
                    
                    freq_match = re.search(r'\(Frequência:\s*(\d+)\)', line_stripped, re.IGNORECASE)
                    if freq_match:
                        current_frequencia = int(freq_match.group(1))
                    else:
                        current_frequencia = 1
                
                elif line_stripped.startswith("Q:"):
                    # If we already had Q and A but no blank line separator
                    if current_q and current_a:
                        try:
                            qna_pairs.append(QnAPair(
                                perguntaPadronizada=current_q.strip(),
                                respostaConsolidada=current_a.strip(),
                                frequencia=current_frequencia,
                                metadata=current_metadata
                            ))
                        except Exception:
                            pass
                        current_a = None
                        current_metadata = None
                        current_frequencia = 1
                    current_q = line_stripped[2:].strip()
                elif line_stripped.startswith("A:"):
                    current_a = line_stripped[2:].strip()
                else:
                    if current_a is not None:
                        current_a += "\n" + line
                    elif current_q is not None:
                        current_q += "\n" + line
            
            if current_q and current_a:
                try:
                    qna_pairs.append(QnAPair(
                        perguntaPadronizada=current_q.strip(),
                        respostaConsolidada=current_a.strip(),
                        frequencia=current_frequencia,
                        metadata=current_metadata
                    ))
                except Exception:
                    pass
            
            return qna_pairs
        except Exception as e:
            raise ValueError(f"Failed to parse TXT: {e}")
