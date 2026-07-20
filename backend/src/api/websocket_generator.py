"""
WebSocket endpoint for real-time Q&A generation from unstructured text.

Endpoint: WS /api/generate

Protocol (contracts/websocket.md):
  1. Client opens the connection and immediately sends a START message (JSON).
  2. Server validates the payload, resolves the API key and prompt config,
     validates the prompt belongs to ferramenta='gerador', splits each file
     into chunks, and enqueues them in FIFO order.
  3. Server processes each chunk sequentially, streaming events back:
       - LOG          → real-time informational / error log entry
       - CHUNK_SUCCESS → chunk processed, generated pairs included
       - QUEUE_ERROR  → unrecoverable error; partial results returned, connection closed
       - QUEUE_COMPLETE → all files processed; final consolidated results returned, connection closed
  4. The server closes the WebSocket after QUEUE_COMPLETE or QUEUE_ERROR.

Design notes (research.md §3):
  - Mirrors websocket.py in structure but calls generator_client.generate_qna_from_chunk().
  - The prompt is validated to belong to ferramenta='gerador'; rejects 'extrator' prompts.
  - uncategorized_database_content is always [] (generator does not extract unstructured facts).
  - Reuses split_text (chunker) and consolidate_qna_pairs (consolidator) unchanged.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.models.schemas import (
    ArquivoProcessamento,
    FilePayload,
    ModeloOpenAI,
    PromptConfig,
    ResultadoParPR,
    StatusArquivo,
    TipoFerramenta,
    TipoLog,
    WSStartMessage,
)
from src.services.chunker import split_text
from src.services.consolidator import consolidate_qna_pairs
from src.services.generator_client import generate_qna_from_chunk

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Helper: current timestamp string
# ──────────────────────────────────────────────────────────────────────────────


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


# ──────────────────────────────────────────────────────────────────────────────
# Helper: send typed WebSocket events
# ──────────────────────────────────────────────────────────────────────────────


async def _send_log(
    ws: WebSocket,
    mensagem: str,
    tipo: TipoLog = TipoLog.INFO,
) -> None:
    payload = {
        "event": "LOG",
        "data": {
            "timestamp": _now_ts(),
            "tipo": tipo.value,
            "mensagem": mensagem,
        },
    }
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


async def _send_chunk_success(
    ws: WebSocket,
    file_id: str,
    chunk_index: int,
    total_chunks: int,
    extracted_pairs: list[ResultadoParPR],
) -> None:
    payload = {
        "event": "CHUNK_SUCCESS",
        "data": {
            "file_id": file_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "extracted_pairs": [p.model_dump() for p in extracted_pairs],
            # Generator always returns empty uncategorized list (contract compat)
            "uncategorized_database_content": [],
        },
    }
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


async def _send_queue_error(
    ws: WebSocket,
    mensagem: str,
    partial_results: list[ResultadoParPR],
) -> None:
    payload = {
        "event": "QUEUE_ERROR",
        "data": {
            "timestamp": _now_ts(),
            "mensagem": mensagem,
            "partial_results": [p.model_dump() for p in partial_results],
            "uncategorized_database_content": [],
        },
    }
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


async def _send_queue_complete(
    ws: WebSocket,
    results: list[ResultadoParPR],
) -> None:
    payload = {
        "event": "QUEUE_COMPLETE",
        "data": {
            "results": [p.model_dump() for p in results],
            "uncategorized_database_content": [],
        },
    }
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


# ──────────────────────────────────────────────────────────────────────────────
# Storage resolution helpers (lazy imports to support incremental development)
# ──────────────────────────────────────────────────────────────────────────────


async def _resolve_api_key(key_id: str) -> str:
    """
    Retrieve the raw API key string for *key_id* from the key storage service.
    Falls back to environment variable OPENAI_API_KEY if the key_id is the
    sentinel value 'env'.

    Raises:
        KeyError: if the key_id is not found in persistent storage.
    """
    if key_id == "env":
        import os

        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise KeyError(
                "OPENAI_API_KEY environment variable is not set and key_id='env' was used."
            )
        return key

    try:
        from src.services.key_storage import KeyStorageService

        storage = KeyStorageService()
        key_obj = storage.get_by_id(key_id)
        if key_obj is None:
            raise KeyError(f"API key with id='{key_id}' not found in storage.")
        return key_obj.chave
    except ModuleNotFoundError:
        raise KeyError(
            f"Key storage module not found. Cannot resolve key_id='{key_id}'. "
            "Use key_id='env' to fall back to the OPENAI_API_KEY environment variable."
        )


async def _resolve_generator_prompt(prompt_id: str) -> PromptConfig | None:
    """
    Retrieve the PromptConfig for *prompt_id* from the prompt storage service.
    Validates the prompt belongs to ferramenta='gerador'.

    Returns None if prompt_id is 'default'/'env' (uses built-in generator default).

    Raises:
        ValueError: If the prompt is found but belongs to ferramenta='extrator'.
    """
    if prompt_id in ("default", "env"):
        return None

    try:
        from src.services.prompt_storage import PromptStorageService

        storage = PromptStorageService()
        prompt = storage.get_by_id(prompt_id)
        if prompt is None:
            logger.warning(
                "Prompt ID '%s' not found in storage. Using default generator prompt.",
                prompt_id,
            )
            return None

        # Enforce tool-specific prompt validation (contract requirement)
        if prompt.ferramenta != TipoFerramenta.GERADOR:
            raise ValueError(
                f"O prompt '{prompt.nome}' pertence à ferramenta '{prompt.ferramenta.value}', "
                "mas o endpoint /api/generate requer um prompt com ferramenta='gerador'."
            )

        return prompt

    except ModuleNotFoundError:
        logger.warning(
            "Prompt storage module not found. Using default generator prompt for prompt_id='%s'.",
            prompt_id,
        )
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Core FIFO queue processor for the generator
# ──────────────────────────────────────────────────────────────────────────────


async def _process_generator_queue(
    ws: WebSocket,
    files: list[FilePayload],
    api_key: str,
    model: ModeloOpenAI,
    prompt_config: PromptConfig | None,
) -> None:
    """
    Main processing loop for the question generator.

    Iterates over each file → each chunk sequentially (FIFO).
    Streams LOG, CHUNK_SUCCESS events during execution.
    Sends QUEUE_COMPLETE or QUEUE_ERROR when done.

    Note: uncategorized_database_content is always [] for the generator.
    """
    all_pairs: list[ResultadoParPR] = []
    partial_pairs: list[ResultadoParPR] = []

    # Build ArquivoProcessamento objects and chunk each file
    arquivo_list: list[ArquivoProcessamento] = []

    for fp in files:
        # Only .txt files are supported by the generator
        ext = "." + fp.nomeArquivo.rsplit(".", 1)[-1].lower() if "." in fp.nomeArquivo else ""
        if ext != ".txt":
            await _send_log(
                ws,
                f"Arquivo '{fp.nomeArquivo}' ignorado: apenas arquivos .txt são suportados pelo gerador.",
                TipoLog.ERRO,
            )
            continue

        raw_text = fp.conteudoBruto
        chunks = split_text(raw_text)

        arquivo = ArquivoProcessamento(
            nomeArquivo=fp.nomeArquivo,
            tamanho=len(fp.conteudoBruto.encode("utf-8")),
            conteudoBruto=fp.conteudoBruto,
            chunks=chunks,
            status=StatusArquivo.PENDENTE,
        )
        arquivo_list.append(arquivo)

        await _send_log(
            ws,
            f"Iniciando fatiamento de {fp.nomeArquivo} ({len(chunks)} chunk(s) gerado(s))",
        )

    # Enqueue all (arquivo, chunk_index) tuples into a FIFO asyncio queue
    queue: asyncio.Queue[tuple[ArquivoProcessamento, int]] = asyncio.Queue()
    for arquivo in arquivo_list:
        for idx in range(len(arquivo.chunks)):
            await queue.put((arquivo, idx))

    if queue.empty():
        await _send_log(
            ws,
            "Nenhum chunk para processar. Verifique os arquivos enviados.",
            TipoLog.ERRO,
        )
        await _send_queue_error(ws, "Nenhum chunk para processar.", [])
        return

    # Process the queue sequentially
    while not queue.empty():
        arquivo, chunk_idx = await queue.get()
        chunk_text = arquivo.chunks[chunk_idx]
        total = len(arquivo.chunks)

        await _send_log(
            ws,
            f"Gerando perguntas para chunk {chunk_idx + 1}/{total} de '{arquivo.nomeArquivo}'…",
        )

        arquivo.status = StatusArquivo.PROCESSANDO

        try:
            pairs, _ = await generate_qna_from_chunk(
                chunk_text=chunk_text,
                api_key=api_key,
                model=model,
                prompt_config=prompt_config,
            )
            all_pairs.extend(pairs)
            partial_pairs.extend(pairs)

            await _send_chunk_success(
                ws,
                file_id=arquivo.id,
                chunk_index=chunk_idx,
                total_chunks=total,
                extracted_pairs=pairs,
            )
            await _send_log(
                ws,
                f"Chunk {chunk_idx + 1}/{total} concluído: {len(pairs)} par(es) gerado(s).",
                TipoLog.SUCESSO,
            )

        except RuntimeError as exc:
            arquivo.status = StatusArquivo.ERRO
            err_msg = f"Erro da API OpenAI: {exc}"
            await _send_log(ws, err_msg, TipoLog.ERRO)
            await _send_queue_error(ws, err_msg, partial_pairs)
            return

        except Exception as exc:  # noqa: BLE001
            arquivo.status = StatusArquivo.ERRO
            err_msg = f"Erro inesperado ao processar chunk {chunk_idx + 1}: {exc}"
            await _send_log(ws, err_msg, TipoLog.ERRO)
            await _send_queue_error(ws, err_msg, partial_pairs)
            return

        finally:
            queue.task_done()

    # All chunks processed successfully
    for arquivo in arquivo_list:
        if arquivo.status != StatusArquivo.ERRO:
            arquivo.status = StatusArquivo.CONCLUIDO

    await _send_log(
        ws,
        f"Iniciando consolidação semântica de {len(all_pairs)} par(es)...",
        TipoLog.INFO,
    )

    consolidated_pairs = await consolidate_qna_pairs(
        pairs=all_pairs,
        api_key=api_key,
        model=model,
        prompt_config=None,  # consolidation uses its own fixed prompt
    )

    await _send_log(
        ws,
        f"Geração concluída. {len(all_pairs)} par(es) consolidados em {len(consolidated_pairs)} par(es) únicos.",
        TipoLog.SUCESSO,
    )
    await _send_queue_complete(ws, consolidated_pairs)


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket route handler
# ──────────────────────────────────────────────────────────────────────────────


@router.websocket("/api/generate")
async def generate_websocket(ws: WebSocket) -> None:
    """
    WebSocket endpoint that accepts a START message and streams generation
    events (LOG, CHUNK_SUCCESS, QUEUE_COMPLETE / QUEUE_ERROR) back to the client.

    Validates that the provided prompt_id belongs to ferramenta='gerador'.
    """
    await ws.accept()
    logger.info("Generator WebSocket connection accepted from %s", ws.client)

    try:
        # ── 1. Receive and validate the START message ─────────────────────────
        raw_msg = await ws.receive_text()
        try:
            data: Any = json.loads(raw_msg)
            start_msg = WSStartMessage(**data)
        except Exception as exc:
            await _send_log(
                ws,
                f"Payload inválido: {exc}. Esperado: {{action: 'START', key_id, prompt_id, files}}",
                TipoLog.ERRO,
            )
            await ws.close(code=1003)
            return

        if start_msg.action != "START":
            await _send_log(ws, "Ação desconhecida. Use action='START'.", TipoLog.ERRO)
            await ws.close(code=1003)
            return

        await _send_log(
            ws,
            f"Sessão de geração iniciada. {len(start_msg.files)} arquivo(s) recebido(s).",
        )

        # ── 2. Resolve API key ────────────────────────────────────────────────
        try:
            api_key = await _resolve_api_key(start_msg.key_id)
        except KeyError as exc:
            await _send_log(ws, f"Chave de API não encontrada: {exc}", TipoLog.ERRO)
            await _send_queue_error(ws, str(exc), [])
            await ws.close(code=1008)
            return

        # ── 3. Resolve and validate prompt config (must be ferramenta='gerador') ─
        try:
            prompt_config = await _resolve_generator_prompt(start_msg.prompt_id)
        except ValueError as exc:
            await _send_log(ws, str(exc), TipoLog.ERRO)
            await _send_queue_error(ws, str(exc), [])
            await ws.close(code=1008)
            return

        # Determine model from prompt_config or default
        model = prompt_config.modeloOpenAI if prompt_config else ModeloOpenAI.GPT_4O_MINI

        # ── 4. Run the FIFO generator queue processor ─────────────────────────
        await _process_generator_queue(
            ws=ws,
            files=start_msg.files,
            api_key=api_key,
            model=model,
            prompt_config=prompt_config,
        )

    except WebSocketDisconnect:
        logger.info("Generator WebSocket client disconnected.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Unhandled Generator WebSocket error: %s", exc, exc_info=True)
        try:
            await _send_log(ws, f"Erro interno do servidor: {exc}", TipoLog.ERRO)
            await ws.close(code=1011)
        except Exception:  # noqa: BLE001
            pass
    finally:
        logger.info("Generator WebSocket session ended.")
