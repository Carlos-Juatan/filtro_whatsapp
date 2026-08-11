import json
import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.models.exact_qa import ChunkConfig, ChunkProgressPayload
from src.services.exact_parser import parse_whatsapp_chat
from src.services.exact_extractor import ExactExtractorService
from src.services.key_storage import key_storage

logger = logging.getLogger(__name__)
router = APIRouter()
exact_extractor_service = ExactExtractorService()


@router.websocket("/ws")
async def exact_extractor_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Cliente WebSocket do Extrator Exato conectado.")

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                payload = json.loads(raw_msg)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "JSON inválido enviado pelo cliente."
                })
                continue

            action = payload.get("action")
            if action != "start_extraction":
                await websocket.send_json({
                    "type": "error",
                    "error": f"Ação desconhecida: '{action}'."
                })
                continue

            filename = payload.get("filename", "conversa.txt")
            content = payload.get("content", "")
            key_id = payload.get("key_id")
            api_key = payload.get("api_key")

            # Resolve API Key
            if not api_key:
                if key_id:
                    key_obj = key_storage.get_by_id(key_id)
                    if key_obj:
                        api_key = key_obj.chave
                if not api_key:
                    keys = key_storage.get_all()
                    if keys:
                        api_key = keys[0].chave
                if not api_key:
                    api_key = os.getenv("OPENAI_API_KEY")

            if not api_key:
                await websocket.send_json({
                    "type": "error",
                    "error": "Nenhuma chave de API da OpenAI encontrada. Cadastre uma chave nas configurações."
                })
                continue

            # ---------------------------------------------------------------
            # Passo 1: Parser Determinístico
            # ---------------------------------------------------------------
            await websocket.send_json({
                "type": "log",
                "message": f"Iniciando parser determinístico no arquivo '{filename}'...",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            raw_messages = parse_whatsapp_chat(content)
            total_messages = len(raw_messages)

            await websocket.send_json({
                "type": "log",
                "message": f"Parser determinístico concluiu a indexação de {total_messages} mensagens.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            if total_messages == 0:
                await websocket.send_json({
                    "type": "complete",
                    "data": {
                        "filename": filename,
                        "total_messages_parsed": 0,
                        "total_pairs_extracted": 0,
                        "pairs": []
                    }
                })
                continue

            # ---------------------------------------------------------------
            # Passo 2: Chunking + Mapeamento via IA com progresso chunk a chunk
            # ---------------------------------------------------------------
            chunk_config = ChunkConfig()  # chunk_size=100, overlap=20
            total_chunks_estimate = max(1, (total_messages + chunk_config.chunk_size - 1) // chunk_config.chunk_size)

            await websocket.send_json({
                "type": "log",
                "message": (
                    f"Iniciando processamento em {total_chunks_estimate} lote(s) de "
                    f"{chunk_config.chunk_size} mensagens (overlap={chunk_config.overlap}) via IA..."
                ),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            mappings = None
            try:
                async for event in exact_extractor_service.extract_mappings_with_llm_streaming(
                    raw_messages=raw_messages,
                    api_key=api_key,
                    chunk_config=chunk_config,
                ):
                    if isinstance(event, ChunkProgressPayload):
                        # Transmit chunk-by-chunk progress to client (T006)
                        await websocket.send_json({
                            "type": "chunk_progress",
                            "data": event.model_dump(),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        await websocket.send_json({
                            "type": "log",
                            "message": (
                                f"Lote {event.chunk_index}/{event.total_chunks} processado — "
                                f"{event.pairs_found_in_chunk} par(es) novo(s) encontrado(s) "
                                f"({event.total_pairs_so_far} total, {event.percent}%)"
                            ),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    else:
                        # Final list of deduplicated mappings
                        mappings = event

            except Exception as exc:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Erro na chamada da LLM: {str(exc)}"
                })
                continue

            if mappings is None:
                mappings = []

            await websocket.send_json({
                "type": "log",
                "message": f"IA retornou {len(mappings)} pares de IDs únicos mapeados.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # ---------------------------------------------------------------
            # Passo 3: Reconstrução Exata
            # ---------------------------------------------------------------
            await websocket.send_json({
                "type": "log",
                "message": "Reconstruindo texto exato dos pares a partir do banco de mensagens brutas...",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            reconstructed_pairs = exact_extractor_service.reconstruct_pairs(
                raw_messages=raw_messages,
                llm_mappings=mappings
            )

            pair_dicts = [p.model_dump() for p in reconstructed_pairs]

            await websocket.send_json({
                "type": "complete",
                "data": {
                    "filename": filename,
                    "total_messages_parsed": total_messages,
                    "total_pairs_extracted": len(reconstructed_pairs),
                    "pairs": pair_dicts
                }
            })

    except WebSocketDisconnect:
        logger.info("Cliente WebSocket do Extrator Exato desconectou.")
