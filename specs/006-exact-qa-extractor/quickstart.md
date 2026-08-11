# Quickstart: Extração Exata de P&R

## Visão Geral
Esta funcionalidade adiciona uma ferramenta no frontend e backend para extrair pares de Pergunta e Resposta exatamente como foram escritos no WhatsApp, sem paráfrases ou alterações de texto pela IA.

## Passos para Execução/Testes

### 1. Testes Unitários no Backend
Execute a suíte de testes do parser determinístico e da fábrica de reconstrução:
```bash
pytest backend/tests/test_exact_parser.py backend/tests/test_exact_extractor.py
```

### 2. Executando Localmente no Ambiente Docker
Inicie o ambiente de desenvolvimento completo:
```bash
docker-compose up --build
```
Acesse a aplicação no navegador em `http://localhost:8000` (ou na porta configurada) e selecione a ferramenta "Extração Exata P&R" no cabeçalho.

### 3. Teste com Arquivo de Exemplo
1. Faça o upload de uma conversa exportada do WhatsApp (`.txt`).
2. Clique no botão de processamento.
3. Observe os logs de indexação determinística em tempo real na tela.
4. Confira a lista final de pares e valide a exportação nos formatos `.txt` e `.json`.
