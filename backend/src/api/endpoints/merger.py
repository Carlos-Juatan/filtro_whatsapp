"""
FastAPI router for the Q&A Document Merger (Consolidador de P&R).

Endpoints:
- POST /consolidate  – upload files, parse, deduplicate via chunk processor,
                       AI-consolidate, export; emits SSE log events per job
- GET  /download/{filename} – download a previously generated output file
"""

import io
import uuid
import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from src.models.merger import (
    MergeJobResult,
    InputFormat,
    MergerLogEvent,
    MergerLogEventType,
    QnAPair,
)
from src.services.qna_parser_factory import QnAParserFactory
from src.services.qna_chunk_processor import QnaChunkProcessor
from src.services.qna_merger_service import QnAMergerService
from src.services.qna_exporter import QnAExporter
from src.api.endpoints.merger_log import register_job, emit, close_job

router = APIRouter()

# Define output directory
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "outputs"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/consolidate", response_model=MergeJobResult)
async def consolidate_files(
    input_format: InputFormat = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Upload multiple JSON or TXT Q&A files, parse them, deduplicate pairs
    via the chunked batch processor (FR-013/FR-014), optionally refine via
    ChatGPT (CONSOLIDADOR prompt / FR-011), and export dual outputs (FR-009).

    Real-time log events are emitted per job — connect to
    ``GET /api/merger/logs/{job_id}`` via SSE before or during this request.

    If no OpenAI API key is configured, algorithmic local merging is used and a
    warning is included in the response so the frontend can surface it to the user.
    """
    job_id = str(uuid.uuid4())[:8]
    register_job(job_id)

    def _emit(event_type: MergerLogEventType, message: str, meta: Optional[dict] = None) -> None:
        emit(job_id, MergerLogEvent(event_type=event_type, message=message, metadata=meta))

    warnings: List[str] = []
    all_pairs: List[QnAPair] = []
    total_files_processed = 0

    # ── Parse uploaded files ──────────────────────────────────────────────────
    try:
        parser = QnAParserFactory.get_parser(input_format)
    except ValueError as e:
        close_job(job_id)
        raise HTTPException(status_code=400, detail=str(e))

    _emit(
        MergerLogEventType.PARSE_START,
        f"Iniciando leitura de {len(files)} arquivo(s) no formato {input_format.value.upper()}.",
        {"total_files": len(files), "format": input_format.value},
    )

    for file in files:
        try:
            content = await file.read()
            file_obj = io.BytesIO(content)
            pairs = parser.parse(file_obj)
            all_pairs.extend(pairs)
            total_files_processed += 1
            _emit(
                MergerLogEventType.PARSE_END,
                f"Arquivo '{file.filename}' lido: {len(pairs)} par(es) extraído(s).",
                {"filename": file.filename, "pairs_extracted": len(pairs)},
            )
        except Exception as e:
            warning_msg = f"Failed to process {file.filename}: {str(e)}"
            warnings.append(warning_msg)
            _emit(MergerLogEventType.WARNING, warning_msg, {"filename": file.filename})

    total_qna_extracted = len(all_pairs)
    _emit(
        MergerLogEventType.PARSE_END,
        f"Extração concluída: {total_qna_extracted} par(es) no total de {total_files_processed} arquivo(s).",
        {"total_extracted": total_qna_extracted, "files_ok": total_files_processed},
    )

    # ── Chunked deduplication + merging (FR-013 / FR-014) ────────────────────
    _emit(
        MergerLogEventType.DEDUP_START,
        "Iniciando mesclagem e deduplicação via processador por chunks.",
    )

    chunk_processor = QnaChunkProcessor(on_event=lambda ev: emit(job_id, ev))
    # On first run the "main document" is empty; all pairs are treated as new
    merged_pairs = chunk_processor.process(main_pairs=[], new_pairs=all_pairs)

    # ── AI-assisted consolidation (FR-011) with graceful fallback ──────────────
    _emit(
        MergerLogEventType.AI_BATCH_START,
        f"Enviando {len(merged_pairs)} par(es) pré-agrupado(s) para consolidação IA.",
        {"pairs_to_consolidate": len(merged_pairs)},
    )

    consolidated_pairs, ai_warning = await QnAMergerService.consolidate_with_ai(merged_pairs)
    if ai_warning:
        warnings.append(ai_warning)
        _emit(MergerLogEventType.WARNING, ai_warning)

    _emit(
        MergerLogEventType.AI_BATCH_END,
        f"Consolidação concluída: {len(consolidated_pairs)} par(es) únicos.",
        {"total_consolidated": len(consolidated_pairs)},
    )

    total_qna_merged = len(consolidated_pairs)

    # ── Export dual output files ───────────────────────────────────────────────
    _emit(MergerLogEventType.EXPORT_START, "Gerando arquivos de saída JSON e TXT.")

    json_filename: Optional[str] = f"merged_{job_id}.json"
    txt_filename: Optional[str] = f"merged_{job_id}.txt"

    json_path = os.path.join(OUTPUT_DIR, json_filename)
    txt_path = os.path.join(OUTPUT_DIR, txt_filename)

    try:
        json_content = QnAExporter.export_to_json(consolidated_pairs)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)

        txt_content = QnAExporter.export_to_txt(consolidated_pairs)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        _emit(
            MergerLogEventType.EXPORT_END,
            f"Arquivos exportados: {json_filename}, {txt_filename}.",
            {"json_file": json_filename, "txt_file": txt_filename},
        )
    except Exception as e:
        error_msg = f"Failed to export files: {str(e)}"
        warnings.append(error_msg)
        _emit(MergerLogEventType.ERROR, error_msg)
        json_filename = None
        txt_filename = None

    _emit(
        MergerLogEventType.COMPLETE,
        (
            f"Processo finalizado — {total_files_processed} arquivo(s) processado(s), "
            f"{total_qna_extracted} pares extraídos, {total_qna_merged} únicos após consolidação."
        ),
        {
            "job_id": job_id,
            "files_processed": total_files_processed,
            "extracted": total_qna_extracted,
            "merged": total_qna_merged,
        },
    )
    close_job(job_id)

    return MergeJobResult(
        success=total_files_processed > 0,
        total_files_processed=total_files_processed,
        total_qna_extracted=total_qna_extracted,
        total_qna_merged=total_qna_merged,
        json_output_filename=json_filename,
        txt_output_filename=txt_filename,
        warnings=warnings,
        qna_pairs=consolidated_pairs,
    )


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Return a previously generated output file for download."""
    # Security: ensure no path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=safe_filename)
