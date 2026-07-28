"""
FastAPI router for the Q&A Document Merger (Consolidador de P&R).

Endpoints:
- POST /consolidate  – upload files, parse, deduplicate, AI-consolidate, export
- GET  /download/{filename} – download a previously generated output file
"""

import io
import uuid
import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from src.models.merger import MergeJobResult, InputFormat, QnAPair
from src.services.qna_parser_factory import QnAParserFactory
from src.services.qna_merger_service import QnAMergerService
from src.services.qna_exporter import QnAExporter

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
    Upload multiple JSON or TXT Q&A files, parse them, deduplicate pairs,
    optionally refine via ChatGPT (CONSOLIDADOR prompt), and export dual outputs.

    If no OpenAI API key is configured, algorithmic local merging is used and a
    warning is included in the response so the frontend can surface it to the user.
    """
    warnings: List[str] = []
    all_pairs: List[QnAPair] = []
    total_files_processed = 0

    try:
        parser = QnAParserFactory.get_parser(input_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    for file in files:
        try:
            content = await file.read()
            file_obj = io.BytesIO(content)
            pairs = parser.parse(file_obj)
            all_pairs.extend(pairs)
            total_files_processed += 1
        except Exception as e:
            warnings.append(f"Failed to process {file.filename}: {str(e)}")

    total_qna_extracted = len(all_pairs)

    # ── AI-assisted consolidation (FR-011) with graceful fallback ──────────────
    consolidated_pairs, ai_warning = await QnAMergerService.consolidate_with_ai(all_pairs)
    if ai_warning:
        warnings.append(ai_warning)

    total_qna_merged = len(consolidated_pairs)

    # ── Export dual output files ───────────────────────────────────────────────
    job_id = str(uuid.uuid4())[:8]
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
    except Exception as e:
        warnings.append(f"Failed to export files: {str(e)}")
        json_filename = None
        txt_filename = None

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
