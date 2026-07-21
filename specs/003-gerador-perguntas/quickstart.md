# Quickstart: Gerador de Perguntas

This quickstart guide describes how to run and test the Question Generator feature after implementation.

## Prerequisites
- A working Docker setup or running services locally.
- A valid OpenAI API key configured.

---

## 1. Running Backend & Frontend Locally

If you are running backend and frontend independently for local development:

### Backend
1. Go to the `backend/` directory.
2. Initialize virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

### Frontend
1. Go to the `frontend/` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run Vite dev server:
   ```bash
   npm run dev
   ```

---

## 2. Running Verification Tests

We provide tests to verify the correctness of prompt segregation and the new WebSocket router.

### Running Unit & Integration Tests
Run pytest in the backend directory:
```bash
cd backend
pytest -v tests/test_generator_client.py tests/test_websocket_generator.py
```

---

## 3. Verifying Prompt Storage Migration

When the backend starts up, it automatically migrates the existing database.
1. Check `backend/data/prompts.json` after running the app.
2. Verify that:
   - All existing prompts contain the field `"ferramenta": "extrator"`.
   - A new default prompt named `"Gerador de Perguntas Padrão"` exists with ID `00000000-0000-0000-0000-000000000002` and `"ferramenta": "gerador"`.
