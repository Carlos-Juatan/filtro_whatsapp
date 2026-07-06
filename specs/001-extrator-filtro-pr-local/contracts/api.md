# API Contracts: Extrator e Filtro de P&R (Local)

This document defines the HTTP REST and WebSocket interfaces for communication between the React frontend and the FastAPI backend.

---

## 1. REST Endpoints (Configuration Management)

### GET /api/keys
Retrieve all registered API keys.

* **Response (200 OK)**:
  ```json
  [
    {
      "id": "e2d83c2e-4b72-468b-b156-f6d22ef1492b",
      "nomeIdentificacao": "OpenAI Principal",
      "chave": "sk-proj-...kL9a" 
    }
  ]
  ```
  *(Note: Keys should be masked or partially redacted when listed, e.g. showing only first 7 and last 4 characters, but returning full key only for validation if necessary. For local simplicity, full key storage and display in configurations is acceptable, but masking in logs is recommended.)*

---

### POST /api/keys
Create a new API key. Name uniqueness is checked.

* **Request Body**:
  ```json
  {
    "nomeIdentificacao": "OpenAI Principal",
    "chave": "sk-proj-someApiKeyStringHere"
  }
  ```
* **Response (201 Created)**:
  ```json
  {
    "id": "e2d83c2e-4b72-468b-b156-f6d22ef1492b",
    "nomeIdentificacao": "OpenAI Principal",
    "chave": "sk-proj-someApiKeyStringHere"
  }
  ```
* **Response (400 Bad Request - Name Collision)**:
  ```json
  {
    "detail": "O nome de identificação 'OpenAI Principal' já está em uso."
  }
  ```

---

### DELETE /api/keys/{id}
Delete an existing API key.

* **Response (204 No Content)**: Empty body
* **Response (404 Not Found)**:
  ```json
  {
    "detail": "Chave de API não encontrada."
  }
  ```

---

### GET /api/prompts
Retrieve standard and custom prompts.

* **Response (200 OK)**:
  ```json
  [
    {
      "id": "d007c08a-cf8e-49b0-a54f-561b36952771",
      "nome": "Filtro Padrão P&R",
      "tipo": "FIXO",
      "textoInstrucao": "Extraia perguntas e respostas...",
      "palavrasChave": [],
      "idiomaModelo": "pt-br",
      "modeloOpenAI": "gpt-4o-mini"
    }
  ]
  ```

---

### POST /api/prompts
Save or update a custom prompt configuration.

* **Request Body**:
  ```json
  {
    "nome": "Meu Prompt Customizado",
    "textoInstrucao": "Diretrizes específicas de extração...",
    "palavrasChave": ["atendimento", "suporte"],
    "idiomaModelo": "pt-br",
    "modeloOpenAI": "gpt-4o-mini"
  }
  ```
* **Response (200 OK / 201 Created)**:
  ```json
  {
    "id": "f512739a-7c22-4911-9fa6-ee76541f71a9",
    "nome": "Meu Prompt Customizado",
    "tipo": "CUSTOMIZADO",
    "textoInstrucao": "Diretrizes específicas de extração...",
    "palavrasChave": ["atendimento", "suporte"],
    "idiomaModelo": "pt-br",
    "modeloOpenAI": "gpt-4o-mini"
  }
  ```

---

## 2. WebSocket Connection (Real-time Processing Queue)

To fulfill real-time logging (`FR-011`) and error recovery preserving current results, text processing is handled via WebSockets.

* **Connection Endpoint**: `WS /api/process`

### A. Client Connection Payload
Upon opening the WebSocket, the frontend sends the initiation settings and file details:

```json
{
  "action": "START",
  "key_id": "e2d83c2e-4b72-468b-b156-f6d22ef1492b",
  "prompt_id": "f512739a-7c22-4911-9fa6-ee76541f71a9",
  "files": [
    {
      "nomeArquivo": "transcricao_suporte_01.txt",
      "conteudoBruto": "Cliente: Qual o horário... Atendente: Das 8h às 18h..."
    }
  ]
}
```

### B. Server Stream Events
During queue execution, the server emits log events and processing updates:

#### Log Event (`ItemLog`)
```json
{
  "event": "LOG",
  "data": {
    "timestamp": "09:21:40",
    "tipo": "INFO",
    "mensagem": "Iniciando fatiamento de transcricao_suporte_01.txt (3 chunks gerados)"
  }
}
```

#### Chunk Completed Event
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
    ]
  }
}
```

#### Error Event (Halts Queue)
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
    ]
  }
}
```

#### Complete Success Event
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
    ]
  }
}
```
*(The server closes the WebSocket connection after sending either `QUEUE_COMPLETE` or `QUEUE_ERROR`.)*
