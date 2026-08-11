# Phase 0: Research - Extração Exata de Perguntas e Respostas do WhatsApp

## Decision 1: Estrutura do Parser Determinístico para WhatsApp
- **Decision**: Criar um módulo de parsing determinístico no backend (`backend/src/services/exact_parser.py`) utilizando expressões regulares para capturar marcas d'água de data/hora do WhatsApp e agrupamento de mensagens multilinha. Cada mensagem parsed recebe um ID sequencial único (ex: `MSG-0001`, `MSG-0002`).
- **Rationale**: Ao desvincular a captura de texto da inteligência da LLM, garantimos 100% de precisão nos caracteres originais e evitaremos alterações por parte do modelo.
- **Alternatives Considered**: 
  - Enviar o texto bruto direto para a LLM e pedir para ela retornar o texto extraído (Rejeitado: a LLM frequentemente parafraseia, remove emojis ou altera pontuações).

## Decision 2: Protocolo de Comunicação e Prompting com a LLM
- **Decision**: Enviar à LLM um payload contendo apenas o ID e o conteúdo resumido/completo da conversa com instruções estritas para responder em formato JSON contendo a lista de pares de IDs: `[{"question_id": "MSG-0001", "answer_id": "MSG-0003"}]`.
- **Rationale**: A LLM atua estritamente como um classificador/indexador sem permissão para reescrever o texto das mensagens.
- **Alternatives Considered**:
  - LLM retornar o texto da pergunta e apenas o ID da resposta (Rejeitado: quebra o requisito de imutabilidade textual em ambas as partes).

## Decision 3: Reconstrução Exata e Endpoints da API
- **Decision**: O backend expõe uma nova rota WebSocket ou HTTP endpoint (`/api/exact-extractor` ou via WebSocket `/api/exact-extractor/ws`) para permitir o envio do arquivo `.txt`, emitindo logs em tempo real e retornando a lista final de pares exatos reconstruídos por lookup direto nos IDs.
- **Rationale**: Mantém consistência com as ferramentas existentes (`extrator`, `gerador`, `consolidador`) e permite progresso visual no frontend em tempo real.
- **Alternatives Considered**:
  - Endpoint REST síncrono simples sem feedback de progresso (Rejeitado: violaria a Constituição II sobre processamento transparente e logs detalhados em tempo real).
