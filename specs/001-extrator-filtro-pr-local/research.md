# Research Notes: Extrator e Filtro de P&R (Local)

This document resolves the design decisions marked as `NEEDS CLARIFICATION` in the Implementation Plan.

---

## 1. Frontend Serving (Single Container Deployment)

### Decision
The frontend built by Vite (React + TS + Tailwind CSS) will compile static files to the `frontend/dist` directory. The FastAPI backend will serve this directory using `fastapi.staticfiles.StaticFiles`.
Additionally, we will mount a catch-all route at the backend to serve `dist/index.html` for any unmatched HTML GET requests, ensuring client-side React routing functions correctly.

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Mount backend API routes first
# app.include_router(api_router, prefix="/api")

# Serve frontend static files
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/{catchall:path}")
def serve_react_app(catchall: str):
    return FileResponse("frontend/dist/index.html")
```

### Rationale
- **Single Port Simplicity**: Exposes only port `8100` (or another user-configured port), complying with the single-container requirement of the project constitution.
- **No CORS Issues**: Since both the UI and API run on the same origin (localhost:8100), there is no need for CORS headers or preflight checks in production.
- **Docker Multi-Stage Build**: Keeps the final runtime image lightweight by building the frontend in a Node stage, discarding Node, and copying the built assets into a clean Python environment.

### Alternatives Considered
- **Separate Frontend & Backend Containers**: Rejected. Adds docker-compose configuration overhead and violates the single-container deployment guideline in the Constitution.
- **Reverse Proxy (Nginx) in Container**: Rejected. Running an Nginx server alongside Python inside the same container requires a process manager (like Supervisord) which increases image size and complexity. Serving static assets directly via FastAPI is fast enough for local single-user tools.

---

## 2. Text Chunking Strategy

### Decision
We will use the OpenAI tokenization library `tiktoken` (specifically using the `cl100k_base` encoding, which is standard for `gpt-4o` and `gpt-4o-mini`) to precisely calculate chunk boundaries.
- **Chunk Size Limit**: Max 8,000 tokens (leaving enough buffer for a 2,000 token response within standard model token windows).
- **Split Hierarchy**:
  1. If total tokens <= 8,000, keep as a single chunk.
  2. If total tokens > 8,000, split by double newlines (`\n\n` - paragraph level).
  3. If double newlines are not present or result in chunks still > 8,000 tokens, split by single newlines (`\n`).
  4. If a single line is still > 8,000 tokens, split by sentences (using simple punctuation delimiters `.` / `?` / `!`).
- The chunker accumulates segments until adding the next segment would exceed the 8,000-token limit, at which point it starts a new chunk.

### Rationale
- **Context Preservation**: Splitting at paragraphs or line boundaries ensures that Q&As are not cut off mid-sentence, preserving context for the LLM.
- **Token Overflow Protection**: Word/character count limits can be imprecise because of token-to-character ratio variations. Using `tiktoken` guarantees we never exceed OpenAI's input token limits.

### Alternatives Considered
- **Strict Character Splitting**: Rejected. Characters do not map 1:1 to tokens. It also breaks words and sentences in half, causing loss of semantic context.

---

## 3. Factory Pattern (Backend and Frontend)

### Decision

#### Backend Factory for File Parsers
We define a base class `BaseParser` and instantiate specific parsers through a `ParserFactory`.
```python
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_content: bytes) -> str:
        pass

class TxtParser(BaseParser):
    def parse(self, file_content: bytes) -> str:
        return file_content.decode("utf-8", errors="ignore")

class ParserFactory:
    @staticmethod
    def get_parser(file_extension: str) -> BaseParser:
        if file_extension.lower() == ".txt":
            return TxtParser()
        raise ValueError(f"Unsupported file format: {file_extension}")
```

#### Frontend Factory for API Services
We will implement an `ApiClientFactory` that returns an configured instance of our API client interface, allowing easy switching between mock clients and real production Axios/Fetch clients.
```typescript
interface ApiClient {
  processFile(file: File, options: ProcessOptions): Promise<ProcessResponse>;
  saveApiKey(key: ApiKey): Promise<void>;
}

class ApiClientFactory {
  static getClient(env: string): ApiClient {
    if (env === "test") {
      return new MockApiClient();
    }
    return new ProductionApiClient();
  }
}
```

### Rationale
- **Decoupling and Extensibility**: Adapting the backend to support other text formats (like `.csv` or `.md`) in the future only requires adding a parser class and updating the factory, leaving routes untouched.
- **Testability**: Facilitates unit testing by enabling simple mock injections.

### Alternatives Considered
- **Direct inline parser and API logic**: Rejected. Hardcoding the logic inside routes prevents testing in isolation and violates the modular architecture mandate of the Constitution.

---

## 4. Semantic Deduplication and Aggregation

### Decision
Semantic deduplication will be executed in a two-stage pipeline:
1. **Extraction (Per Chunk)**: During the sequential processing of chunks, the OpenAI API will extract questions and answers. The system will prompt the model to return a structured JSON array of Q&As. The prompt instructs the LLM to padronize questions and compute frequency within *that* chunk.
2. **Consolidation (Post-Queue)**: After all chunks are processed, the accumulated list of Q&A pairs is compiled. If the number of extracted questions is low, we do a single consolidation LLM call. If high, we perform batch grouping.
   - **Consolidation Prompt**: Injects the consolidated Q&As and asks the LLM to group semantically equivalent questions (e.g. *"Qual o preço?"* and *"Quanto custa?"*), unifies them under a single canonical question/answer, and sums their frequencies.

```json
// LLM Output schema for extraction and consolidation
{
  "qna_pairs": [
    {
      "question": "Qual o horário de atendimento?",
      "answer": "Nosso atendimento é de segunda a sexta, das 8h às 18h.",
      "frequency": 3,
      "metadata": "horário, atendimento",
      "category": "Suporte"
    }
  ]
}
```

### Rationale
- **API Call Minimization**: Executing deduplication in a final consolidation step keeps total API calls to $N+1$, where $N$ is the number of chunks. This is both fast and cost-effective.
- **Semantic Quality**: Regex or string similarity algorithms (like Levenshtein) cannot detect that "Quanto custa?" and "Qual o valor?" have the same intent. Using the LLM for consolidation ensures high accuracy.

### Alternatives Considered
- **Levenshtein/Cosine Distance on Vector Embeddings**: Rejected. Generating embeddings for all questions and clustering them locally adds heavy runtime libraries (like `scikit-learn` or `numpy`) and API costs for embedding generation.
- **Incremental Deduplication**: Deduplicating chunk 2 against chunk 1, chunk 3 against the merged result, etc. Rejected because it increases total OpenAI API tokens significantly due to passing growing lists of consolidated questions in each chunk request.
