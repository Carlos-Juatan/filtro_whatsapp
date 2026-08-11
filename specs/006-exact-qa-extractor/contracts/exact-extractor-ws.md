# Interface Contracts: Exact QA Extractor

## WebSocket Endpoint: `/api/exact-extractor/ws`

### Client -> Server: Message Initialization
```json
{
  "action": "start_extraction",
  "filename": "conversa.txt",
  "content": "01/02/2026 10:00 - João: Olá, qual o horário de funcionamento?\n01/02/2026 10:02 - Maria: Abrimos às 08h e fechamos às 18h.",
  "prompt_id": "optional_custom_prompt_id"
}
```

### Server -> Client: Progress Event (Log Stream)
```json
{
  "type": "log",
  "message": "Parser determinístico concluiu a indexação de 2 mensagens.",
  "timestamp": "2026-08-11T14:40:00Z"
}
```

### Server -> Client: Final Result Event
```json
{
  "type": "complete",
  "data": {
    "filename": "conversa.txt",
    "total_messages_parsed": 2,
    "total_pairs_extracted": 1,
    "pairs": [
      {
        "id": "PAIR-0001",
        "question_id": "MSG-0001",
        "question_text": "Olá, qual o horário de funcionamento?",
        "answer_id": "MSG-0002",
        "answer_text": "Abrimos às 08h e fechamos às 18h.",
        "metadata": {
          "question_sender": "João",
          "answer_sender": "Maria"
        }
      }
    ]
  }
}
```
