"""
Pydantic schemas for the Extrator e Filtro de P&R (Local) application.

Extended for feature 003-gerador-perguntas:
  - TipoFerramenta enum added to segregate prompts by tool.
  - ferramenta field added to PromptConfigBase (default: EXTRATOR for backward compat.).

Entities:
  - ChaveAPI          → Persisted in Docker volume JSON file
  - PromptConfig      → Persisted in Docker volume JSON file
  - ArquivoProcessamento → In-memory only
  - ResultadoParPR    → In-memory / final export
  - ItemLog           → In-memory real-time log events
  - WebSocket message types (client → server and server → client)
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, List, Literal, Optional, Union

# Re-exported for convenience in other modules
__all__ = [
    "TipoFerramenta",
]

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────


class StatusArquivo(str, Enum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"
    ERRO = "ERRO"


class TipoPrompt(str, Enum):
    FIXO = "FIXO"
    CUSTOMIZADO = "CUSTOMIZADO"


class TipoFerramenta(str, Enum):
    """Identifies which tool a PromptConfig applies to."""

    EXTRATOR = "extrator"
    GERADOR = "gerador"


class TipoLog(str, Enum):
    INFO = "INFO"
    SUCESSO = "SUCESSO"
    ERRO = "ERRO"


class ModeloOpenAI(str, Enum):
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"


# ──────────────────────────────────────────────────────────────────────────────
# A. ChaveAPI  (Persisted: JSON on Docker Volume)
# ──────────────────────────────────────────────────────────────────────────────


class ChaveAPIBase(BaseModel):
    """Fields shared by creation and full representation of an API key."""

    nomeIdentificacao: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Friendly name used to identify the key (must be unique).",
    )
    chave: str = Field(
        ...,
        description="The OpenAI API key value. Must not be empty.",
    )

    @field_validator("nomeIdentificacao")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("nomeIdentificacao must not be blank after stripping whitespace.")
        return stripped

    @field_validator("chave")
    @classmethod
    def validate_chave_format(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("chave must not be empty or blank.")
        # Accept any non-empty key; relaxed for local tool use
        return v.strip()


class ChaveAPICreate(ChaveAPIBase):
    """Request body for POST /api/keys."""
    pass


class ChaveAPI(ChaveAPIBase):
    """Full representation returned by the API, including UUID."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID v4 identifier.")

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# B. PromptConfig  (Persisted: JSON on Docker Volume)
# ──────────────────────────────────────────────────────────────────────────────


class PromptConfigBase(BaseModel):
    """Fields shared by creation and full representation of a prompt config."""

    nome: str = Field(..., min_length=1, max_length=100, description="Friendly name for the prompt config.")
    tipo: TipoPrompt = Field(TipoPrompt.CUSTOMIZADO, description="FIXO (system) or CUSTOMIZADO (user-defined).")
    textoInstrucao: Optional[str] = Field(
        None,
        min_length=10,
        max_length=5000,
        description="Main LLM system instructions. Required for CUSTOMIZADO prompts.",
    )
    palavrasChave: List[str] = Field(default_factory=list, description="Optional keyword filters for extraction.")
    idiomaModelo: str = Field(default="pt-br", description="Output target language code (e.g. 'pt-br', 'en-us').")
    modeloOpenAI: ModeloOpenAI = Field(default=ModeloOpenAI.GPT_4O_MINI, description="Selected LLM model.")
    ferramenta: TipoFerramenta = Field(
        default=TipoFerramenta.EXTRATOR,
        description="Tool this prompt applies to: 'extrator' or 'gerador'. Defaults to 'extrator' for backward compatibility.",
    )

    @field_validator("textoInstrucao")
    @classmethod
    def validate_texto_instrucao(cls, v: Optional[str], info: Any) -> Optional[str]:
        # Validation that CUSTOMIZADO prompts must have a textoInstrucao is
        # done at the service layer, where tipo is known alongside this value.
        return v


class PromptConfigCreate(PromptConfigBase):
    """Request body for POST /api/prompts (tipo defaults to CUSTOMIZADO)."""
    pass


class PromptConfig(PromptConfigBase):
    """Full representation returned by the API, including UUID."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID v4 identifier.")

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# C. ArquivoProcessamento  (In-Memory)
# ──────────────────────────────────────────────────────────────────────────────


class ArquivoProcessamento(BaseModel):
    """Represents a file uploaded by the user for Q&A extraction."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID v4 identifier.")
    nomeArquivo: str = Field(..., description="Original file name. Must have a supported extension (e.g. .txt).")
    tamanho: int = Field(..., gt=0, description="File size in bytes. Must be > 0.")
    conteudoBruto: str = Field(
        ...,
        max_length=1_000_000,
        description="Complete raw text content. Max 1,000,000 characters.",
    )
    chunks: List[str] = Field(default_factory=list, description="Smart text slices produced by the chunker.")
    status: StatusArquivo = Field(default=StatusArquivo.PENDENTE, description="Current processing state.")

    @field_validator("nomeArquivo")
    @classmethod
    def validate_extension(cls, v: str) -> str:
        supported = {".txt"}
        ext = "." + v.rsplit(".", 1)[-1].lower() if "." in v else ""
        if ext not in supported:
            raise ValueError(f"Unsupported file extension '{ext}'. Supported: {supported}")
        return v


# ──────────────────────────────────────────────────────────────────────────────
# D. ResultadoParPR  (In-Memory / Final Export)
# ──────────────────────────────────────────────────────────────────────────────


class ResultadoParPR(BaseModel):
    """Represents an extracted, grouped, and consolidated Q&A pair."""

    perguntaPadronizada: str = Field(..., min_length=1, description="Semantic unified question. Must not be empty.")
    respostaConsolidada: str = Field(..., min_length=1, description="Consolidated answer. Must not be empty.")
    frequencia: int = Field(..., ge=1, description="Cumulative count of occurrences (>= 1).")
    metadata: Optional[str] = Field(None, description="Associated context keywords / tags.")
    category: str = Field(..., min_length=1, description="Categorization group. Must not be empty.")


# ──────────────────────────────────────────────────────────────────────────────
# E. ItemLog  (In-Memory, Real-Time)
# ──────────────────────────────────────────────────────────────────────────────


class ItemLog(BaseModel):
    """Represents an execution event streamed to the real-time log area."""

    timestamp: str = Field(..., description="Time of the event in HH:MM:SS format.")
    tipo: TipoLog = Field(..., description="Event classification: INFO, SUCESSO, or ERRO.")
    mensagem: str = Field(..., min_length=1, description="Event details. Must not be empty.")


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket Message Types (Client → Server)
# ──────────────────────────────────────────────────────────────────────────────


class FilePayload(BaseModel):
    """A single file submitted in the WebSocket START action."""

    nomeArquivo: str
    conteudoBruto: str


class WSStartMessage(BaseModel):
    """Client → Server: Initiate a processing session."""

    action: Literal["START"]
    key_id: str = Field(..., description="UUID of the ChaveAPI to use for OpenAI calls.")
    prompt_id: str = Field(..., description="UUID of the PromptConfig to apply.")
    files: List[FilePayload] = Field(..., min_length=1, description="One or more files to process.")


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket Message Types (Server → Client)
# ──────────────────────────────────────────────────────────────────────────────


class WSLogEvent(BaseModel):
    """Server → Client: A real-time log entry."""

    event: Literal["LOG"]
    data: ItemLog


class WSChunkSuccessData(BaseModel):
    file_id: str
    chunk_index: int
    total_chunks: int
    extracted_pairs: List[ResultadoParPR]
    uncategorized_database_content: List[str] = Field(default_factory=list, description="Useful facts/statements extracted from the chunk that are not Q&A pairs.")


class WSChunkSuccessEvent(BaseModel):
    """Server → Client: A chunk was processed successfully."""

    event: Literal["CHUNK_SUCCESS"]
    data: WSChunkSuccessData


class WSQueueErrorData(BaseModel):
    timestamp: str
    mensagem: str
    partial_results: List[ResultadoParPR]
    uncategorized_database_content: List[str] = Field(default_factory=list, description="Partially accumulated uncategorized content up to the point of error.")


class WSQueueErrorEvent(BaseModel):
    """Server → Client: Queue halted due to an unrecoverable error."""

    event: Literal["QUEUE_ERROR"]
    data: WSQueueErrorData


class WSQueueCompleteData(BaseModel):
    results: List[ResultadoParPR]
    uncategorized_database_content: List[str] = Field(default_factory=list, description="Deduplicated list of all useful facts/statements extracted across all files.")


class WSQueueCompleteEvent(BaseModel):
    """Server → Client: All files processed successfully."""

    event: Literal["QUEUE_COMPLETE"]
    data: WSQueueCompleteData


# Union type for all server-side WebSocket events
WSServerEvent = Union[WSLogEvent, WSChunkSuccessEvent, WSQueueErrorEvent, WSQueueCompleteEvent]


# ──────────────────────────────────────────────────────────────────────────────
# Generic error response
# ──────────────────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    detail: str
