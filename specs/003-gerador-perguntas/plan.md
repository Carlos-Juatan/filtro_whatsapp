# Implementation Plan: Gerador de Perguntas a partir de Conteúdo Não Classificado

**Branch**: `003-gerador-perguntas` | **Date**: 2026-07-15 | **Spec**: [spec.md](file:///mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp/specs/003-gerador-perguntas/spec.md)
**Input**: Feature specification from `/specs/003-gerador-perguntas/spec.md`

## Summary

The goal is to create a new, separate tool in the system called "Gerador de Perguntas" which allows uploading unstructured text files (`.txt`), segments them using the existing token-based chunking logic, and utilizes the OpenAI API to generate relevant Q&A pairs (where the question is created by the AI and the answer is the original factual statement). The results are consolidated semantically, displayed in a tabular interface, and are exportable to TXT and JSON matching the existing tool's output schema. Additionally, the prompt system will be refactored to separate prompts per tool, and a new WebSocket endpoint `/api/generate` will be created to handle the generator's processing queue independently.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript / React 18+ (Frontend)  
**Primary Dependencies**: FastAPI, Pydantic, tiktoken, openai, Tailwind CSS, Lucide React, shadcn/ui  
**Storage**: Local files (`prompts.json` in docker volume `data/`)  
**Testing**: pytest (unit and integration tests)  
**Target Platform**: Linux (Docker single container running local-first)  
**Project Type**: Web application  
**Performance Goals**: Tab switching < 150ms, processing up to 500,000 characters without memory leaks or UI freezes  
**Constraints**: Fully offline-capable except for OpenAI completions, running inside a single container  
**Scale/Scope**: <10 files per batch, 500k characters max  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Constraint | Status | Ref / Line | Justification / Notes |
|:---|:---|:---|:---|
| **I. Local-First e Usuário Único** | Pass | Principle I | System continues to run entirely locally in localhost. |
| **II. Processamento Transparente** | Pass | Principle II | Live logs, uploaded files list, and results tables are displayed to the user. |
| **III. Estética Premium e Micro-animações** | Pass | Principle III | Using modern design with tabs, consistent color scheme, and clean transitions. |
| **IV. Formatos de Exportação Duplos** | Pass | Principle IV | TXT and JSON exports are generated using the exact same structure as before. |
| **V. Mecanismo de Extração Modular** | Pass | Principle V | Code remains decoupled. Separate websocket handler and clean prompt storage patterns. |
| **Dockerização (Single Container)** | Pass | Restrição 1 | The single container structure remains unchanged. |

*Gate Status*: **PASS**. No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/003-gerador-perguntas/
├── spec.md              # Clarified Feature Specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
    └── websocket.md     # WebSocket API contract for /api/generate
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── websocket.py           # Extrator WebSocket route
│   │   └── websocket_generator.py # [NEW] Gerador WebSocket route
│   ├── models/
│   │   └── schemas.py             # Schemas (PromptConfig extended with 'ferramenta')
│   ├── services/
│   │   ├── prompt_storage.py      # Storage (extended with tool-specific prompts & default generator prompt)
│   │   └── generator_client.py    # [NEW] OpenAI client logic for question generation
│   └── main.py                    # App router (registered new websocket route)
└── tests/
    ├── conftest.py
    ├── test_generator_client.py   # [NEW] Tests for question generation
    └── test_websocket_generator.py# [NEW] Integration tests for the new WS endpoint

frontend/
├── src/
│   ├── components/
│   │   ├── ExtractorPanel.tsx     # [NEW] Existing view refactored into a panel
│   │   └── GeneratorPanel.tsx     # [NEW] New view panel for question generator
│   └── App.tsx                    # Main App with Top Navigation / Tabs
```

**Structure Decision**: Web application layout. The backend code will be augmented with `websocket_generator.py` and `generator_client.py`. The frontend will be reorganized into two independent view panels (`ExtractorPanel` and `GeneratorPanel`) switched via a tab layout in `App.tsx`.

## Complexity Tracking

*No violations to track.*
