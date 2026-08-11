from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class RawMessage(BaseModel):
    """Representa uma mensagem extraída do arquivo .txt do WhatsApp pelo parser determinístico."""
    id: str = Field(..., description="Identificador único sequencial (ex: MSG-0001)")
    timestamp: Optional[str] = Field(None, description="Data/hora extraída do cabeçalho da mensagem")
    sender: Optional[str] = Field(None, description="Nome ou número do remetente")
    content: str = Field(..., description="Texto bruto e intacto da mensagem")


class LLMQAPairMapping(BaseModel):
    """Estrutura de resposta retornada pela LLM após análise das mensagens."""
    question_id: str = Field(..., description="ID da mensagem identificada como pergunta")
    answer_id: str = Field(..., description="ID da mensagem identificada como resposta correspondente")


class LLMMappingResponse(BaseModel):
    """Resposta contendo a lista de mapeamentos de IDs da LLM."""
    pairs: List[LLMQAPairMapping] = Field(default_factory=list)


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
