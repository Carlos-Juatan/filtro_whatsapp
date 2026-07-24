from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class InputFormat(str, Enum):
    json = "json"
    txt = "txt"

class QnAPair(BaseModel):
    perguntaPadronizada: str
    respostaConsolidada: str
    frequencia: int = Field(..., ge=1)
    metadata: Optional[str] = None
    category: Optional[str] = None

class MergeJobResult(BaseModel):
    success: bool
    total_files_processed: int
    total_qna_extracted: int
    total_qna_merged: int
    json_output_filename: Optional[str] = None
    txt_output_filename: Optional[str] = None
    warnings: List[str]
    qna_pairs: List[QnAPair]
