import asyncio
import json
import logging
from typing import AsyncGenerator, List, Dict, Set, Tuple

from openai import AsyncOpenAI
from src.models.exact_qa import (
    ChunkConfig,
    ChunkProgressPayload,
    ExactQAPair,
    LLMQAPairMapping,
    RawMessage,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt (T004) — Instructs the LLM to:
#   • Identify genuine Q&A pairs only
#   • Ignore courtesy/greeting messages with no real question
#   • Discard placeholder messages (<Ficheiro não revelado>, <Mídia omitida>, <Media omitted>)
# ---------------------------------------------------------------------------
EXACT_QA_SYSTEM_PROMPT = """\
Você é um assistente especializado em extração exata de perguntas e respostas em conversas do WhatsApp.
Sua única tarefa é analisar as mensagens indexadas com IDs no formato 'MSG-XXXX' e identificar quais mensagens são perguntas e quais são suas respostas correspondentes.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS um objeto JSON no seguinte formato:
{
  "pairs": [
    {"question_id": "MSG-0001", "answer_id": "MSG-0002"}
  ]
}
2. Identifique apenas pares de pergunta e resposta onde existe uma resposta clara e direta à pergunta.
3. IGNORE mensagens de saudação ou cortesia que não contenham uma dúvida ou pergunta real.
   Exemplos a IGNORAR: "Bom dia!", "Oi, tudo bem?", "Obrigado!", "Ok!", "Certo!", "Entendido!".
4. IGNORE completamente mensagens que contenham apenas um dos seguintes placeholders de mídia:
   - "<Ficheiro não revelado>"
   - "<Mídia omitida>"
   - "<Media omitted>"
   Estas mensagens NÃO devem aparecer como question_id nem como answer_id.
5. Não altere os IDs das mensagens em hipótese alguma.
6. Se nenhuma pergunta com resposta for encontrada no lote, retorne {"pairs": []}.
7. NÃO invente IDs nem inclua texto extra fora do JSON.
"""

# Known media placeholder patterns (used by the parser and the service for pre-filtering)
MEDIA_PLACEHOLDER_PATTERNS = frozenset(
    p.lower() for p in [
        "<ficheiro não revelado>",
        "<mídia omitida>",
        "<media omitted>",
    ]
)

# ---------------------------------------------------------------------------
# Chunk helpers (T002)
# ---------------------------------------------------------------------------

def _build_chunks(
    messages: List[RawMessage],
    chunk_config: ChunkConfig,
) -> List[List[RawMessage]]:
    """
    Divide a lista de mensagens em chunks com overlap.

    Args:
        messages:     Lista completa de RawMessage.
        chunk_config: Configuração com chunk_size e overlap.

    Returns:
        Lista de sublistas (chunks) de RawMessage com sobreposição de ``overlap`` mensagens.
    """
    size = chunk_config.chunk_size
    step = max(1, size - chunk_config.overlap)
    chunks: List[List[RawMessage]] = []

    i = 0
    while i < len(messages):
        chunk = messages[i: i + size]
        chunks.append(chunk)
        if i + size >= len(messages):
            break
        i += step

    return chunks


def _format_chunk_for_llm(messages: List[RawMessage]) -> str:
    """Serializa um chunk de mensagens para texto estruturado enviado à LLM."""
    lines = []
    for msg in messages:
        header = f"[{msg.id}]"
        if msg.sender:
            header += f" {msg.sender}:"
        lines.append(f"{header} {msg.content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ExactExtractorService:
    """Serviço responsável por orquestrar a extração por IDs com LLM e reconstruir o texto exato."""

    # -----------------------------------------------------------------------
    # Reconstruction (unchanged core logic, now global-scope for all chunks)
    # -----------------------------------------------------------------------

    def reconstruct_pairs(
        self,
        raw_messages: List[RawMessage],
        llm_mappings: List[LLMQAPairMapping],
    ) -> List[ExactQAPair]:
        """
        Reconstrói os pares de Pergunta e Resposta mapeando os IDs de volta para o texto original
        das RawMessages. Garante fidelidade 100% preservando cada caractere, emoji e quebra de linha.
        """
        msg_map: Dict[str, RawMessage] = {msg.id: msg for msg in raw_messages}
        reconstructed: List[ExactQAPair] = []

        for idx, mapping in enumerate(llm_mappings, start=1):
            q_msg = msg_map.get(mapping.question_id)
            a_msg = msg_map.get(mapping.answer_id)

            if q_msg and a_msg:
                pair_id = f"PAIR-{idx:04d}"
                metadata = {
                    "question_sender": q_msg.sender,
                    "question_timestamp": q_msg.timestamp,
                    "answer_sender": a_msg.sender,
                    "answer_timestamp": a_msg.timestamp,
                }
                reconstructed.append(
                    ExactQAPair(
                        id=pair_id,
                        question_id=q_msg.id,
                        question_text=q_msg.content,
                        answer_id=a_msg.id,
                        answer_text=a_msg.content,
                        metadata=metadata,
                    )
                )
            else:
                logger.warning(
                    "Mapeamento de ID inválido ignorado: question_id=%s, answer_id=%s",
                    mapping.question_id,
                    mapping.answer_id,
                )

        return reconstructed

    # -----------------------------------------------------------------------
    # Single-chunk LLM call with resilience (T003)
    # -----------------------------------------------------------------------

    async def _call_llm_for_chunk(
        self,
        chunk: List[RawMessage],
        client: AsyncOpenAI,
        model: str,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> List[LLMQAPairMapping]:
        """
        Chama a LLM para um único chunk de mensagens com mecanismo de retry automático (T003).
        Captura JSONDecodeError e realiza até `max_retries` tentativas adicionais com backoff simples.
        Define max_tokens=4000 para evitar truncamentos.

        Returns:
            Lista de LLMQAPairMapping extraída do chunk.
        """
        chunk_text = _format_chunk_for_llm(chunk)
        attempt = 0

        while True:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": EXACT_QA_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Mensagens para análise:\n\n{chunk_text}"},
                    ],
                    temperature=0.0,
                    max_tokens=4000,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                data = json.loads(content)
                pairs_raw = data.get("pairs", [])
                mappings: List[LLMQAPairMapping] = []
                for item in pairs_raw:
                    if "question_id" in item and "answer_id" in item:
                        mappings.append(
                            LLMQAPairMapping(
                                question_id=item["question_id"],
                                answer_id=item["answer_id"],
                            )
                        )
                return mappings

            except json.JSONDecodeError as exc:
                attempt += 1
                if attempt > max_retries:
                    logger.error(
                        "JSONDecodeError persistente após %d tentativas no chunk: %s",
                        max_retries + 1,
                        exc,
                    )
                    return []
                logger.warning(
                    "JSONDecodeError na tentativa %d/%d — realizando retry em %.1fs: %s",
                    attempt,
                    max_retries + 1,
                    retry_delay,
                    exc,
                )
                await asyncio.sleep(retry_delay)

            except Exception as exc:
                logger.error("Erro inesperado ao chamar LLM para chunk: %s", exc, exc_info=True)
                raise

    # -----------------------------------------------------------------------
    # Multi-chunk extraction with deduplication (T005)
    # -----------------------------------------------------------------------

    async def extract_mappings_with_llm(
        self,
        raw_messages: List[RawMessage],
        api_key: str,
        model: str = "gpt-4o-mini",
        chunk_config: ChunkConfig | None = None,
    ) -> List[LLMQAPairMapping]:
        """
        Processa a lista completa de mensagens em chunks com overlap (T002).
        Agrega e deduplica pares de (question_id, answer_id) entre chunks (T005).

        Args:
            raw_messages:  Lista completa de RawMessage já indexada pelo parser.
            api_key:       Chave de API da OpenAI.
            model:         Modelo da OpenAI a utilizar.
            chunk_config:  Configuração de chunking (padrão: 100 msg / 20 overlap).

        Returns:
            Lista deduplicada de LLMQAPairMapping.
        """
        if not raw_messages:
            return []

        cfg = chunk_config or ChunkConfig()
        chunks = _build_chunks(raw_messages, cfg)
        client = AsyncOpenAI(api_key=api_key)

        seen: Set[Tuple[str, str]] = set()
        all_mappings: List[LLMQAPairMapping] = []

        for chunk in chunks:
            chunk_mappings = await self._call_llm_for_chunk(chunk, client, model)
            for mapping in chunk_mappings:
                key = (mapping.question_id, mapping.answer_id)
                if key not in seen:
                    seen.add(key)
                    all_mappings.append(mapping)

        return all_mappings

    # -----------------------------------------------------------------------
    # Streaming extraction with chunk-by-chunk progress (T006 helper)
    # -----------------------------------------------------------------------

    async def extract_mappings_with_llm_streaming(
        self,
        raw_messages: List[RawMessage],
        api_key: str,
        model: str = "gpt-4o-mini",
        chunk_config: ChunkConfig | None = None,
    ) -> AsyncGenerator[ChunkProgressPayload | List[LLMQAPairMapping], None]:
        """
        Versão streaming de extract_mappings_with_llm que emite ChunkProgressPayload
        após cada chunk processado (para transmissão via WebSocket) e por fim
        retorna a lista final de LLMQAPairMapping via AsyncGenerator.

        Usage (in WebSocket handler):
            async for event in service.extract_mappings_with_llm_streaming(...):
                if isinstance(event, ChunkProgressPayload):
                    await ws.send_json({"type": "chunk_progress", "data": event.model_dump()})
                else:
                    mappings = event  # final list
        """
        if not raw_messages:
            yield []
            return

        cfg = chunk_config or ChunkConfig()
        chunks = _build_chunks(raw_messages, cfg)
        total_chunks = len(chunks)
        client = AsyncOpenAI(api_key=api_key)

        seen: Set[Tuple[str, str]] = set()
        all_mappings: List[LLMQAPairMapping] = []

        for i, chunk in enumerate(chunks, start=1):
            chunk_mappings = await self._call_llm_for_chunk(chunk, client, model)
            new_in_chunk = 0
            for mapping in chunk_mappings:
                key = (mapping.question_id, mapping.answer_id)
                if key not in seen:
                    seen.add(key)
                    all_mappings.append(mapping)
                    new_in_chunk += 1

            progress = ChunkProgressPayload(
                chunk_index=i,
                total_chunks=total_chunks,
                pairs_found_in_chunk=new_in_chunk,
                total_pairs_so_far=len(all_mappings),
                percent=round((i / total_chunks) * 100, 1),
            )
            yield progress

        yield all_mappings
