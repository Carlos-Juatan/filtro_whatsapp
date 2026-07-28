# Data Model Specification: Consolidated Question & Answer Document Merger

**Feature Branch**: `004-merge-qa-documents`  

## Entities & Enums

### 1. `InputFormat` (Enum)
Defines supported input file formats for batch parsing.
- Values:
  - `json`: Structured JSON file with `qna_pairs` array.
  - `txt`: Standard text file formatted with `[Metadata] (Frequência: n)` headers, `Q:` and `A:` blocks.

### 2. `TipoFerramenta` (Enum Extension)
Segregates prompt templates by tool type in `PromptStorageService` and `schemas.py`.
- Values:
  - `extrator`: Prompts for text chunk extraction tool.
  - `gerador`: Prompts for Q&A pair generator tool.
  - `consolidador`: Prompts for Q&A document merger tool.

### 3. `QnAPair` (Model)
Represents a single Question & Answer pair extracted or consolidated across files.
- Fields:
  - `perguntaPadronizada` (string, required): Standardized question text.
  - `respostaConsolidada` (string, required): Consolidated answer text.
  - `frequencia` (integer, required, default=1): Number of occurrences/occurrences count across source files.
  - `metadata` (string | null, optional): Comma-separated metadata tags (e.g. source file names or topics).
  - `category` (string | null, optional): Category classification tag.

### 4. `MergeJobResult` (Model)
Response structure returned by `POST /api/merger/consolidate`.
- Fields:
  - `success` (boolean): `true` if at least one file was parsed and consolidated.
  - `total_files_processed` (integer): Count of input files successfully read.
  - `total_qna_extracted` (integer): Total Q&A pairs extracted before deduplication.
  - `total_qna_merged` (integer): Count of unique Q&A pairs after pre-grouping & ChatGPT consolidation.
  - `json_output_filename` (string | null): File basename of the generated JSON output file in server output directory.
  - `txt_output_filename` (string | null): File basename of the generated TXT output file in server output directory.
  - `warnings` (List[string]): List of non-fatal warnings (e.g. skipped unparseable files, fallback to local merge when API key is missing).
  - `qna_pairs` (List[QnAPair]): Array of the final consolidated Q&A pair objects.
