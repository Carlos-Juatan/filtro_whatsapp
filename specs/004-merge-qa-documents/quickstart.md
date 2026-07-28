# Quickstart Guide: Testing Q&A Document Merger Tool

**Feature Branch**: `004-merge-qa-documents`  

## Running Tests

Run the full backend unit and integration test suite:

```bash
backend/venv/bin/pytest backend/tests/ -v
```

Run specific merger unit tests and API integration tests:

```bash
backend/venv/bin/pytest backend/tests/unit/test_qna_merger_service.py backend/tests/integration/test_merger_api.py -v
```

## Running the Application Locally

1. Start the FastAPI backend server (port 8100):
```bash
cd backend
venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8100 --reload
```

2. Start the Vite React frontend dev server (port 5100):
```bash
cd frontend
npm run dev
```

3. Open your browser to `http://localhost:5100` (or `http://localhost:8100`), navigate to **Consolidar P&R**, select `.json` or `.txt` input files, and click **Consolidar Arquivos**.

4. Verify that:
   - Duplicate questions/answers across selected files are merged.
   - Summaries show extracted vs merged P&R count.
   - Download links for both `.json` and `.txt` are generated.
