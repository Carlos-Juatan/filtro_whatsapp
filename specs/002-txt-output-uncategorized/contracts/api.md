# API Contracts Additions: Exportar Conteúdo Não Classificado

This document describes the changes to the WebSocket schemas and payloads for the `WS /api/process` endpoint.

---

## 1. WebSocket Event Extensions

The server-side events `CHUNK_SUCCESS`, `QUEUE_ERROR`, and `QUEUE_COMPLETE` are extended to include the new field `uncategorized_database_content`.

### A. Chunk Completed Event (`CHUNK_SUCCESS`)
Includes uncategorized database content statements extracted from the specific chunk.

```json
{
  "event": "CHUNK_SUCCESS",
  "data": {
    "file_id": "arquivo-uuid",
    "chunk_index": 0,
    "total_chunks": 3,
    "extracted_pairs": [
      {
        "question": "Qual o horário de atendimento?",
        "answer": "Nosso atendimento é de segunda a sexta, das 8h às 18h.",
        "frequency": 1,
        "metadata": "horário",
        "category": "Suporte"
      }
    ],
    "uncategorized_database_content": [
      "A taxa de entrega é de R$ 15,00 para toda a região metropolitana."
    ]
  }
}
```

---

### B. Error Event (`QUEUE_ERROR`)
Includes accumulated, deduplicated uncategorized database content retrieved up to the point of failure.

```json
{
  "event": "QUEUE_ERROR",
  "data": {
    "timestamp": "09:21:45",
    "mensagem": "Erro da API OpenAI: Limite de taxa atingido (429) após 3 tentativas de backoff.",
    "partial_results": [
      {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "Nosso atendimento é de segunda a sexta, das 8h às 18h.",
        "frequencia": 1,
        "metadata": "horário",
        "category": "Suporte"
      }
    ],
    "uncategorized_database_content": [
      "A taxa de entrega é de R$ 15,00 para toda a região metropolitana."
    ]
  }
}
```

---

### C. Complete Success Event (`QUEUE_COMPLETE`)
Includes the full list of consolidated and deduplicated uncategorized database content.

```json
{
  "event": "QUEUE_COMPLETE",
  "data": {
    "results": [
      {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "Nosso atendimento é de segunda a sexta, das 8h às 18h.",
        "frequencia": 3,
        "metadata": "horário",
        "category": "Suporte"
      }
    ],
    "uncategorized_database_content": [
      "A taxa de entrega é de R$ 15,00 para toda a região metropolitana.",
      "Nosso sistema aceita Pix, cartões de crédito e boleto bancário."
    ]
  }
}
```
