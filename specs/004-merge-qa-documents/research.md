# Research: Consolidated Question & Answer Document Merger

## 1. Matching & Deduplication Algorithm

### Decision
Use question text normalization: convert to lowercase, strip outer whitespace, remove trailing punctuation (e.g. `?`), and collapse internal whitespace sequences into a single space. Group pairs by normalized question key.

### Rationale
- High precision for detecting duplicates across files.
- Preserves original case and formatting of the question from the first encountered instance while normalizing keys internally for matching.

### Alternatives Considered
- **Fuzzy matching (Levenshtein distance)**: Rejected for initial implementation as exact normalized matching is predictable, fast, and meets specification requirements without introducing false positive merges.

## 2. Duplicate Answer Selection Policy

### Decision
When matching questions are discovered across files:
1. Sum the `frequencia` integer values of all matching entries.
2. Compare answer texts after stripping whitespace; select the longest (most detailed) answer string.
3. Preserve existing metadata/category or merge unique metadata tags.

### Rationale
- User spec explicitly requires summing frequencies and retaining the most detailed/complete answer.
- Length comparison (`len(strip(answer))`) is a robust heuristic for detail completeness.

## 3. Formatting & Parsing Standards

### Decision
- **JSON Input/Output Schema**:
  ```json
  {
    "qna_pairs": [
      {
        "perguntaPadronizada": "...",
        "respostaConsolidada": "...",
        "frequencia": 1,
        "metadata": "...",
        "category": "..."
      }
    ]
  }
  ```
- **TXT Input/Output Schema**:
  ```text
  [<metadata>] (Frequência: <frequencia>)
  Q: <perguntaPadronizada>
  A: <respostaConsolidada>
  ----------------------------------------
  ```

### Rationale
Matches exact project conventions established in previous spec phases (Extractor and Generator).

## 4. Error Handling Strategy

### Decision
If a file fails parsing during a batch job, log a warning with the filename and error reason, skip that specific file, and continue merging the remaining valid files. Return detailed warnings in the API response.

### Rationale
Conforms to clarification requirement for resilience during multi-file operations.
