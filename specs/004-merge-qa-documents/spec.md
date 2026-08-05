# Feature Specification: Consolidated Question & Answer Document Merger

**Feature Branch**: `004-merge-qa-documents`  
**Created**: 2026-07-24  
**Status**: In Progress  
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

1. **Given** multiple Q&A entries with identical questions across different files, **When** deduplication runs, **Then** identical entries are merged into a single Q&A pair without repetition, and their `frequencia` values are summed.
2. **Given** Q&A entries with identical questions but slight whitespace/formatting differences, **When** deduplication runs, **Then** normalized matching (case-insensitive, whitespace-stripped) identifies them as duplicates and retains the longest/most complete answer string, summing their frequency counts.
3. **Given** an active OpenAI API key is configured, **When** consolidation runs, **Then** the pre-grouped Q&A batch is submitted to the ChatGPT API using the `TipoFerramenta.CONSOLIDADOR` prompt to perform final AI-driven deduplication, refinement, and formatting before output generation.

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

- **Incomplete Q&A pairs** (e.g., a question without a corresponding answer): The incomplete pair is skipped during parsing and a warning is added to the processing log identifying the file name and the orphaned question text. Processing continues for all remaining valid pairs in the batch.
- **Very large batches (>50 files or extremely large individual files)**: SC-003's <1 min SLA applies to standard input file batches (up to 50 standard-sized files). For large documents (300+ Q&A pairs), the chunked batch processing strategy (FR-013/SC-005) ensures reliable execution without timeouts or LLM context overflow.
- **Format mismatch** (e.g., a plain-text file submitted as JSON): Treated as a malformed file per FR-010 — the parser raises a parse error, the file is skipped with a descriptive warning in the log, and processing continues for the remaining files.

## Clarifications

### Session 2026-07-24
- Q: What exact format/structure should be used for JSON and TXT parsing and generation? → A: Use the project's existing tool format: JSON uses `qna_pairs` array with `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, and `category`. TXT uses `[<metadata>] (Frequência: <n>)` blocks followed by `Q: ...` and `A: ...` lines with `----------------------------------------` delimiters.
- Q: How should duplicates and frequencies be merged when matching questions are found? → A: Merge matching questions by summing their `frequencia` values and retaining the most detailed (longest/most complete) answer string.
- Q: How should the tool be integrated into the user interface? → A: Integrate as the 3rd tool option within the existing application's multi-tool Navigation / Config panel alongside the existing tools.
- Q: How should malformed files in a batch be handled during processing? → A: Skip the malformed file with a warning notification to the user, and continue processing all remaining valid files in the batch.

### Session 2026-07-28
- Q: Como o ChatGPT (OpenAI API) deve ser integrado no fluxo da Ferramenta de Juntar? → A: Usar pré-agrupamento algorítmico local em Python e enviar o lote para o ChatGPT via Prompt Padrão configurado (`TipoFerramenta.CONSOLIDADOR`) para deduplicar, refinar e formatar as respostas e perguntas finais.

### Session 2026-07-29
- Q: Qual é o separador exato entre cada bloco Q&A no arquivo `.txt` de saída? → A: Cada bloco é separado por uma linha de 40 traços (`----------------------------------------`) após o par `A: ...`, conforme exemplo: `[Categoria] (Frequência: 1)\nQ: pergunta?\nA: resposta.\n----------------------------------------`.
- Q: Como deve ser exibido o progresso do processamento na interface? → A: Assim como nas demais ferramentas do projeto, deve ser exibido um log detalhado em tempo real mostrando a etapa atual do processamento (ex: "Parseando arquivo X", "Mesclando pares duplicados", "Exportando saída").
- Q: Como o sistema de junção deve escalar para documentos principais com muitos pares Q&A sem travar a LLM? → A: O sistema deve dividir o documento principal em chunks e as novas perguntas em lotes. Cada lote é avaliado sequencialmente contra cada chunk do documento principal; pares duplicados são mesclados inline. Ao final, os pares restantes do lote (novos) são adicionados ao final do documento principal. O próximo lote de perguntas repete o processo no documento principal já atualizado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a new dedicated 3rd tool interface within the existing application navigation structure, following the exact UI pattern of existing tools.
- **FR-002**: The system MUST allow the user to specify the input file format (JSON or TXT) when supplying input files.
- **FR-003**: The system MUST accept multiple input files in a single batch operation.
- **FR-004**: The system MUST parse JSON files matching the project format with a `qna_pairs` array containing `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, and `category`.
- **FR-005**: The system MUST parse TXT files structured with `[<metadata>] (Frequência: <n>)`, `Q: <question>`, and `A: <answer>` sections delimited by `----------------------------------------`.
- **FR-006**: The system MUST perform algorithmic pre-grouping of questions and submit the batch to the ChatGPT API using a default configurable prompt (`TipoFerramenta.CONSOLIDADOR`) to deduplicate, refine, sum frequencies, and format consolidated Q&A pairs into final outputs.
- **FR-007**: The system MUST automatically generate two output files for every completed consolidation run: one `.txt` file and one `.json` file.
- **FR-008**: The JSON output MUST follow the `qna_pairs` schema structure (`perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, `category`).
- **FR-009**: The TXT output MUST format each Q&A block using `[<metadata>] (Frequência: <n>)\nQ: <question>\nA: <answer>\n----------------------------------------`, where the 40-dash separator line appears after every `A:` line, including the last block in the file.
- **FR-010**: The system MUST gracefully handle malformed or unparseable files by logging a warning, skipping the invalid file, and processing all remaining valid files in the batch.
- **FR-011**: The system MUST provide a local-only deduplication fallback when no OpenAI API key is configured — algorithmic pre-grouping and frequency summation MUST complete successfully without any external API call, and the user MUST be notified that AI consolidation was skipped.
- **FR-012**: The system MUST emit a detailed real-time processing log to the UI during each processing stage, following the same log pattern as the other tools in the application. Logged events MUST include at minimum: file parsing start/end per file, deduplication start/end, chunk processing progress (current chunk / total chunks), export start/end, and any warnings or skipped-file notifications.
- **FR-013**: The system MUST implement chunked batch processing for large document sets: the main (accumulated) document is split into fixed-size chunks of Q&A pairs; new incoming questions are split into batches. Each batch is evaluated sequentially against every chunk; duplicate matches are merged inline into the chunk. At the end of all chunk evaluations, any remaining (unmatched) pairs from the batch are appended to the main document. The updated main document is then used as the reference for the next batch. This strategy prevents LLM context overflow and ensures the process does not hang on large inputs.
- **FR-014**: The minimum chunk size for FR-013 MUST be configurable (default: 30 Q&A pairs per chunk). Batches of incoming questions MUST also be configurable (default: 30 pairs per batch). These defaults are chosen to stay within safe LLM context limits.

### Key Entities *(include if feature involves data)*

- **QA Pair**: Represents a single question-and-answer pair (`perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, `category`).
- **Consolidation Job**: Represents a single execution run with input format selection, list of input files, status, and generated output paths.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of identical duplicate Q&A pairs across input documents are merged, resulting in zero exact duplicate entries in the final outputs while combining their frequency counts.
- **SC-002**: Every consolidation run successfully creates both valid `.json` and readable `.txt` export files conforming strictly to the project schema. Each block in the `.txt` file ends with a `----------------------------------------` separator line.
- **SC-003**: Users can complete input selection, format choice, and consolidation in under 1 minute for standard file batches (up to 50 files). This target applies to the local algorithmic processing phase only; total wall-clock time when using the ChatGPT API depends on external API latency and is best-effort.
- **SC-004**: Processing log events are emitted to the UI within 500 ms of each stage transition, giving the user continuous visual feedback throughout the entire consolidation pipeline.
- **SC-005**: The chunked processing strategy (FR-013) MUST successfully handle a main document with 300+ Q&A pairs without hanging, timeout, or LLM context overflow. Each chunk evaluation MUST complete independently and deterministically.

## Assumptions

- The tool is standalone and does not overwrite existing app features.
- TXT input files use the standard project format (`[Metadata] (Frequência: X)\nQ: ...\nA: ...`).
- Duplicate detection matches questions using case-insensitive and whitespace-normalized string comparisons (with standard whitespace stripping and lowercasing).
- Algorithmic pre-grouping uses the normalized `perguntaPadronizada` field as the grouping key before submitting the batch to the ChatGPT API.
- SC-003's 1-minute SLA covers only the local processing pipeline (parsing + algorithmic merge + file export). API-bound consolidation time is excluded.
- The chunked processing strategy (FR-013/FR-014) applies to both local algorithmic deduplication and AI-assisted consolidation phases.
- Chunk size defaults (30 pairs/chunk, 30 pairs/batch) may be tuned by the operator at deployment time without requiring a code change (e.g., via environment variable or config file).
