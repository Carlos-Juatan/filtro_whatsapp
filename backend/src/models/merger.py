from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
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


# ──────────────────────────────────────────────────────────────────────────────
# Real-time processing log events (FR-012 / SC-004)
# ──────────────────────────────────────────────────────────────────────────────

class MergerLogEventType(str, Enum):
    """Categorises each stage in the consolidation pipeline."""
    PARSE_START = "parse_start"
    PARSE_END = "parse_end"
    DEDUP_START = "dedup_start"
    DEDUP_END = "dedup_end"
    CHUNK_PROGRESS = "chunk_progress"
    AI_BATCH_START = "ai_batch_start"
    AI_BATCH_END = "ai_batch_end"
    EXPORT_START = "export_start"
    EXPORT_END = "export_end"
    WARNING = "warning"
    COMPLETE = "complete"
    ERROR = "error"


class MergerLogEvent(BaseModel):
    """
    A single timestamped log event emitted during consolidation processing.

    Consumed by:
    - SSE endpoint  ``GET /api/merger/logs/{job_id}``
    - In-memory queue accumulated per-job and polled by the frontend

    Fields:
        event_type:  Stage / event category from ``MergerLogEventType``.
        message:     Human-readable description (shown verbatim in the UI log panel).
        timestamp:   UTC ISO-8601 string; auto-populated if not provided.
        metadata:    Optional dict with stage-specific counters or context
                     (e.g. ``{"chunk": 2, "total_chunks": 10, "pairs_in_chunk": 30}``).
    """
    event_type: MergerLogEventType
    message: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Optional[Dict[str, Any]] = None

