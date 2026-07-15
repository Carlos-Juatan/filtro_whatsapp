# API Contract: WebSocket `/api/generate`

This document defines the WebSocket communication contract for the Question Generator service.

- **Endpoint**: `WS /api/generate`
- **Protocol**: JSON-based message streaming.

---

## 1. Client → Server: Session Start (`START`)

To initiate a question generation process, the client opens the WebSocket connection and must immediately send a `START` payload.

### Payload Schema
```json
{
  "action": "START",
  "key_id": "string (UUID or 'env')",
  "prompt_id": "string (UUID)",
  "files": [
    {
      "nomeArquivo": "string (.txt extension only)",
      "conteudoBruto": "string (raw file contents, max 1,000,000 chars)"
    }
  ]
}
```

- **`action`**: Must be exactly `"START"`.
- **`key_id`**: The UUID of the OpenAI API key or the sentinel value `"env"` to use the server's environment variable.
- **`prompt_id`**: The UUID of the prompt configuration. The backend will validate that this prompt belongs to `ferramenta == "gerador"`.
- **`files`**: An array containing one or more files to process.

---

## 2. Server → Client: Event Messages

During processing, the server streams real-time feedback messages to the client.

### A. Execution Log (`LOG`)
Sent to update the execution log console in real-time.

```json
{
  "event": "LOG",
  "data": {
    "timestamp": "HH:MM:SS",
    "tipo": "INFO | SUCESSO | ERRO",
    "mensagem": "Log entry message description"
  }
}
```

---

### B. Chunk Success (`CHUNK_SUCCESS`)
Sent when a single chunk of a file is successfully processed by the OpenAI API.

```json
{
  "event": "CHUNK_SUCCESS",
  "data": {
    "file_id": "string (UUID)",
    "chunk_index": 0,
    "total_chunks": 5,
    "extracted_pairs": [
      {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "O horário de atendimento é de segunda a sexta, das 8h às 18h.",
        "frequencia": 1,
        "metadata": "Horários",
        "category": "FAQ"
      }
    ],
    "uncategorized_database_content": []
  }
}
```

*Note: For the question generator, `uncategorized_database_content` is always returned as an empty list to maintain contract compatibility with the frontend parser.*

---

### C. Processing Completed (`QUEUE_COMPLETE`)
Sent when all files and chunks in the queue are completed and consolidated successfully. The server closes the connection after sending this message.

```json
{
  "event": "QUEUE_COMPLETE",
  "data": {
    "results": [
      {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "O horário de atendimento é de segunda a sexta, das 8h às 18h, e aos sábados das 8h às 12h.",
        "frequencia": 2,
        "metadata": "Horários",
        "category": "FAQ"
      }
    ],
    "uncategorized_database_content": []
  }
}
```

---

### D. Processing Error (`QUEUE_ERROR`)
Sent if an unrecoverable error occurs (such as API quota limit reached or connection issue). The server sends this message containing any partially generated results and closes the connection.

```json
{
  "event": "QUEUE_ERROR",
  "data": {
    "timestamp": "HH:MM:SS",
    "mensagem": "Error description details...",
    "partial_results": [
      {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "O horário de atendimento é de segunda a sexta, das 8h às 18h.",
        "frequencia": 1,
        "metadata": "Horários",
        "category": "FAQ"
      }
    ],
    "uncategorized_database_content": []
  }
}
```
