# Implementation Plan: Extração Exata de P&R no WhatsApp

**Branch**: `006-exact-qa-extractor`  
**Spec**: [`spec.md`](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/006-exact-qa-extractor/spec.md)  
**Status**: Approved / In-Progress

## Technical Context

- **Backend**: Python 3.10+, FastAPI, AsyncOpenAI, Pytest.
- **Frontend**: TypeScript, React, Tailwind CSS, WebSockets.
- **Estratégia de Processamento**:
  - Divisão determinística da conversa do WhatsApp em instâncias `RawMessage` com ID `MSG-XXXX`.
  - Processamento em Chunks de 100 mensagens com 20 mensagens de sobreposição (overlap).
  - Prompts do sistema com regras claras para descarte de saudações isoladas e mídias/placeholders (`<Ficheiro não revelado>`, `<Mídia omitida>`).
  - Chamadas LLM com `max_tokens=4000`, validação rigorosa de sintaxe JSON e mecanismo de retry automático para prevenir erros de truncamento (`Unterminated string`).
  - Reconstrução exata de texto bruto por lookup direto nos IDs retornados pela LLM.

## Constitution Check

- **I. Local-First e Usuário Único**: Compliant. Execução inteiramente local via FastAPI e React.
- **II. Processamento Transparente**: Compliant. Streaming do progresso via WebSocket e logs estruturados no frontend.
- **III. Estética Premium**: Compliant. Visualização no `ExactExtractorPanel` utilizando componentes modernos.
- **IV. Formatos de Exportação Duplos**: Compliant. Exportação dos pares em `.txt` formatado e `.json` estruturado.
- **V. Mecanismo Modular & Factory Pattern**: Compliant. Serviços desacoplados `ExactExtractorService` e `ExactWhatsAppParser`.

## Proposed Architecture & Design

### Artifacts Generated
- [`research.md`](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/006-exact-qa-extractor/research.md): Decisões sobre chunking (100/20 overlap), resiliência de JSON (`max_tokens=4000` + retries) e descarte de saudações e placeholders.
- [`data-model.md`](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/006-exact-qa-extractor/data-model.md): Definição de `RawMessage`, `ChunkConfig`, `LLMQAPairMapping` e `ExactQAPair`.
- [`quickstart.md`](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/006-exact-qa-extractor/quickstart.md): Instruções para testes automatizados com Pytest e especificações do WebSocket.

## Planned Execution Steps

1. **Refatoração e Aprimoramento do Backend (`src/services/exact_extractor.py`)**:
   - Atualizar `EXACT_QA_SYSTEM_PROMPT` para instruir explicitamente o descarte de saudações sem pergunta real e de placeholders como `<Ficheiro não revelado>`.
   - Implementar janelamento por chunks de 100 mensagens com sobreposição de 20 mensagens.
   - Implementar tratamento de exceções com retry automático (capturando `json.JSONDecodeError`) e definir `max_tokens=4000`.
   - Implementar deduplicação de pares extraídos de áreas de sobreposição.

2. **WebSocket Endpoint (`src/api/exact_extractor_ws.py`)**:
   - Ajustar o endpoint para transmitir o progresso dos chunks ao frontend.

3. **Frontend (`frontend/src/`)**:
   - Atualizar a interface do `ExactExtractorPanel` para exibir o progresso do processamento em lote (chunks) e exibir estatísticas consolidadas.

4. **Validação de Testes**:
   - Escrever e atualizar testes unitários em `tests/test_exact_extractor.py` garantindo cobertura do chunking, resiliência a JSONs truncados e descarte de placeholders.
