# Implementation Plan: Extração Exata de Perguntas e Respostas do WhatsApp

**Branch**: `006-exact-qa-extractor` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-exact-qa-extractor/spec.md`

## Summary

Implementar a nova ferramenta de extração exata de perguntas e respostas a partir de exportações de conversa do WhatsApp (`.txt`). A solução adota uma abordagem em 3 etapas para garantir fidelidade textual absoluta (100%):
1. **Parser Determinístico**: O backend processa o arquivo `.txt` dividindo o chat em mensagens individuais e indexando cada uma com um ID sequencial único (`MSG-XXXX`).
2. **Mapeamento via IA (LLM)**: O bloco indexado é enviado para a IA, que retorna exclusivamente os pares de identificadores `(question_id -> answer_id)`.
3. **Reconstrução Exata**: O backend recupera o texto bruto original armazenado no parser para cada ID pareado, garantindo zero alteração, alucinação ou paráfrase.

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript / React (Frontend)  
**Primary Dependencies**: FastAPI, Pydantic, Tailwind CSS, React, Lucide React  
**Storage**: N/A (Processamento de arquivos na memória com streaming local)  
**Testing**: pytest (Backend unit/integration)  
**Target Platform**: Navegador Web Local (Docker Single Container / Localhost)  
**Project Type**: Web Application (Backend FastAPI + Frontend React)  
**Performance Goals**: Processamento de conversas com até 10.000 mensagens sem travamentos  
**Constraints**: Zero alteração nos caracteres das perguntas/respostas extraídas  
**Scale/Scope**: Ferramenta isolada integrada ao painel principal do filtro de WhatsApp  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Princípio I (Local-First e Usuário Único)**: SIM - Sem dependência de nuvem, backend e frontend em execução local no container Docker.
- **Princípio II (Processamento Transparente)**: SIM - Logs em tempo real via WebSocket e pré-visualização completa dos pares extraídos.
- **Princípio III (Estética Premium)**: SIM - Interface React/TypeScript com componentes estilizados via Tailwind CSS mantendo o padrão visual das ferramentas existentes.
- **Princípio IV (Formatos de Exportação Duplos)**: SIM - Suporte a exportação em `.txt` formatado e `.json` estruturado.
- **Princípio V (Mecanismo de Extração Modular)**: SIM - Arquitetura modular no FastAPI usando Factory Pattern para parsers e extratores com testes unitários em pytest.

## Project Structure

### Documentation (this feature)

```text
specs/006-exact-qa-extractor/
├── plan.md              # Este arquivo
├── research.md          # Decisões técnicas e racional
├── data-model.md        # Entidades e estruturas de dados
├── quickstart.md        # Guia rápido de execução e testes
└── contracts/           # Especificação do contrato WebSocket
    └── exact-extractor-ws.md
```

### Source Code Layout

```text
backend/
├── src/
│   ├── api/
│   │   └── exact_extractor_ws.py  # WebSocket router do extrator exato
│   ├── models/
│   │   └── exact_qa.py            # Pydantic schemas para mensagens e pares
│   ├── services/
│   │   ├── exact_parser.py        # Parser determinístico de mensagens do WhatsApp
│   │   └── exact_extractor.py     # Serviço de reconstrução e orquestração da LLM
└── tests/
    ├── test_exact_parser.py
    └── test_exact_extractor.py

frontend/
├── src/
│   ├── components/
│   │   └── ExactExtractorPanel.tsx # Interface web do Extrator Exato P&R
│   ├── services/
│   │   └── exactExtractorService.ts# Cliente WebSocket e comunicação
```

**Structure Decision**: Estrutura modular padrão Web Application (Backend Python/FastAPI + Frontend TypeScript/React) seguindo as convenções e padrões estabelecidos na Constituição.

## Complexity Tracking

> **Sem violações registradas da Constituição.** Todos os princípios e restrições foram satisfeitos sem a necessidade de exceções.
