# Tasks: Gerador de Perguntas

**Input**: Design documents from `/specs/003-gerador-perguntas/`  
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Back-end unit and integration tests are generated as part of Setup and Foundational tasks to ensure correctness of prompt migration and the WebSocket connection.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- File paths are explicitly specified in the task description.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update database models, prompt configuration schemas, and REST endpoints to support tool-specific prompt segregation and in-memory migrations.

- [ ] T001 [P] Add TipoFerramenta enum and ferramenta field to PromptConfig schemas in backend/src/models/schemas.py
- [ ] T002 Update PromptStorageService in backend/src/services/prompt_storage.py to support in-memory migration of prompts and seed the default generator prompt
- [ ] T003 [P] Add query parameter filtering to get_prompts endpoint in backend/src/api/routes/prompts.py
- [ ] T004 [P] Add TipoFerramenta type and ferramenta field to PromptConfig interfaces in frontend/src/services/api.ts
- [ ] T005 [P] Update ApiClient interface and listPrompts implementation to support tool filtering in frontend/src/services/api.ts
- [ ] T006 [P] Add backend unit tests for prompt migrations and filtering in backend/tests/test_prompt_storage_migration.py

**Checkpoint**: Shared models, storage, and API prompt filtering are verified by tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the back-end LLM prompt generator client and WebSocket generator endpoint to handle connection queues and stream events.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T007 [P] Create question generation logic and LLM prompt in backend/src/services/generator_client.py
- [ ] T008 Create WebSocket generator endpoint and message queue handling in backend/src/api/websocket_generator.py
- [ ] T009 [P] Register the new WebSocket router in backend/src/main.py
- [ ] T010 [P] Add backend integration tests for the /api/generate WebSocket in backend/tests/test_websocket_generator.py

**Checkpoint**: The WebSocket `/api/generate` is fully functional and can run Q&A generation from backend payloads.

---

## Phase 3: User Story 1 - Geração de Perguntas por IA a partir de Conteúdo Não Classificado (Priority: P1) 🎯 MVP

**Goal**: Enable uploading `.txt` files containing facts, chunking them, initiating `/api/generate` WS connection, streaming processing logs, and displaying the consolidated results table.

**Independent Test**: Upload a test `.txt` file with known statements (e.g. "O horário de atendimento é das 8h às 18h."), start generation, verify that a corresponding question is created ("Qual o horário de atendimento?"), its answer is the statement, it is mapped in the results table, and is consolidated.

### Implementation for User Story 1

- [ ] T011 [US1] Parameterize WebSocket connection client to support endpoint path arguments in frontend/src/services/websocket.ts
- [ ] T012 [P] [US1] Create the GeneratorPanel scaffolding in frontend/src/components/GeneratorPanel.tsx
- [ ] T013 [US1] Implement file dropzone and list display with token count details in frontend/src/components/GeneratorPanel.tsx
- [ ] T014 [US1] Implement WebSocket processing queue hook/state (connect, start, logs stream) in frontend/src/components/GeneratorPanel.tsx
- [ ] T015 [US1] Implement results table for generated pairs (question, answer, frequency, category, metadata) in frontend/src/components/GeneratorPanel.tsx
- [ ] T016 [US1] Implement prompt dropdown and configuration trigger filtering for "gerador" prompts in frontend/src/components/GeneratorPanel.tsx

**Checkpoint**: User Story 1 is fully functional. Users can generate Q&As from uploaded text files and view them on the screen in a table.

---

## Phase 4: User Story 2 - Menu Principal de Navegação Separado (Priority: P2)

**Goal**: Decouple the UI so that Extrator and Gerador components reside in their own panels, navigated via a top header menu, preserving state when switching tabs.

**Independent Test**: Connect to the dev server, switch between the Extrator and Gerador tabs, verify that uploaded files, logs, and results table contents in one tab do not leak or reset the state of the other tab.

### Implementation for User Story 2

- [ ] T017 [US2] Refactor App.tsx main body layout into ExtractorPanel.tsx in frontend/src/components/ExtractorPanel.tsx
- [ ] T018 [US2] Update App.tsx to use a clean tab/navigation bar at the top to toggle active panels
- [ ] T019 [US2] Integrate ExtractorPanel and GeneratorPanel into the main tab system in frontend/src/App.tsx
- [ ] T020 [P] [US2] Add animation and transitions for smooth panel switching in frontend/src/App.tsx and frontend/src/index.css

**Checkpoint**: Main navigation allows switching screens in <150ms without cross-tab state leakage.

---

## Phase 5: User Story 3 - Exportação de Resultados no Mesmo Formato Anterior (Priority: P3)

**Goal**: Provide buttons in the results panel to download TXT (structured FAQ layout) and JSON (exact same keys structure) files of the generated Q&As.

**Independent Test**: Generate Q&A pairs, export to JSON and TXT, and run schema validation on the generated JSON to verify keys match the original schema (`qna_pairs` containing items with `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, `category`).

### Implementation for User Story 3

- [ ] T021 [US3] Implement export to TXT logic using the exact ResultadoParPR structure in frontend/src/components/GeneratorPanel.tsx
- [ ] T022 [US3] Implement export to JSON logic matching the schema with qna_pairs key in frontend/src/components/GeneratorPanel.tsx
- [ ] T023 [P] [US3] Add interactive browser validation test scenario or unit tests for export download actions in frontend/src/test/export.test.ts

**Checkpoint**: Exported TXT and JSON output structures match the Extrator output exactly.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate edge cases, clean up unused logs/debug details, and run validation of the quickstart guide.

- [ ] T024 Run linting, formatting, and quickstart.md validation manually
- [ ] T025 Verify edge cases (empty files, API rate limit exhaustion) behave safely without connection leaks
- [ ] T026 Update user documentation and clean up any debug statements

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. Blocks frontend user stories.
- **User Stories (Phase 3+)**: Depend on Foundational completion.
  - User Story 1 (P1 - MVP) is independent of other user stories.
  - User Story 2 (P2) is independent but integrates both panels in `App.tsx`.
  - User Story 3 (P3) is built into the GeneratorPanel (completed in US1).
- **Polish (Phase 6)**: Runs after all user stories are complete.

### Parallel Opportunities
- All Setup tasks marked [P] (T001, T003, T004, T005, T006) can run in parallel once T001/T002 schemas are in place.
- Backend tasks T007, T009, T010 can run in parallel during Foundational.
- Frontend panels (T012 scaffolding, and initial UI layouts) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **Validate**: Test Q&A generation lifecycle manually by uploading test files.

### Incremental Delivery
1. Setup + Foundation ready.
2. User Story 1 integrated (allows Q&A generation).
3. User Story 2 integrated (splits UI into two clean tabs).
4. User Story 3 integrated (enables TXT/JSON exports).
5. Run final Polish.
