# Implementation Plan: Exportar Conteúdo Não Classificado para Base de Dados

**Branch**: `002-txt-output-uncategorized` | **Date**: 2026-07-15 | **Spec**: [spec.md](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/002-txt-output-uncategorized/spec.md)
**Input**: Feature specification from `/specs/002-txt-output-uncategorized/spec.md`

## Summary

The objective is to update the application to support the extraction of non-classified content from WhatsApp chat logs (facts, rules, prices, business info) which are not structured as Questions & Answers (Q&A). This content will be extracted alongside Q&A pairs using OpenAI models, accumulated, deduplicated using exact case-insensitive match, and displayed in the frontend via a dedicated panel/tab. Finally, the user will be able to download a third exported file: a clean `.txt` document with one uncategorized statement per line.

Crucially, this uncategorized content will **not** be included in the standard Q&A JSON export file. It will only be exported via the new `.txt` download button.

The backend prompt system and WebSocket message schemas will be updated. The frontend will be modified to support visual tab switching between the Q&A table and the new Uncategorized Content list, and a new export button will be added.

## Technical Context

**Language/Version**: Python 3.11/3.12, TypeScript 5.2.2, Node 20  
**Primary Dependencies**: FastAPI (0.111.0), React (18.3.1), Tailwind CSS, Lucide React, OpenAI (1.30.1), Pydantic (2.7.1)  
**Storage**: In-memory during execution / Q&A exported to JSON and TXT / Uncategorized content exported to TXT only.  
**Testing**: pytest (8.2.0), pytest-asyncio, httpx (backend); vitest (frontend)  
**Target Platform**: Single-container Docker / Linux local execution  
**Project Type**: web-service / web application  
**Performance Goals**: Extractions completed without introducing delays > 15% to processing times. Export of additional TXT file completed in < 100ms.  
**Constraints**: Local execution, offline-capable except LLM API calls.  
**Scale/Scope**: Single user, local tool.  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Status | Notes |
|---|---|---|
| **I. Local-First e Usuário Único** | PASS | All backend processing remains local; no cloud database/auth dependencies are added. |
| **II. Processamento Transparente** | PASS | The uncategorized content will be logged and returned dynamically in real-time events. |
| **III. Estética Premium** | PASS | The new UI panel/tab will use shadcn/ui components, Outfit/Inter typography, and smooth transitions. |
| **IV. Formatos de Exportação** | PASS | The standard formats (Q&A TXT and JSON) are preserved. A third `.txt` file is added as a supplemental feature per customer request. |
| **V. Mecanismo Modular** | PASS | The extraction logic will remain in the backend, exposing it through updated schemas and services. |

## Project Structure

### Documentation (this feature)

```text
specs/002-txt-output-uncategorized/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    └── api.md           # API/WebSocket updates contract
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── websocket.py     # Updates to handle and return uncategorized database content
│   ├── models/
│   │   └── schemas.py       # WSChunkSuccessData, WSQueueCompleteData, WSQueueErrorData updates
│   └── services/
│       ├── openai_client.py # Prompt updates to extract uncategorized content
│       ├── consolidator.py  # Local deduplication of uncategorized content
│       └── prompt_storage.py # DEFAULT_SYSTEM_PROMPT_TEXT update and user prompts custom suffix logic
└── tests/
    └── unit/
        ├── test_openai_client.py
        └── test_consolidator.py

frontend/
├── src/
│   ├── components/
│   │   └── ResultsViewer.tsx # New tabs and export button
│   ├── services/
│   │   └── api.ts            # Type definitions update
│   └── types/
│       └── websocket.ts      # WebSocket event interface updates
```

**Structure Decision**: Web application layout containing `backend` and `frontend`.

## Complexity Tracking

*No violations detected.*
