# Implementation Plan: Extrator e Filtro de P&R (Local)

**Branch**: `001-extrator-filtro-pr-local` | **Date**: 2026-07-06 | **Spec**: [spec.md](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/001-extrator-filtro-pr-local/spec.md)

## Summary
The goal of this feature is to implement a local, single-user desktop utility packaged in a single Docker container. The application consists of a FastAPI backend and a React (Vite) frontend. It allows users to upload local text files, intelligently chunks them, processes them sequentially using the OpenAI API, semantically groups the extracted questions and answers, and allows exporting results in both human-readable text (.txt) and structured JSON formats. Custom prompts, selected language, and API keys are stored in a persistent Docker volume.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5+, Node.js 18+ (Frontend)  
**Primary Dependencies**: FastAPI, uvicorn, openai (python SDK), tiktoken, pydantic, pytest (Backend) / React, Tailwind CSS, shadcn/ui, lucide-react, vitest (Frontend)  
**Storage**: JSON-based local files persisted in a Docker volume for configuration (`ChaveAPI`, `PromptConfig`); in-memory state for runtime data (`ArquivoProcessamento`, `ResultadoParPR`, `ItemLog`)  
**Testing**: `pytest` for backend unit/integration tests; `vitest` for frontend components  
**Target Platform**: Linux/MacOS/Windows via Docker (Single Container, exposing a single local port)  
**Project Type**: web-service & web-app (single container)  
**Performance Goals**: Frontend render time < 200ms for up to 500 P&R pairs; chunk size processing <= 10,000 characters  
**Constraints**: Estritamente local (localhost), offline-capable (except for OpenAI API requests), no authentication/login, Docker volume mount for persistent configs  
**Scale/Scope**: Single user, documents up to 1,000,000 characters, automatic rate-limit retries (exponential backoff)  

**Design Decisions Needing Detail (Phase 0 Research)**:
- **Frontend Serving**: NEEDS CLARIFICATION (How FastAPI serves Vite-compiled static assets and routes them under a single Docker container)
- **Text Chunking Strategy**: NEEDS CLARIFICATION (Algorithm for smart text slicing by paragraphs/lines while keeping under OpenAI token limits via `tiktoken`)
- **Factory Pattern**: NEEDS CLARIFICATION (How to structure factories for file parsers in the backend and API clients in the frontend)
- **Semantic Deduplication**: NEEDS CLARIFICATION (Prompt engineering and aggregation logic for merging semantically similar Q&As)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Restriction | Spec Alignment Status | Justification / Notes |
| :--- | :--- | :--- |
| **I. Local-First e Usuário Único** | PASS | Entirely local, single container Docker, FastAPI + React Vite, no auth/login. |
| **II. Processamento Transparente** | PASS | Spec details clear file list, real-time log area (`ItemLog`), and clear Q&A listing. |
| **III. Estética Premium e Micro-animações** | PASS | Tailwind + shadcn/ui, Outfit/Inter fonts, micro-animations, dark/sleek theme. |
| **IV. Formatos de Exportação Duplos** | PASS | TXT (human readable) and JSON (fields: `question`, `answer`, `metadata`, `category`). |
| **V. Mecanismo de Extração Modular** | PASS | Modular structure mandated. Factory Pattern required for backend parsers and frontend APIs. Unit tests via pytest. |
| **Dockerização (Single Container)** | PASS | FastAPI serves Vite build, running under a single port. |

## Project Structure

The project will use the web application multi-directory layout, packaged together via Docker:

```text
/mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/
├── backend/
│   ├── src/
│   │   ├── api/             # FastAPI routes and middleware
│   │   ├── core/            # Config, security, and main prompt utilities
│   │   ├── models/          # Pydantic schemas (ChaveAPI, PromptConfig, etc.)
│   │   ├── services/        # Extraction queue, file chunks, and openai integration
│   │   └── main.py          # App entrypoint (initializes routes and static mounts)
│   ├── tests/               # Pytest suites
│   ├── requirements.txt
│   └── Dockerfile           # Backend + production final image
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components (modal, settings, log viewer, etc.)
│   │   ├── services/        # API client factories and connections
│   │   ├── App.tsx          # Main layout and state coordination
│   │   └── main.tsx
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml       # Dev/Local deployment orchestration
└── README.md
```

**Structure Decision**: The web application multi-directory layout is chosen. Frontend and backend are separated under `frontend/` and `backend/` for clean development, testing, and dependency management. In production, they are built together: Node.js builds the static assets in `frontend/dist`, which are then copied into the backend Docker image and served by FastAPI's static filesystem utility.

## Complexity Tracking

*No violations of the Constitution identified. Complexity is kept minimal and aligned with requirements.*
