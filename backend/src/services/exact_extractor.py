import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from src.models.exact_qa import RawMessage, LLMQAPairMapping, ExactQAPair

logger = logging.getLogger(__name__)

EXACT_QA_SYSTEM_PROMPT = """Você é um assistente especializado em extração exata de perguntas e respostas em conversas do WhatsApp.
Sua única tarefa é analisar as mensagens indexadas com IDs no formato 'MSG-XXXX' e identificar quais mensagens são perguntas e quais são suas respostas correspondentes.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS um objeto JSON no seguinte formato:
{
  "pairs": [
    {"question_id": "MSG-0001", "answer_id": "MSG-0002"}
  ]
}
2. Identifique apenas pares de pergunta e resposta onde existe uma resposta clara.
3. Não altere os IDs das mensagens em hipótese alguma.
4. Se nenhuma pergunta com resposta for encontrada, retorne {"pairs": []}.
5. NÃO invente IDs nem inclua texto extra.
"""


class ExactExtractorService:
    """Serviço responsável por orquestrar a extração por IDs com LLM e reconstruir o texto exato."""

    def reconstruct_pairs(
        self,
        raw_messages: List[RawMessage],
        llm_mappings: List[LLMQAPairMapping]
    ) -> List[ExactQAPair]:
        """
        Reconstrói os pares de Pergunta e Resposta mapeando os IDs de volta para o texto original das RawMessages.
        Garante fidelidade 100% preservando cada caractere, emoji e quebra de linha.
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
                    "answer_timestamp": a_msg.timestamp
                }
                reconstructed.append(ExactQAPair(
                    id=pair_id,
                    question_id=q_msg.id,
                    question_text=q_msg.content,
                    answer_id=a_msg.id,
                    answer_text=a_msg.content,
                    metadata=metadata
                ))
            else:
                logger.warning(
                    "Mapeamento de ID inválido ignorado: question_id=%s, answer_id=%s",
                    mapping.question_id, mapping.answer_id
                )

        return reconstructed

    async def extract_mappings_with_llm(
        self,
        raw_messages: List[RawMessage],
        api_key: str,
        model: str = "gpt-4o-mini"
    ) -> List[LLMQAPairMapping]:
        """
        Envia o lote de mensagens formatadas com IDs para a LLM e obtém o mapeamento dos pares.
        """
        if not raw_messages:
            return []

        formatted_lines = []
        for msg in raw_messages:
            header = f"[{msg.id}]"
            if msg.sender:
                header += f" {msg.sender}:"
            formatted_lines.append(f"{header} {msg.content}")

        chunk_text = "\n".join(formatted_lines)
        client = AsyncOpenAI(api_key=api_key)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXACT_QA_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Mensagens para análise:\n\n{chunk_text}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            pairs_raw = data.get("pairs", [])
            mappings: List[LLMQAPairMapping] = []
            for item in pairs_raw:
                if "question_id" in item and "answer_id" in item:
                    mappings.append(LLMQAPairMapping(
                        question_id=item["question_id"],
                        answer_id=item["answer_id"]
                    ))
            return mappings
        except Exception as exc:
            logger.error("Erro ao chamar LLM para extração exata: %s", exc, exc_info=True)
            raise exc
