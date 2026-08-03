import json
from typing import List
from src.models.merger import QnAPair

class QnAExporter:
    @staticmethod
    def export_to_json(qna_pairs: List[QnAPair]) -> str:
        """
        Exports a list of QnAPair to a JSON formatted string.
        """
        data = {
            "qna_pairs": [
                pair.model_dump(exclude_none=True)
                for pair in qna_pairs
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def export_to_txt(qna_pairs: List[QnAPair]) -> str:
        """
        Exports a list of QnAPair to a TXT formatted string.

        Format per entry:
            [metadata] (Frequência: N)   ← optional metadata prefix
            Q: <question>
            A: <answer>
            ----------------------------------------

        The separator line is always appended after every A: block,
        including the final entry in the file (SC-002 compliance).
        """
        SEPARATOR = "----------------------------------------"
        lines = []
        for pair in qna_pairs:
            meta_part = f"[{pair.metadata}] " if pair.metadata else ""
            header = f"{meta_part}(Frequência: {pair.frequencia})"

            lines.append(header)
            lines.append(f"Q: {pair.perguntaPadronizada}")
            lines.append(f"A: {pair.respostaConsolidada}")
            lines.append(SEPARATOR)

        return "\n".join(lines)
