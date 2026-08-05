# Research & Architecture Decisions: Q&A Document Merger Tool

**Feature Branch**: `004-merge-qa-documents`  
**Date**: 2026-07-28  

## 1. ChatGPT Prompt Integration Strategy for Q&A Consolidation

### Decision
Add `CONSOLIDADOR = "consolidador"` to `TipoFerramenta` enum in `backend/src/models/schemas.py` and register a system-default consolidation prompt in `PromptStorageService`. The merger workflow will perform an algorithmic pre-grouping of similar/exact questions in Python before passing batches through the OpenAI API using the active `CONSOLIDADOR` prompt.

### Rationale
- **Context Window Protection**: Sending hundreds of un-grouped raw Q&A pairs directly to OpenAI risk exceeding token limits. Local pre-grouping clusters questions with matching normalized strings/topics and sums frequency counters before sending to ChatGPT.
- **Consistency**: Reuses the established prompt management system (`PromptStorageService`), allowing users to edit and customize the consolidation system prompt in the prompt configuration panel just like the Extrator and Gerador tools.
- **Data Integrity**: ChatGPT is instructed via prompt JSON-mode formatting to preserve accurate frequency counts, metadata tags, and categories while synthesizing clean, non-repetitive answers.

### Alternatives Considered
- **Pure Algorithmic Deduplication**: Fast and zero-cost, but fails to combine answers that describe the same concept with different wording or syntax. Rejected based on user requirement for ChatGPT refinement.
- **Single Mass LLM Request**: Unpredictable for large file batches due to context window boundaries.

---

## 2. OpenAI API Integration & Fallback Handling

### Decision
The backend service `QnAMergerService` will check for an active OpenAI API key via `key_storage.get_active()`. If an active key is present, it formats the pre-grouped batches and invokes the OpenAI chat completion API (using `gpt-4o-mini` by default or the prompt's configured model) with JSON response formatting (`response_format={"type": "json_object"}`). If no API key is set, it gracefully falls back to local algorithmic string selection (longest answer) and logs a warning in the result payload.

### Rationale
- Guarantees system resilience: users can still consolidate documents even without an active OpenAI API key configured.
- Matches existing patterns in `openai_client.py` and `generator_client.py`.

---

## 3. Schema & Enum Integration (`TipoFerramenta`)

### Decision
Extend `TipoFerramenta` in `backend/src/models/schemas.py` and `frontend/src/services/api.ts`:
- Enum values: `EXTRATOR = "extrator"`, `GERADOR = "gerador"`, `CONSOLIDADOR = "consolidador"`.
- Update `PromptStorageService` migration logic to automatically seed a default prompt for `TipoFerramenta.CONSOLIDADOR`.

### Default Consolidador Prompt Text
```text
Você é um assistente especialista em consolidar e organizar bases de Perguntas e Respostas (P&R).
Sua tarefa é analisar o grupo de P&R fornecido, remover perguntas e respostas duplicadas ou redundantes, combinar as frequências das perguntas idênticas/similares e gerar uma lista limpa, unificada e padronizada.

Instruções:
1. Agrupe perguntas com o mesmo sentido em uma única Pergunta Padronizada clara e direta.
2. Combine as respostas correspondentes em uma única Resposta Consolidada abrangente e sem contradições.
3. some as frequências das perguntas duplicadas.
4. Mantenha os metadados e categorias mais relevantes.
5. Retorne a resposta ESTRITAMENTE em formato JSON com a chave 'qna_pairs' contendo o array de objetos:
   [
     {
       "perguntaPadronizada": "string",
       "respostaConsolidada": "string",
       "frequencia": integer,
       "metadata": "string ou null",
       "category": "string ou null"
     }
   ]
```
