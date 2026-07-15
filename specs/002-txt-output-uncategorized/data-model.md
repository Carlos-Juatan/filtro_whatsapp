# Data Model: Exportar Conteúdo Não Classificado

This document describes the in-memory data structures and JSON schemas used to support the extraction and export of uncategorized content.

## In-Memory Structures

### 1. Uncategorized Content Accumulator
- **Type**: `list[str]`
- **Scope**: Exists in the WebSocket session handler context during queue processing.
- **Description**: Stores all statements and facts extracted from each text chunk before deduplication and final presentation.

### 2. WebSocket Schemas (Extending `src/models/schemas.py`)

#### WSChunkSuccessData
```python
class WSChunkSuccessData(BaseModel):
    file_id: str
    chunk_index: int
    total_chunks: int
    extracted_pairs: List[ResultadoParPR]
    uncategorized_database_content: List[str]  # Added field
```

#### WSQueueCompleteData
```python
class WSQueueCompleteData(BaseModel):
    results: List[ResultadoParPR]
    uncategorized_database_content: List[str]  # Added field
```

#### WSQueueErrorData
```python
class WSQueueErrorData(BaseModel):
    timestamp: str
    mensagem: str
    partial_results: List[ResultadoParPR]
    uncategorized_database_content: List[str]  # Added field
```

## Persistent / Exported Formats

### 1. JSON Export File
The standard consolidated JSON report contains questions and answers (`qna_pairs`) and remains unchanged. Uncategorized content is **not** included in this file.


### 2. TXT Export File (`nao_classificados.txt`)
A plain text file where each entry is written on its own line:
```text
O horário de funcionamento é das 8h às 18h.
A taxa de entrega custa R$ 15,00.
```
- **Encoding**: UTF-8
- **Delimiter**: `\n`
