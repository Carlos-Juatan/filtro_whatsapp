# Tasks: Extração Exata de Perguntas e Respostas do WhatsApp

**Feature Branch**: `006-exact-qa-extractor`  
**Feature Name**: Extração Exata de P&R  
**Spec**: [`specs/006-exact-qa-extractor/spec.md`](./spec.md)  
**Plan**: [`specs/006-exact-qa-extractor/plan.md`](./plan.md)  

---

## Dependency Graph

```mermaid
flowchart TD
    Phase1[Phase 1: Setup & Data Models] --> Phase2[Phase 2: Foundational Components]
    Phase2 --> Phase3[Phase 3: User Story 1 - Extração Exata (P1)]
    Phase3 --> Phase4[Phase 4: User Story 2 - Indexação Determinística (P2)]
    Phase4 --> Phase5[Phase 5: User Story 3 - Mapeamento e Reconstrução (P3)]
    Phase5 --> Phase6[Phase 6: Polish & Cross-Cutting]
```

---

## Execution Tasks

### Phase 1: Setup & Data Models

- [ ] T001 Define Pydantic data schemas for raw messages and exact QA pairs in `backend/src/models/exact_qa.py`
- [ ] T002 Define TypeScript interfaces for exact QA extraction state in `frontend/src/types/exactQA.ts`

---

### Phase 2: Foundational Components

- [ ] T003 Implement unit tests for the deterministic WhatsApp message parser in `backend/tests/test_exact_parser.py`
- [ ] T004 Implement deterministic WhatsApp message parser in `backend/src/services/exact_parser.py`
- [ ] T005 Implement unit tests for LLM ID mapping and exact text reconstruction in `backend/tests/test_exact_extractor.py`
- [ ] T006 Implement exact text reconstruction service and LLM prompt handler in `backend/src/services/exact_extractor.py`

---

### Phase 3: User Story 1 - Extração Exata de Pares Pergunta/Resposta (Priority: P1)

**Goal**: Garantir a extração exata de pares de pergunta e resposta preservando 100% o texto bruto original.  
**Independent Test**: Enviar um arquivo `.txt` do WhatsApp com perguntas/respostas conhecidas e validar se o texto retornado pela API coincide caractere por caractere com o original.

- [ ] T007 [US1] Create WebSocket router for exact QA extraction service in `backend/src/api/exact_extractor_ws.py`
- [ ] T008 [US1] Register `exact_extractor_ws` router in FastAPI application in `backend/src/main.py`
- [ ] T009 [US1] Create exact extraction WebSocket client service in `frontend/src/services/exactExtractorService.ts`

---

### Phase 4: User Story 2 - Indexação Determinística das Mensagens (Priority: P2)

**Goal**: Atribuir IDs únicos e sequenciais a todas as mensagens do arquivo `.txt` antes de enviar à IA.  
**Independent Test**: Executar o parser determinístico em um arquivo com quebras de linha e emojis e verificar a atribuição correta de IDs (`MSG-0001`, `MSG-0002`).

- [ ] T010 [US2] Update exact parser service in `backend/src/services/exact_parser.py` to handle multiline messages and timestamp edge cases

---

### Phase 5: User Story 3 - Mapeamento e Reconstrução por IDs (Priority: P3)

**Goal**: Exibir a interface gráfica e permitir a visualização e exportação dos resultados reconstruídos nos formatos `.txt` e `.json`.  
**Independent Test**: Carregar um arquivo na UI, acompanhar os logs de progresso e baixar os arquivos de exportação formatados.

- [ ] T011 [US3] Build `ExactExtractorPanel.tsx` UI component in `frontend/src/components/ExactExtractorPanel.tsx`
- [ ] T012 [US3] Register `ExactExtractorPanel` component and header navigation button in `frontend/src/App.tsx`
- [ ] T013 [US3] Implement `.txt` and `.json` exporter functions for exact QA pairs in `frontend/src/utils/exactExporters.ts`

---

### Phase 6: Polish & Cross-Cutting Concerns

- [ ] T014 Run full pytest suite for backend services (`pytest backend/tests/`)
- [ ] T015 Verify single-container Docker build and local execution via `docker-compose up --build`

---

## Implementation Strategy & MVP Scope

1. **MVP Scope**: Concluir as Fases 1, 2 e 3 (User Story 1), o que entregará o parser backend funcional, o endpoint WebSocket e o serviço de comunicação básico para testes de extração.
2. **Entrega Incremental**:
   - **Etapa 1**: Estrutura de dados e Parser determinístico com testes pytest (Fases 1 e 2).
   - **Etapa 2**: Integração WebSocket Backend/Frontend e Reconstrução Exata por IDs (Fase 3).
   - **Etapa 3**: Refinamento de borda e interface web com download de resultados em `.txt` e `.json` (Fases 4 e 5).
