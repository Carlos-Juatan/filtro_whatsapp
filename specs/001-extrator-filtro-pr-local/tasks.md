---
description: "Implementation tasks for the Extrator e Filtro de P&R (Local) feature"
---

# Tasks: Extrator e Filtro de P&R (Local)

**Input**: Design documents from `/specs/001-extrator-filtro-pr-local/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Simple automated unit and integration tests are included using `pytest` (backend) and `vitest` (frontend) as planned.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and workspace folder creation

- [X] T001 Initialize workspace directory structure under backend/ and frontend/
- [X] T002 Initialize backend FastAPI app configuration and dependencies in backend/requirements.txt
- [X] T003 Initialize frontend React Vite app config, shadcn/ui configuration (components.json), and install dependencies in frontend/package.json and frontend/vite.config.ts
- [X] T003a Configure Vitest testing environment and dependencies in frontend/
- [X] T004 [P] Configure development server scripts and Docker environment files in docker-compose.yml and .env

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Define Pydantic models for ChaveAPI, PromptConfig, and LogItem in backend/src/models/schemas.py
- [X] T006 Configure FastAPI router registry and error handlers in backend/src/main.py
- [X] T007 Configure frontend routing, Axios API client instance, proxy, and ApiClientFactory in frontend/src/services/api.ts
- [X] T008 Setup single-container production multi-stage build instructions in backend/Dockerfile

**Checkpoint**: Foundation ready - user story implementation can now begin in priority order

---

## Phase 3: User Story 1 - Processamento Local de P&R com Fatiamento e Fila (Priority: P1) 🎯 MVP

**Goal**: Split large text files securely using tiktoken token-based chunking, process them sequentially via the OpenAI API, and stream progress logs in real-time.

**Independent Test**: Connect to the WebSocket endpoint `/api/process` with a large text file, and verify logs show sequential chunk parsing and success events without crashing.

### Implementation for User Story 1

- [X] T009 [P] [US1] Create ParserFactory and TxtParser class in backend/src/services/parsers.py
- [X] T010 [P] [US1] Implement cl100k_base token counting and split algorithm in backend/src/services/chunker.py
- [X] T011 [US1] Implement OpenAI client manager with exponential backoff retry in backend/src/services/openai_client.py
- [X] T012 [US1] Implement WebSocket processor connection handler and FIFO queue in backend/src/api/websocket.py
- [X] T013 [P] [US1] Implement WebSocket client service connection manager in frontend/src/services/websocket.ts
- [X] T014 [US1] Create file upload drag-and-drop, upload list showing status/size, and progress bar component in frontend/src/components/FileUploader.tsx
- [X] T015 [US1] Implement log viewer pane with level-based syntax highlighting in frontend/src/components/LogViewer.tsx
- [X] T016 [P] [US1] Write backend unit tests for chunker, parsers, and processor in backend/tests/test_processing.py
- [X] T016a [P] [US1] Write frontend component tests for FileUploader and LogViewer in frontend/tests/components.test.tsx using Vitest

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Exibição de Resultados Agrupados e Exportação (Priority: P1)

**Goal**: Consolidate similar Q&As semantically, compute frequency counts, display the results in a grid, and export them as TXT/JSON.

**Independent Test**: Process a file with similar questions, confirm they are merged and mapped under a single answer with updated frequency counts, and verify both TXT and JSON exports are correctly formatted.

### Implementation for User Story 2

- [x] T017 [US2] Implement LLM semantic deduplication and consolidation service (extracting metadata and category labels) in backend/src/services/consolidator.py
- [x] T018 [P] [US2] Write unit tests for semantic consolidation logic in backend/tests/test_consolidator.py
- [x] T019 [US2] Create results table component with search and sorting in frontend/src/components/ResultsTable.tsx
- [x] T020 [P] [US2] Implement TXT/JSON generation (with client-side JSON schema validation against ResultadoParPR) and download trigger in frontend/src/utils/export.ts
- [x] T021 [US2] Orchestrate main application layout, tab selection, and global state in frontend/src/App.tsx
- [x] T021a [P] [US2] Write frontend component tests for ResultsTable and export utilities in frontend/tests/results.test.tsx using Vitest

**Checkpoint**: At this point, User Stories 1 AND 2 are functional together.

---

## Phase 5: User Story 3 - Gestão e Seleção de Chaves de API em Volume Docker (Priority: P1)

**Goal**: Save OpenAI API keys locally in a persistent JSON volume file, with ID and unique identification name, allowing selection or deletion.

**Independent Test**: Add a new key name and string in settings, reload the browser, and verify it is still populated from the backend.

### Implementation for User Story 3

- [ ] T022 [P] [US3] Implement JSON-file-based persistent storage for API keys in backend/src/services/key_storage.py
- [ ] T023 [US3] Implement API key router endpoints GET, POST, and DELETE in backend/src/api/routes/keys.py
- [ ] T024 [P] [US3] Create API client interface for key operations in frontend/src/services/keys.ts
- [ ] T025 [US3] Create key management setting form and list in frontend/src/components/KeySettings.tsx
- [ ] T026 [P] [US3] Write unit tests for API key serialization and unique constraint in backend/tests/test_keys.py
- [ ] T026a [P] [US3] Write frontend component tests for KeySettings in frontend/tests/keys.test.tsx using Vitest

**Checkpoint**: At this point, API keys can be managed and selected.

---

## Phase 6: User Story 4 - Configuração de Prompt Personalizado e Seleção de Idioma (Priority: P2)

**Goal**: Customize prompt templates (fixed/custom) and configure OpenAI model/language selection, persisting parameters in the Docker volume.

**Independent Test**: Select a custom prompt and set language to English. Run extraction on a Portuguese text, verifying the output is in English and respects the custom prompt guidelines.

### Implementation for User Story 4

- [ ] T027 [P] [US4] Implement JSON-file-based persistent storage for PromptConfig in backend/src/services/prompt_storage.py
- [ ] T028 [US4] Implement PromptConfig endpoints GET and POST in backend/src/api/routes/prompts.py
- [ ] T029 [P] [US4] Create API client interface for prompt operations in frontend/src/services/prompts.ts
- [ ] T030 [US4] Create prompt/model/language configurations UI form in frontend/src/components/PromptSettings.tsx
- [ ] T031 [P] [US4] Write unit tests for prompt formatting and persistence in backend/tests/test_prompts.py
- [ ] T031a [P] [US4] Write frontend component tests for PromptSettings in frontend/tests/prompts.test.tsx using Vitest

**Checkpoint**: Prompt configuration and language parameters are fully integrated.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Visual improvements, container building validation, and complete E2E system testing.

- [ ] T032 Verify system functionality end-to-end under docker-compose local build using docker-compose.yml
- [ ] T033 Apply premium custom styling, Outfit font integration, dark-mode styling, and transitions in frontend/src/index.css
- [ ] T034 [P] Write integration tests for end-to-end processing pipeline in backend/tests/test_integration.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User Story 1 (P1) is the MVP engine.
  - User Story 2 (P1) consumes US1 results.
  - User Story 3 (P1) provides API keys.
  - User Story 4 (P2) customizes US1 prompts.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1**: Can run with environment variables or hardcoded values initially. Integration with US3/US4 occurs once they are finished.
- **User Story 2**: Depends on User Story 1 results.
- **User Story 3**: Independent of US1/US2.
- **User Story 4**: Independent of US1/US2.

### Within Each User Story

- Models are created before services.
- Services are created before endpoints/controllers.
- Core backend functionality is built before frontend components.
- Story complete before moving to next priority.

### Parallel Opportunities

- All Setup tasks (Phase 1) can run sequentially or in parallel for configuration items.
- Chunker (`T010`) and Parser (`T009`) in User Story 1 can be developed in parallel.
- API Key and PromptConfig persistent storages (`T022`, `T027`) can be developed in parallel.
- Unit tests (`T016`, `T018`, `T026`, `T031`, `T034`) can be written in parallel with corresponding implementations.

---

## Parallel Example: User Story 1

```bash
# Developer A: Implement text chunker
Task: "Implement cl100k_base token counting and split algorithm in backend/src/services/chunker.py"

# Developer B: Implement file parsing
Task: "Create ParserFactory and TxtParser class in backend/src/services/parsers.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete **Phase 1 (Setup)**.
2. Complete **Phase 2 (Foundational)**.
3. Complete **Phase 3 (User Story 1)** using hardcoded key or config values.
4. Complete **Phase 4 (User Story 2)**.
5. **STOP and VALIDATE**: Verify file processing, semantic consolidation, and exports work correctly.
6. Complete **Phase 5 (User Story 3)** and **Phase 6 (User Story 4)** to add configuration.
7. Complete **Phase 7 (Polish & Cross-Cutting)**.
