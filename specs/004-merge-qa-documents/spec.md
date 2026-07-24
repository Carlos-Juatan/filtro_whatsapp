# Feature Specification: Consolidated Question & Answer Document Merger

**Feature Branch**: `004-merge-qa-documents`  
**Created**: 2026-07-24  
**Status**: Draft  
**Input**: User description: "Vamos criar uma nova ferramenta separada das outras agora para juntar as perguntas e respostas de vários documentos em um conjunto, eu quero poder escolher se os documentos enviados serão em json ou em txt e enviar vários documentos para juntar em uma saída de um arquivo txt e um arquivo json com as perguntas e respostas juntas, além disso, as perguntas e respostas que estiverem repetidas serão mescladas."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-document Selection & Format Ingestion (Priority: P1)

As a user with multiple Q&A files, I want to select several documents in JSON or TXT format so that the tool can parse and ingest all question-and-answer pairs into a single processing batch.

**Why this priority**: Core entry point for processing data. Without input selection and parsing of TXT/JSON documents, no merging can occur.

**Independent Test**: Provide multiple sample JSON files and TXT files separately or selected together, verify the tool successfully extracts all raw Q&A pairs without crashing.

**Acceptance Scenarios**:

1. **Given** a set of valid JSON files containing Q&A pairs, **When** the user selects JSON mode and inputs the files, **Then** all Q&A pairs from all files are extracted into memory.
2. **Given** a set of valid TXT files containing Q&A pairs formatted with clear question/answer delimiters, **When** the user selects TXT mode and inputs the files, **Then** all Q&A pairs are extracted into memory.
3. **Given** invalid or unparseable input files, **When** ingestion runs, **Then** the user receives an informative error detailing which file failed and why.

---

### User Story 2 - Deduplication & Merging of Q&A Pairs (Priority: P1)

As a user, I want duplicate questions and answers across documents to be automatically merged so that the consolidated dataset contains clean, non-repetitive content.

**Why this priority**: Deduplication is the primary value proposition requested to clean and unify fragmented documents.

**Independent Test**: Supply input documents containing exact and near-exact duplicate questions/answers, verify that the resulting internal dataset has merged duplicates into single entries.

**Acceptance Scenarios**:

1. **Given** multiple Q&A entries with identical questions across different files, **When** deduplication runs, **Then** identical entries are merged into a single Q&A pair without repetition.
2. **Given** Q&A entries with identical questions but slight whitespace/formatting differences, **When** deduplication runs, **Then** normalized matching identifies them as duplicates and consolidates them appropriately.

---

### User Story 3 - Dual Output Export (TXT and JSON) (Priority: P1)

As a user, I want the tool to output the consolidated Q&A dataset simultaneously into a TXT file and a JSON file so that I can use the result in different downstream applications.

**Why this priority**: The user explicitly requested outputs in both `.txt` and `.json` files concurrently.

**Independent Test**: Run a full processing flow and verify that both a `.txt` file and a `.json` file are generated containing the exact same consolidated set of Q&A pairs formatted appropriately for each file type.

**Acceptance Scenarios**:

1. **Given** a completed deduplicated Q&A batch, **When** export is executed, **Then** a `.json` file containing structured Q&A objects and a `.txt` file containing human-readable formatted Q&A text are generated.
2. **Given** a designated output location, **When** export finishes, **Then** the user is informed of the export success with file locations.

---

### Edge Cases

- What happens when an input file contains incomplete Q&A pairs (e.g., a question without a corresponding answer)?
- How does the system handle very large text files or hundreds of files selected simultaneously?
- What happens if the selected input format (e.g., JSON) does not match the actual file contents (e.g., plain text disguised as `.json`)?

## Clarifications

### Session 2026-07-24
- Q: What exact format/structure should be used for JSON and TXT parsing and generation? → A: Use the project's existing tool format: JSON uses `qna_pairs` array with `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, and `category`. TXT uses `[<metadata>] (Frequência: <n>)` blocks followed by `Q: ...` and `A: ...` lines with `----------------------------------------` delimiters.
- Q: How should duplicates and frequencies be merged when matching questions are found? → A: Merge matching questions by summing their `frequencia` values and retaining the most detailed (longest/most complete) answer string.
- Q: How should the tool be integrated into the user interface? → A: Integrate as the 3rd tool option within the existing application's multi-tool Navigation / Config panel alongside the existing tools.
- Q: How should malformed files in a batch be handled during processing? → A: Skip the malformed file with a warning notification to the user, and continue processing all remaining valid files in the batch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a new dedicated 3rd tool interface within the existing application navigation structure, following the exact UI pattern of existing tools.
- **FR-002**: The system MUST allow the user to specify the input file format (JSON or TXT) when supplying input files.
- **FR-003**: The system MUST accept multiple input files in a single batch operation.
- **FR-004**: The system MUST parse JSON files matching the project format with a `qna_pairs` array containing `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, and `category`.
- **FR-005**: The system MUST parse TXT files structured with `[<metadata>] (Frequência: <n>)`, `Q: <question>`, and `A: <answer>` sections delimited by `----------------------------------------`.
- **FR-006**: The system MUST identify repeated questions across ingested documents, merge them into single entries by summing their `frequencia` values, and select the most detailed answer when slight answer differences exist.
- **FR-007**: The system MUST automatically generate two output files for every completed consolidation run: one `.txt` file and one `.json` file.
- **FR-008**: The JSON output MUST follow the `qna_pairs` schema structure (`perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, `category`).
- **FR-009**: The TXT output MUST format questions and answers using the standard `[<metadata>] (Frequência: <n>)\nQ: ...\nA: ...\n----------------------------------------` block format.
- **FR-010**: The system MUST gracefully handle malformed or unparseable files by logging a warning, skipping the invalid file, and processing all remaining valid files in the batch.

### Key Entities *(include if feature involves data)*

- **QA Pair**: Represents a single question-and-answer pair (`perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, `category`).
- **Consolidation Job**: Represents a single execution run with input format selection, list of input files, status, and generated output paths.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of identical duplicate Q&A pairs across input documents are merged, resulting in zero exact duplicate entries in the final outputs while combining their frequency counts.
- **SC-002**: Every consolidation run successfully creates both valid `.json` and readable `.txt` export files conforming strictly to the project schema.
- **SC-003**: Users can complete input selection, format choice, and consolidation in under 1 minute for standard file batches (up to 50 files).

## Assumptions

- The tool is standalone and does not overwrite existing app features.
- TXT input files use the standard project format (`[Metadata] (Frequência: X)\nQ: ...\nA: ...`).
- Duplicate detection matches questions using case-insensitive and whitespace-normalized string comparisons.
