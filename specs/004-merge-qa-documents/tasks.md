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

- [ ] T005 [P] [US1] Implement JSON Q&A parser adhering to `qna_pairs` schema in `backend/src/services/json_qna_parser.py`
- [ ] T006 [P] [US1] Implement TXT Q&A parser adhering to block format (`[Metadata] (Frequência: N)`, `Q:`, `A:`) in `backend/src/services/txt_qna_parser.py`
- [ ] T007 [US1] Register JSON and TXT parser implementations in factory in `backend/src/services/qna_parser_factory.py`
- [ ] T008 [US1] Implement file selection UI, format selector (JSON/TXT), and file batch upload component using shadcn/ui in `frontend/src/components/MergerPanel.tsx`
- [ ] T009 [US1] Add unit tests for JSON and TXT parsers including format validation, large batch handling, and malformed file edge cases in `backend/tests/unit/test_qna_parser.py`

**Checkpoint**: User Story 1 is fully functional - files in JSON or TXT format can be ingested and parsed reliably.

---

## Phase 4: User Story 2 - Deduplication & Merging of Q&A Pairs (Priority: P1)

**Goal**: Automatically identify duplicate questions across documents, sum their frequency counts, and retain the most detailed answer.

**Independent Test**: Ingest input documents containing exact and whitespace/case-differing duplicate questions, verify that duplicates are merged, frequencies are summed, and the best answer is selected.

### Implementation for User Story 2

- [ ] T010 [US2] Implement deduplication, normalization, frequency summation, and answer selection service in `backend/src/services/qna_merger_service.py`
- [ ] T011 [US2] Add unit tests for deduplication logic, frequency summation, and answer selection edge cases in `backend/tests/unit/test_qna_merger_service.py`

**Checkpoint**: User Story 2 is functional - parsed Q&A pairs are correctly deduplicated and merged.

---

## Phase 5: User Story 3 - Dual Output Export (TXT and JSON) (Priority: P1)

**Goal**: Generate both `.json` and `.txt` files containing the merged Q&A dataset concurrently and return download links/results to the user.

**Independent Test**: Execute a complete merge operation and confirm that both `.json` and `.txt` output files are generated and downloadable via the frontend UI.

### Implementation for User Story 3

- [ ] T012 [P] [US3] Implement TXT and JSON file exporters in `backend/src/services/qna_exporter.py`
- [ ] T013 [US3] Create FastAPI endpoint `/api/merger/merge` handling multi-file upload, parser invocation, merger service, export generation, and returning `MergeJobResult` in `backend/src/api/endpoints/merger.py`
- [ ] T014 [US3] Register merger router in main FastAPI application in `backend/src/main.py`
- [ ] T015 [US3] Connect frontend `MergerPanel.tsx` to `mergerService.ts` to trigger merge API, show log output, download links, and summary metrics in `frontend/src/components/MergerPanel.tsx`
- [ ] T016 [US3] Add API integration tests for `/api/merger/merge` endpoint in `backend/tests/integration/test_merger_api.py`

**Checkpoint**: All 3 User Stories are integrated and working end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Overall UI refinement, micro-animations, error boundary handling, and test validation

- [ ] T017 [P] Add Tailwind glassmorphism styles, hover micro-animations, and status badges to `frontend/src/components/MergerPanel.tsx`
- [ ] T018 Run test suite (`pytest`) to ensure 100% pass rate across unit and integration tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all User Stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on US1 (ingestion/parsers).
- **User Story 3 (Phase 5)**: Depends on US2 (merged dataset) and US1.
- **Polish (Phase 6)**: Depends on Phase 5.

### Parallel Opportunities

- **T001 & T002**: Setup data models (backend) and API service (frontend) in parallel.
- **T005 & T006**: Implement JSON parser and TXT parser in parallel.
- **T012**: Implement exporters while finalizing merger service.
- **T017**: Polish UI while tests run.

---

## Implementation Strategy

### MVP First (User Story 1 - 3 Sequence)

1. Complete Phase 1 & Phase 2.
2. Build US1 (Parsers) -> US2 (Merger) -> US3 (Endpoint & Export).
3. Validate end-to-end flow with sample JSON/TXT files.
4. Execute Polish & test verification.
