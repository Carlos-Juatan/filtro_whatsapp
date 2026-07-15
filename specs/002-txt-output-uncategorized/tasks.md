---
description: "Task list for Exportar Conteúdo Não Classificado para Base de Dados implementation"
---

# Tasks: Exportar Conteúdo Não Classificado para Base de Dados

**Input**: Design documents from `/specs/002-txt-output-uncategorized/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The task list below includes unit test tasks as detailed in research.md and quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify the test and development environment before starting.

- [X] T001 [P] Verify the project's current tests run successfully using pytest in backend/
- [X] T002 [P] Verify that frontend compiles and launches with npm run dev in frontend/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Update WebSocket schemas in backend/src/models/schemas.py to include uncategorized_database_content: List[str] in WSChunkSuccessData, WSQueueCompleteData, and WSQueueErrorData
- [X] T004 [P] Update frontend WebSocket types in frontend/src/services/api.ts to include uncategorized_database_content: string[] in WSChunkSuccessData, WSQueueCompleteData, and WSQueueErrorData
- [X] T005 [P] Update the default system prompt text DEFAULT_SYSTEM_PROMPT_TEXT in backend/src/services/prompt_storage.py to instruct OpenAI to extract uncategorized_database_content

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Extração de Fatos e Informações Úteis Não Classificadas (Priority: P1) 🎯 MVP

**Goal**: Extract declarations, schedules, prices, and rules from the chat log using OpenAI models and deduplicate them.

**Independent Test**: Upload a conversation text containing declarations only (no explicit Q&A) and verify backend/services extract the facts.

### Tests for User Story 1
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Create unit tests in backend/tests/test_openai_client.py to verify prompt construction and response parsing of uncategorized_database_content
- [X] T008 [P] [US1] Create unit test in backend/tests/test_consolidator.py to verify deduplicate_uncategorized logic

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement deduplicate_uncategorized helper in backend/src/services/consolidator.py to perform case-insensitive deduplication and strip whitespace
- [X] T009 [US1] Update prompt building logic in backend/src/services/openai_client.py to append instruction suffix to CUSTOMIZADO prompts and parse uncategorized_database_content from JSON response
- [X] T010 [US1] Update WebSocket queue processing in backend/src/api/websocket.py to accumulate uncategorized content from chunks and send in events

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Exportação de Arquivo TXT Adicional (Priority: P1)

**Goal**: Enable downloading the consolidated uncategorized statements as a clean `nao_classificados.txt` file (one statement per line).

**Independent Test**: Download the text file and verify it contains the extracted uncategorized content, one statement per line, separated by newlines, with no Q&A markdown.

### Implementation for User Story 2

- [X] T011 [P] [US2] Implement exportToUncategorizedTxt function in frontend/src/utils/export.ts to generate and download nao_classificados.txt file
- [X] T012 [P] [US2] Add mock data for uncategorized content in frontend/src/services/websocket.ts to support local mock testing
- [X] T013 [US2] Update App.tsx state to track uncategorized_database_content and handle it from completed and error WebSocket events

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Interface de Visualização Integrada (Priority: P2)

**Goal**: Display the uncategorized statements in a dedicated tab/panel side-by-side with Q&A.

**Independent Test**: Navigate to the Results tab after processing and switch between the Q&A table and the new Uncategorized Content list.

### Implementation for User Story 3

- [X] T014 [US3] Update frontend/src/components/ResultsTable.tsx to display a tabbed interface (Q&A vs Uncategorized Content) and show the extracted statements list
- [X] T015 [US3] Add the export button "Baixar Conteúdo Adicional (TXT)" to the results panel in frontend/src/components/ResultsTable.tsx

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T016 Run all backend unit tests using pytest in backend/
- [X] T017 Validate the end-to-end user scenario manually using the quickstart.md guidelines

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Visualizes data from US1 and exports using US2

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- All tests/models within User Story 1 marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members once their backend foundation is set up

---

## Parallel Example: User Story 1

```bash
# Launch both tests for User Story 1 together:
Task: "Create unit tests in backend/tests/test_openai_client.py to verify prompt construction and response parsing of uncategorized_database_content"
Task: "Create unit test in backend/tests/test_consolidator.py to verify deduplicate_uncategorized logic"
```

---

## Implementation Strategy

### MVP First (User Story 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2
5. **STOP and VALIDATE**: Test User Story 1 and 2 independently
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 & 2 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
