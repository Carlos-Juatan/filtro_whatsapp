from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class RawMessage(BaseModel):
    """Representa uma mensagem extraída do arquivo .txt do WhatsApp pelo parser determinístico."""
    id: str = Field(..., description="Identificador único sequencial (ex: MSG-0001)")
    timestamp: Optional[str] = Field(None, description="Data/hora extraída do cabeçalho da mensagem")
    sender: Optional[str] = Field(None, description="Nome ou número do remetente")
    content: str = Field(..., description="Texto bruto e intacto da mensagem")
    is_placeholder: bool = Field(
        False,
        description="True se a mensagem for um placeholder de mídia omitida (ex: <Mídia omitida>)"
    )


class ChunkConfig(BaseModel):
    """Parâmetros de configuração para o fatiamento de mensagens em chunks."""
    chunk_size: int = Field(100, ge=1, description="Quantidade de mensagens por lote enviado à LLM")
    overlap: int = Field(20, ge=0, description="Mensagens de sobreposição entre chunks adjacentes")


class LLMQAPairMapping(BaseModel):
    """Mapeamento retornado pela LLM para cada par de P&R."""
    question_id: str = Field(..., description="ID da mensagem identificada como pergunta")
    answer_id: str = Field(..., description="ID da mensagem identificada como resposta correspondente")


class LLMMappingResponse(BaseModel):
    """Resposta contendo a lista de mapeamentos de IDs da LLM."""
    pairs: List[LLMQAPairMapping] = Field(default_factory=list)


class ChunkProgressPayload(BaseModel):
    """Payload de progresso transmitido pelo WebSocket durante o processamento em chunks."""
    chunk_index: int = Field(..., description="Índice do chunk atual (1-based)")
    total_chunks: int = Field(..., description="Total de chunks a processar")
    pairs_found_in_chunk: int = Field(0, description="Pares encontrados neste chunk (antes de deduplicação global)")
    total_pairs_so_far: int = Field(0, description="Total acumulado de pares únicos até este ponto")
    percent: float = Field(0.0, ge=0.0, le=100.0, description="Porcentagem de progresso (0-100)")


class ExactQAPair(BaseModel):
    """Objeto final gerado pela reconstrução exata através de lookup nos IDs."""
    id: str = Field(..., description="Identificador do par de Q&A")
    question_id: str = Field(..., description="ID da mensagem de pergunta original")
    question_text: str = Field(..., description="Texto 100% idêntico à mensagem bruta original da pergunta")
    answer_id: str = Field(..., description="ID da mensagem de resposta original")
    answer_text: str = Field(..., description="Texto 100% idêntico à mensagem bruta original da resposta")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Informações adicionais (remetentes, timestamps)")


class ExtractionResult(BaseModel):
    """Container de resultados de um arquivo processado."""
    filename: str = Field(..., description="Nome do arquivo carregado")
    total_messages_parsed: int = Field(..., description="Total de mensagens identificadas pelo parser")
    total_pairs_extracted: int = Field(..., description="Total de pares P&R válidos reconstruídos")
    pairs: List[ExactQAPair] = Field(default_factory=list, description="Lista dos pares reconstruídos")
