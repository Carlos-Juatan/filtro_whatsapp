# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Refatorar e isolar a gestão de prompts por ferramenta na aplicação para o Extrator de P&R (`extrator`), Gerador de Perguntas (`gerador`) e Consolidador (`consolidador`). Cada ferramenta deve possuir sua própria lista isolada de prompts, mantendo um prompt padrão imutável (`FIXO`) por ferramenta, que pode ser duplicado para personalização com a nomenclatura `<Nome Padrão> (Cópia)` na lista da respectiva ferramenta.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5+ / React 18 (Frontend)  
**Primary Dependencies**: FastAPI, Pydantic v2, React, Tailwind CSS, Lucide React, Radix UI  
**Storage**: JSON file (`prompts.json`) persisted in Docker volume (`DATA_DIR`)  
**Testing**: pytest (Backend), Vitest + React Testing Library (Frontend)  
**Target Platform**: Docker container running on Linux / Localhost  
**Project Type**: Web Application (FastAPI backend + React frontend)  
**Performance Goals**: Instant prompt filtering and duplication (<50ms UI response)  
**Constraints**: Zero prompt cross-contamination between tools, local-first execution  
**Scale/Scope**: 3 tools (`extrator`, `gerador`, `consolidador`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Local-First e Usuário Único**: PASS. Toda a gestão de prompts é mantida localmente em arquivos JSON.
- **II. Processamento Transparente**: PASS. Listagem e filtragem de prompts claras por ferramenta.
- **III. Estética Premium e Micro-animações**: PASS. Componentes com Radix UI, feedback visual e transições suaves.
- **IV. Formatos de Exportação Duplos**: N/A para esta funcionalidade de configuração.
- **V. Mecanismo de Extração Modular & Factory Pattern**: PASS. Endpoints e serviços de armazenamento de prompts utilizam o padrão Factory no backend (`get_prompt_storage_service()`) e no frontend API client.

## Project Structure

### Documentation (this feature)

```text
specs/005-separate-tool-prompts/
├── plan.md              # Implementation plan
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 contract output
    └── prompts-api.md
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── schemas.py              # TipoFerramenta enum & PromptConfig validation
│   ├── services/
│   │   └── prompt_storage.py       # PromptStorageService & system defaults per tool
│   └── api/
│       └── routes/
│           └── prompts.py          # GET, POST, DELETE /api/prompts (with ferramenta filter)
└── tests/
    └── test_prompts.py             # Unit tests for prompt segregation & protection

frontend/
├── src/
│   ├── App.tsx                    # Adição de aba e roteamento do Consolidador no header
│   ├── components/
│   │   ├── ConsolidatorPanel.tsx  # Nova interface dedicada à ferramenta Consolidador
│   │   ├── PromptSettings.tsx     # Tool-scoped prompt list & duplication UI
│   │   └── StartProcessModal.tsx  # Tool-scoped prompt dropdown selection
│   └── services/
│       ├── api.ts                 # ApiClient interface & TipoFerramenta enum
│       └── prompts.ts             # usePrompts hook with tool filtering
└── tests/
    └── prompts.test.tsx           # Component tests for tool-scoped prompts
```

**Structure Decision**: Web application structure with separated `backend/` and `frontend/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

