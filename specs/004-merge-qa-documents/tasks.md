# Tasks: Consolidated Question & Answer Document Merger

**Input**: Design documents from `/specs/004-merge-qa-documents/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1], [US2], [US3]**: User story mapping from spec.md
- File paths are explicitly specified for each task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and folder structure setup for feature 004

- [x] T001 Initialize data models for Q&A pair and merge request/response in `backend/src/models/merger.py`
- [x] T002 [P] Create frontend API service boilerplate in `frontend/src/services/mergerService.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Base abstractions, contracts, and core navigation prerequisites

- [x] T003 Create base Q&A parser abstract interface and factory in `backend/src/services/qna_parser_factory.py`
- [x] T004 Update UI navigation component using shadcn/ui elements to include the 3rd tool ("Consolidar P&R") in `frontend/src/components/Navigation.tsx`

---

## Phase 3: User Story 1 - Multi-document Selection & Format Ingestion (Priority: P1) 🎯 MVP

**Goal**: Enable users to select multiple JSON or TXT documents and parse Q&A pairs into a processing batch, handling malformed files gracefully.

**Independent Test**: Provide multiple sample JSON and TXT files separately or in batches. Verify that all valid Q&A pairs are extracted without errors and malformed files trigger proper warnings.

### Implementation for User Story 1

- [x] T005 [P] [US1] Implement JSON Q&A parser adhering to `qna_pairs` schema in `backend/src/services/json_qna_parser.py`
- [x] T006 [P] [US1] Implement TXT Q&A parser adhering to block format (`[Metadata] (Frequência: N)`, `Q:`, `A:`) in `backend/src/services/txt_qna_parser.py`
- [x] T007 [US1] Register JSON and TXT parser implementations in factory in `backend/src/services/qna_parser_factory.py`
- [x] T008 [US1] Implement file selection UI, format selector (JSON/TXT), and file batch upload component using shadcn/ui in `frontend/src/components/MergerPanel.tsx`
- [x] T009 [US1] Add unit tests for JSON and TXT parsers including format validation, large batch handling, and malformed file edge cases in `backend/tests/unit/test_qna_parser.py`

**Checkpoint**: User Story 1 is fully functional - files in JSON or TXT format can be ingested and parsed reliably.

---

## Phase 4: User Story 2 - Deduplication & Merging of Q&A Pairs (Priority: P1)

**Goal**: Automatically identify duplicate questions across documents, sum their frequency counts, and retain the most detailed answer.

**Independent Test**: Ingest input documents containing exact and whitespace/case-differing duplicate questions, verify that duplicates are merged, frequencies are summed, and the best answer is selected.

### Implementation for User Story 2

- [x] T010 [US2] Implement deduplication, normalization, frequency summation, and answer selection service in `backend/src/services/qna_merger_service.py`
- [x] T011 [US2] Add unit tests for deduplication logic, frequency summation, and answer selection edge cases — **append** to `backend/tests/unit/test_qna_merger_service.py`

**Checkpoint**: User Story 2 is functional - parsed Q&A pairs are correctly deduplicated and merged.

---

## Phase 5: User Story 3 - Dual Output Export (TXT and JSON) (Priority: P1)

**Goal**: Generate both `.json` and `.txt` files containing the merged Q&A dataset concurrently and return download links/results to the user.

**Independent Test**: Execute a complete merge operation and confirm that both `.json` and `.txt` output files are generated and downloadable via the frontend UI.

### Implementation for User Story 3

- [x] T012 [P] [US3] Implement TXT and JSON file exporters in `backend/src/services/qna_exporter.py`
- [x] T013 [US3] Create FastAPI endpoint `/api/merger/consolidate` handling multi-file upload, parser invocation, merger service, export generation, and returning `MergeJobResult` in `backend/src/api/endpoints/merger.py`
- [x] T014 [US3] Register merger router in main FastAPI application in `backend/src/main.py`
- [x] T015 [US3] Connect frontend `MergerPanel.tsx` to `mergerService.ts` using shadcn/ui interactive components to trigger merge API, show log output, download links, and summary metrics in `frontend/src/components/MergerPanel.tsx`
- [x] T016 [US3] Add API integration tests for `/api/merger/consolidate` endpoint including assertion that output contains zero duplicate Q&A entries (SC-001 coverage) in `backend/tests/integration/test_merger_api.py`

**Checkpoint**: All 3 User Stories are integrated and working end-to-end.

---

## Phase 6: Polish & Router Import Fix

**Purpose**: Fix 405 Method Not Allowed error via package imports fix and verify test suite pass rate

- [x] T017 [P] Add Tailwind glassmorphism styles, hover micro-animations, and status badges to `frontend/src/components/MergerPanel.tsx`
- [x] T018 Fix backend import paths with `src.` prefix across merger router and services to resolve 405 Method Not Allowed error in `backend/src/api/endpoints/merger.py`

---

## Phase 7: ChatGPT Prompt Integration (`TipoFerramenta.CONSOLIDADOR`) (Priority: P1)

**Goal**: Integrate ChatGPT (OpenAI API) with standard prompt configuration for Q&A consolidation and deduplication.

**Independent Test**: Trigger consolidation with an active OpenAI key. Verify pre-grouped batches are refined via ChatGPT using the default `CONSOLIDADOR` prompt, and fallback to local merging occurs if no API key is set.

### Implementation for Phase 7

- [X] T019 [P] [US2] Add `TipoFerramenta.CONSOLIDADOR` ("consolidador") to Enum in `backend/src/models/schemas.py` and `TipoFerramenta` type in `frontend/src/services/api.ts`
- [X] T020 [P] [US2] Register default `CONSOLIDADOR` system prompt text in `backend/src/services/prompt_storage.py` and add migration unit tests — **append** to `backend/tests/unit/test_prompt_storage_migration.py` (create file if absent under `unit/`)
- [X] T021 [US2] [FR-011] Integrate OpenAI API call with `TipoFerramenta.CONSOLIDADOR` prompt in `backend/src/services/qna_merger_service.py` with graceful fallback to local merge when no API key is configured; notify user via response field that AI consolidation was skipped
- [X] T022 [US3] Update prompt selection and status feedback using shadcn/ui components in `frontend/src/components/MergerPanel.tsx`
- [X] T023 [US2] Add unit tests for ChatGPT merger service integration and fallback logic — **append** to `backend/tests/unit/test_qna_merger_service.py` (same file as T011; do not overwrite existing tests)
- [X] T024 [US3] Update API integration tests for `/api/merger/consolidate` in `backend/tests/integration/test_merger_api.py`
- [X] T025 [P] [SC-001] Add parametric pytest scenario in `backend/tests/integration/test_merger_api.py` asserting zero duplicate `perguntaPadronizada` values in the JSON output after full consolidation run (SC-001 verification)

---

## Phase 8: Tool Improvements — TXT Format, Logging & Chunked Processing (Priority: P1)

**Goal**: Correct TXT output separator format, add detailed real-time processing logs to the UI (following the pattern of existing tools), and replace the monolithic Q&A merging loop with a chunked batch strategy to handle large documents without hanging the LLM.

**Independent Test**: Run a consolidation with 300+ Q&A pairs and verify: (a) the `.txt` output uses `----------------------------------------` after every `A:` line including the last; (b) the UI log displays one event per stage in near-real-time; (c) the process completes without timeout or LLM context overflow.

### Implementation for Phase 8

- [ ] T026 [FR-009] [SC-002] Fix TXT exporter to always append a `----------------------------------------` separator line after every `A:` block, including the final block of the file — update `backend/src/services/qna_exporter.py`
- [ ] T027 [P] [FR-012] [SC-004] Define a `MergerLogEvent` schema (event type, message, timestamp, optional metadata) and expose a streaming/SSE or WebSocket log endpoint for real-time progress emission — update `backend/src/models/merger.py` and create `backend/src/api/endpoints/merger_log.py`
- [ ] T028 [FR-012] [SC-004] Instrument the consolidation pipeline (parser, merger service, exporter) to emit `MergerLogEvent` entries at each stage transition (file parse start/end, dedup start/end, chunk progress, export start/end, warnings) — update `backend/src/services/qna_merger_service.py` and `backend/src/services/qna_exporter.py`
- [ ] T029 [FR-012] [SC-004] Connect `MergerPanel.tsx` to the log stream endpoint and render a real-time scrollable log panel with stage labels, timestamps, and warning highlights — update `frontend/src/components/MergerPanel.tsx`
- [ ] T030 [P] [FR-013] [FR-014] [SC-005] Implement configurable chunked batch processing engine in `backend/src/services/qna_chunk_processor.py`:
  - Split the main (accumulated) Q&A document into chunks of `CHUNK_SIZE` pairs (default: 30).
  - Split incoming new pairs into batches of `BATCH_SIZE` (default: 30).
  - For each batch: iterate over all chunks sequentially; merge duplicates inline (by normalized `perguntaPadronizada`); append unmatched pairs to the main document after all chunks are processed.
  - Repeat for subsequent batches using the updated main document as the new reference.
  - `CHUNK_SIZE` and `BATCH_SIZE` are read from environment/config (FR-014).
- [ ] T031 [FR-013] [FR-014] Replace the current monolithic merge loop in `backend/src/services/qna_merger_service.py` with calls to the new `QnaChunkProcessor` from T030; ensure the AI consolidation step (T021) also uses chunk-aware batching when calling the ChatGPT API.
- [ ] T032 [P] Add unit tests for the `QnaChunkProcessor` covering: small batches (<30 pairs, no chunking needed), large batches (300+ pairs across multiple chunks), duplicate merging within and across chunk boundaries, and configurable `CHUNK_SIZE`/`BATCH_SIZE` — create `backend/tests/unit/test_qna_chunk_processor.py`
- [ ] T033 Update API integration tests to validate Phase 8 improvements: assert TXT separator present on last block (SC-002), assert log events emitted (SC-004), assert 300-pair consolidation completes without error (SC-005) — **append** to `backend/tests/integration/test_merger_api.py`

**Checkpoint**: TXT output is correctly formatted, UI shows real-time logs, and large-document consolidation no longer hangs.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Completed.
- **Foundational (Phase 2)**: Completed.
- **User Story 1 (Phase 3)**: Completed.
- **User Story 2 (Phase 4)**: Completed.
- **User Story 3 (Phase 5)**: Completed.
- **Polish & Router Fix (Phase 6)**: Completed.
- **ChatGPT Prompt Integration (Phase 7)**: Completed. Includes T025 (SC-001 verification).
- **Tool Improvements (Phase 8)**: Depends on Phase 7. T027 and T030 can run in parallel; T028 depends on T027; T031 depends on T030; T029 depends on T027/T028; T032 depends on T030; T033 depends on T026–T031.

### Parallel Opportunities in Phase 7

- **T019 & T020**: Extend Enum `TipoFerramenta` in models and register default prompt in storage service in parallel.

### Parallel Opportunities in Phase 8

- **T026**: Can run immediately in parallel with T027 and T030 (independent files).
- **T027 & T030**: Can run in parallel (independent service/model work).

---

## Implementation Strategy

1. Execute T019 and T020 (Enum addition & default prompt registration).
2. Execute T021 (Backend ChatGPT consolidation service logic & fallback — also satisfies FR-011).
3. Execute T022 (Frontend prompt selection / UI feedback using shadcn/ui).
4. Execute T023 and T024 (Unit & integration testing — T023 appends to existing test file).
5. Execute T025 (SC-001 zero-duplicate parametric verification test).
6. Execute T026 (TXT separator fix) in parallel with T027 (log event schema + endpoint) and T030 (chunk processor engine).
7. Execute T028 (pipeline instrumentation) after T027; execute T031 (merger service integration) after T030.
8. Execute T029 (frontend log panel) after T028.
9. Execute T032 (chunk processor unit tests) after T030.
10. Execute T033 (integration test updates) after T026–T031 are complete.
