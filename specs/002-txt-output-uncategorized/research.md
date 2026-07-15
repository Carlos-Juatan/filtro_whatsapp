# Research: Exportar Conteúdo Não Classificado para Base de Dados

## Technical Decisions & Rationale

### 1. LLM System Prompt & Return Structure

**Decision:**
- Modify the default system prompt (`DEFAULT_SYSTEM_PROMPT_TEXT` in `prompt_storage.py`) to request the model to identify and extract any useful facts, business rules, price points, and schedules not structured as Q&A.
- Require these items to be returned as a list of strings under the JSON key `uncategorized_database_content`.
- The new JSON format returned by the LLM from `extract_qna_from_chunk` will be:
  ```json
  {
    "qna_pairs": [
      {
        "question": "...",
        "answer": "...",
        "frequency": 1,
        "metadata": "...",
        "category": "..."
      }
    ],
    "uncategorized_database_content": [
      "..."
    ]
  }
  ```

**Custom User Prompts Suffix:**
For custom prompts (where `tipo == TipoPrompt.CUSTOMIZADO`), we will append the following instruction suffix programmatically:
```text
\n\nIMPORTANTE: Além das perguntas e respostas, você deve obrigatoriamente identificar e extrair fatos úteis, regras de negócio ou informações relevantes presentes na conversa que não estejam estruturadas como pergunta e resposta, mas que sirvam para enriquecer uma base de conhecimento. Retorne-os como uma lista de strings sob a chave JSON 'uncategorized_database_content' no mesmo objeto de retorno.
```

**Rationale:**
Ensures that regardless of whether the user uses a system prompt or custom prompt, the model is consistently instructed to extract the uncategorized content. The structured JSON response format keeps API calls robust.

---

### 2. Deduplication of Uncategorized Content

**Decision:**
- Develop a utility function to deduplicate the accumulated uncategorized list.
- The deduplication will utilize case-insensitive comparison and ignore leading/trailing whitespaces.
- For each unique normalized text, the original casing (retaining casing of the first encountered occurrence) will be preserved in the output list.

**Implementation detail:**
```python
def deduplicate_uncategorized(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        stripped = item.strip()
        normalized = stripped.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(stripped)
    return result
```

**Rationale:**
This fulfills requirement **FR-004** perfectly and matches the clarification response ("Correspondência exata de texto (case-insensitive, ignorando espaços em branco nas extremidades)").

---

### 3. API & WebSocket Protocol Extension

**Decision:**
- Update `schemas.py` to add `uncategorized_database_content: list[str] = Field(default_factory=list)` to `WSChunkSuccessData`, `WSQueueCompleteData`, and `WSQueueErrorData`.
- In `websocket.py`, accumulate `uncategorized_database_content` per chunk, perform final deduplication, and return the accumulated list on success/failure over WebSockets. Uncategorized content will not be included in the final exported JSON file.

**Rationale:**
Maintains structured socket communication and fulfills requirement **FR-002** and **FR-005**.

---

### 4. Frontend UI and Exporting

**Decision:**
- In `ResultsViewer.tsx`, introduce a tab layout (using Radix UI tabs or simple Tailwind styled buttons) to switch between "Perguntas & Respostas" and "Base de Dados / Conteúdo Adicional".
- Display the uncategorized list as a list of facts/statements.
- Add a button "Baixar Conteúdo Adicional (TXT)" next to existing download buttons.
- On click, generate a client-side TXT file where each statement is printed on a new line (joined by `\n`), matching requirement **FR-006** and User Story 2.
- The downloaded file name will be `nao_classificados.txt`.

**Rationale:**
Client-side file generation is extremely fast (under 10ms, well below the 100ms threshold in SC-002) and avoids extra backend roundtrips.

---

## Alternatives Considered

- **Semantic consolidation for uncategorized content using LLM:** Rejected because the client specified exact text-based deduplication, which is deterministic, fast, and does not consume extra LLM tokens.
- **Backend-based file download endpoint:** Rejected because we already have the complete processed data in the frontend over WebSockets, making client-side file blob creation much simpler and faster.
