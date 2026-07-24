# Implementation Plan: Consolidated Question & Answer Document Merger

**Branch**: `004-merge-qa-documents` | **Date**: 2026-07-24 | **Spec**: [spec.md](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/004-merge-qa-documents/spec.md)
**Input**: Feature specification from `/specs/004-merge-qa-documents/spec.md`

## Summary

The goal of this feature is to create a 3rd dedicated tool within the web application interface ("Consolidar P&R") to merge Q&A pairs from multiple uploaded documents (JSON or TXT). The system parses documents in the specified format, normalizes and deduplicates Q&A items, sums their frequency (`frequencia`), selects the longest/most complete answer when duplicates occur, and generates both `.txt` and `.json` output files in the standard project schema.

## Technical Context

**Language/Version**: Python 3.10+ (Backend FastAPI), TypeScript / React 18+ (Frontend Vite)  
**Primary Dependencies**: FastAPI, Pydantic, Tailwind CSS, Lucide React, Pytest  
**Storage**: Local temporary filesystem storage for output generation  
**Testing**: pytest (backend unit and endpoint tests)  
**Target Platform**: Docker single container (FastAPI + React static build) / Localhost  
**Project Type**: Full-stack web application (FastAPI backend + React frontend)  
**Performance Goals**: Batch processing of up to 50 files completed in under 1 minute  
**Constraints**: Single Docker container, Local-First, dual export format (.txt & .json), Factory Pattern for parsers/services  
**Scale/Scope**: Multi-document ingestion up to tens of files, deduplication in memory  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Local-First e Usuário Único**: PASS. The consolidation tool runs fully on localhost without cloud or DB dependencies.
- **Principle II: Processamento Transparente de Arquivos**: PASS. Uploaded files will be listed in UI, execution logs stream in real-time, and results/counts are displayed.
- **Principle III: Estética Premium e Micro-animações**: PASS. UI will use React/TypeScript/Tailwind with smooth hover transitions, card components, and status badges consistent with Extractor and Generator tools.
- **Principle IV: Formatos de Exportação Duplos**: PASS. The backend will simultaneously generate `.json` (`qna_pairs` format) and `.txt` (`[Metadata] (Frequência: N)` block format).
- **Principle V: Mecanismo de Extração Modular**: PASS. Merging & parsing logic will use modular services/factories in `backend/src/services/` and `frontend/src/services/`.

## Project Structure

### Documentation (this feature)

```text
specs/004-merge-qa-documents/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── merge_api.json   # OpenAPI contract for merge endpoint
└── tasks.md             # Phase 2 output
```

### Source Code Layout

```text
backend/
├── src/
│   ├── api/
│   │   └── endpoints/
│   │       └── merger.py         # FastApi router for file merge operation
│   ├── models/
│   │   └── merger.py          # Data models for Q&A pair and merge request/response
│   └── services/
│       ├── qna_parser_factory.py # Factory for JSON and TXT Q&A parsers
│       ├── json_qna_parser.py    # JSON QnA Parser implementation
│       ├── txt_qna_parser.py     # TXT QnA Parser implementation
│       └── qna_merger_service.py # Deduplication, frequency summing & answer selection logic
└── tests/
    ├── unit/
    │   └── test_qna_merger.py   # Unit tests for parser and merger service
    └── integration/
        └── test_merger_api.py   # API endpoint integration tests

frontend/
├── src/
│   ├── components/
│   │   ├── MergerPanel.tsx      # Main panel for tool 3 ("Consolidar P&R")
│   │   └── Navigation.tsx       # Tab switcher updated with tool 3 option
│   └── services/
│       └── mergerService.ts     # Frontend API client for consolidation endpoint
```

**Structure Decision**: Web application layout (backend/ and frontend/) following existing patterns in the codebase.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
