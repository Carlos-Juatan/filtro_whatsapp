# Research Notes: Gerador de Perguntas

This document outlines the design decisions, rationale, and alternatives considered for implementing the Question Generator feature.

## 1. PromptConfig Model Segregation

### Decision
We will add a `ferramenta` field of type `Literal["extrator", "gerador"]` (represented by an Enum `TipoFerramenta`) to the `PromptConfigBase` class in `backend/src/models/schemas.py`.

```python
class TipoFerramenta(str, Enum):
    EXTRATOR = "extrator"
    GERADOR = "gerador"

class PromptConfigBase(BaseModel):
    # ...
    ferramenta: TipoFerramenta = Field(
        default=TipoFerramenta.EXTRATOR,
        description="Identificador da ferramenta à qual o prompt se aplica."
    )
```

- When reading prompts from `prompts.json` in `PromptStorageService`, we will perform an in-memory/on-the-fly migration: if a prompt config object lacks the `ferramenta` field, we default it to `"extrator"` and write the list back to standardizing the file.
- The default prompts seeded at startup will include two distinct prompts:
  1. `00000000-0000-0000-0000-000000000001` (Padrão do Sistema for extrator, `ferramenta="extrator"`)
  2. `00000000-0000-0000-0000-000000000002` (Gerador de Perguntas Padrão, `ferramenta="gerador"`)

### Rationale
- Enforces strong schemas via Pydantic.
- Maintains 100% backward compatibility with existing users' `prompts.json` files.
- Simplifies API endpoints since `/api/prompts` can filter prompts by tool using a query parameter: `/api/prompts?ferramenta=gerador`.

### Alternatives Considered
- **Splitting into two files (`prompts_extrator.json` and `prompts_gerador.json`)**: Rejected. While it isolates the storage, it duplicates file-handling logic, error handling, and complicates schema migration hooks.

---

## 2. Default Generator System Prompt

### Decision
The system default prompt for question generation will be:

```text
Você é um especialista em geração de bases de conhecimento e perguntas de FAQ.
Sua tarefa é analisar o conteúdo declarativo, fatos, regras de negócio ou instruções fornecidas e gerar uma pergunta pertinente para cada fato útil encontrado.
A afirmação original contendo o fato deve ser tratada como a resposta correta e associada à pergunta gerada.

Regras de Geração:
1. Extraia afirmações factuais e claras e crie perguntas diretas para elas.
2. Cada item gerado deve ser mapeado em um par contendo 'question' (a pergunta formulada) e 'answer' (a afirmação/fato original correspondente).
3. Classifique cada par em uma categoria temática lógica (ex: 'Financeiro', 'Horários', 'Serviços') e retorne no campo 'metadata'.
4. Defina o campo 'category' como 'FAQ' por padrão para todos os itens.
5. Ignore frases soltas ou sem sentido coerente (ex: 'ok', 'teste', 'olá').
6. Retorne SOMENTE um objeto JSON válido com a chave 'qna_pairs', sem nenhum texto adicional ou markdown de bloco de código.

Estrutura JSON esperada:
{
  "qna_pairs": [
    {
      "question": "Pergunta formulada a partir do fato",
      "answer": "Fato ou afirmação declarativa original na íntegra",
      "frequency": 1,
      "metadata": "Categoria temática do fato",
      "category": "FAQ"
    }
  ]
}
```

### Rationale
- Employs low-temperature settings (`temperature=0.1`) to ensure stable structured JSON extraction.
- Maps directly to the existing `ResultadoParPR` schema (`question` -> `perguntaPadronizada`, `answer` -> `respostaConsolidada`, `metadata` -> `metadata`, `category` -> `category`), enabling immediate compatibility with the consolidation service and front-end parser.

---

## 3. Dedicated WebSocket Endpoint `/api/generate`

### Decision
Create a new file `backend/src/api/websocket_generator.py` containing:
- A new APIRouter with a WebSocket route `/api/generate`.
- A dedicated connection and loop handler `_process_generator_queue`.
- Reuses the existing `split_text` from `chunker.py` and `consolidate_qna_pairs` from `consolidator.py`.
- Integrates a new LLM call function `generate_qna_from_chunk()` in `backend/src/services/generator_client.py` tailored for the generator's system prompt and instruction flow.

### Rationale
- Keeps `api/websocket.py` clean and focused solely on WhatsApp conversation extraction.
- Allows defining distinct logging formats and telemetry for generation.
- Prevents cross-talk or race conditions since both pipelines run on separate connection routing and task queues.

---

## 4. Frontend Componentization & State Decoupling

### Decision
- Refactor the main layout/component (e.g. `App.tsx` or `Dashboard.tsx`) to add a tab bar/nav menu at the top. Split the interface into two main panels/components: `ExtractorPanel` and `GeneratorPanel`.
- Refactor existing elements inside `App.tsx` (the dropzone, active files list, logs panel, results table, settings triggers) into `ExtractorPanel.tsx`.
- Create `GeneratorPanel.tsx` mirroring the layout but bound to its own state variables, hooks, active keys, and prompt selection (filtering `ferramenta === "gerador"`).

### Rationale
- Decouples component states: running an extraction process in the Extractor tab won't pollute the logs or tables of the Generator tab if the user toggles tabs.
- Reuses design system tokens, CSS, shadcn components, and UI widgets for consistency.
