# Quickstart: Extrator Exato de P&R (006-exact-qa-extractor)

## Visão Geral
Esta funcionalidade divide conversas exportadas do WhatsApp (`.txt`) em mensagens indexadas com IDs sequenciais (`MSG-XXXX`), fatia a conversa em chunks com overlap para evitar truncamentos na LLM e mapeia pares de pergunta e resposta. Os textos finais das perguntas e respostas são reconstruídos por lookup direto nos IDs brutos para garantir 100% de correspondência de caracteres sem alterações pela IA.

## Executando os Testes Automatizados

### Backend (Pytest)
Para rodar a suíte de testes do backend para o extrator exato:

```bash
cd backend
pytest tests/test_exact_extractor.py tests/test_exact_parser.py -v
```

## Protocolo WebSocket

- Endpoint: `/api/exact-extractor/extract-ws`
- Fluxo de Mensagens:
  1. Frontend envia payload contendo `filename`, `content` e opcionalmente `api_key`.
  2. Backend envia progresso real em JSON (`status`, `progress`, `current_chunk`, `total_chunks`).
  3. Backend encerra enviando o payload final com status `completed` e objeto `result` contendo todos os `pairs`.
