# Implementation Plan: Consolidated Question & Answer Document Merger

**Branch**: `004-merge-qa-documents` | **Date**: 2026-07-28 | **Spec**: [`specs/004-merge-qa-documents/spec.md`](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/004-merge-qa-documents/spec.md)  
**Input**: Feature specification from `/specs/004-merge-qa-documents/spec.md`

## Summary

The Q&A Document Merger feature ("Ferramenta de Juntar") enables users to upload multiple JSON or TXT documents, parse Q&A pairs using modular factory parsers, perform algorithmic pre-grouping, send batch entries to ChatGPT (OpenAI API) using a standard configurable consolidation prompt (`TipoFerramenta.CONSOLIDADOR`), and concurrently export deduplicated JSON and TXT files for user download.

## Technical Context

**Language/Version**: Python 3.12 (Backend), TypeScript / React 18 (Frontend)  
**Primary Dependencies**: FastAPI, Pydantic, Vite, Tailwind CSS, Lucide React, OpenAI API  
**Storage**: Local filesystem (`data/outputs/` for exports, `prompts.json` for prompt storage)  
**Testing**: pytest (backend unit/integration tests)  
**Target Platform**: Linux single-container Docker / Localhost  
**Project Type**: Web Application (FastAPI backend + React SPA frontend)  
**Performance Goals**: Process up to 50 files in < 1 minute  
**Constraints**: Offline fallback for deduplication when OpenAI API key is missing  
**Scale/Scope**: Single-user local utility tool  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Local-First e Usuário Único**: PASS. Runs on localhost:8100 single container. No external database or cloud auth.
- **II. Processamento Transparente de Arquivos**: PASS. UI displays total uploaded files, progress, extracted vs merged counts, warnings log, and download links.
- **III. Estética Premium e Micro-animações**: PASS. Responsive UI with glassmorphism, micro-animations, loading states, and dark mode compatibility.
- **IV. Formatos de Exportação Duplos**: PASS. Outputs both structured `.json` and formatted `.txt` concurrently for every consolidation run.
- **V. Mecanismo de Extração Modular**: PASS. Uses `QnAParserFactory` for file parsing, decoupled `QnAMergerService` for consolidation logic, and `QnAExporter` for formatting.

## Project Structure

### Documentation (this feature)

```text
specs/004-merge-qa-documents/
├── plan.md              # This file
├── research.md          # Architecture decisions for OpenAI integration & prompt management
├── data-model.md        # QnAPair, MergeJobResult, TipoFerramenta schemas
├── quickstart.md        # Test suite and dev server execution commands
├── contracts/           # API contract OpenAPI schema (merge_api.json)
└── tasks.md             # Implementation task breakdown
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── endpoints/
│   │   │   └── merger.py         # FastAPI router for consolidation & download endpoints
│   │   └── routes/
│   │       ├── keys.py
│   │       └── prompts.py
│   ├── models/
│   │   ├── merger.py             # QnAPair, InputFormat, MergeJobResult models
│   │   └── schemas.py            # TipoFerramenta enum with CONSOLIDADOR
│   └── services/
│       ├── qna_parser_factory.py # Factory pattern for format parsers
│       ├── json_qna_parser.py    # JSON parser implementation
│       ├── txt_qna_parser.py     # TXT parser implementation
│       ├── qna_merger_service.py # Pre-grouping & ChatGPT consolidation service
│       ├── qna_exporter.py       # Dual output generator (JSON and TXT)
│       └── prompt_storage.py     # Storage & default prompts for CONSOLIDADOR
└── tests/
    ├── integration/
    │   └── test_merger_api.py   # API integration tests
    └── unit/
        ├── test_qna_parser.py   # Parser unit tests
        └── test_qna_merger_service.py # Merger service unit tests

frontend/
├── src/
│   ├── components/
│   │   └── MergerPanel.tsx      # Main UI component for document merger
│   └── services/
│       ├── api.ts               # API client interfaces & TipoFerramenta type
│       ├── mergerService.ts     # Frontend HTTP client for consolidation API
│       └── prompts.ts           # Prompt management client
```

**Structure Decision**: Web application layout separating FastAPI backend (`backend/src`) and React TypeScript frontend (`frontend/src`).

## Complexity Tracking

> No violations found in Constitution Check.
