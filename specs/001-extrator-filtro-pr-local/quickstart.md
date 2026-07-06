# Quickstart: Extrator e Filtro de P&R (Local)

This guide helps you set up, develop, test, and run the project locally.

---

## 1. Prerequisites
Ensure you have the following installed on your host system:
- **Python 3.10+** (with `pip` and virtualenv)
- **Node.js 18+** (with `npm`)
- **Docker** and **Docker Compose**

---

## 2. Development Setup

### A. Clone & Setup Workspace
Navigate to the root of the project:
```bash
cd /mnt/D_DADOS/02_Projetos_Ativos/Vet_Manager/Projects/filtro_whatsapp
```

### B. Backend Setup
1. Create a Python virtual environment and activate it:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   uvicorn src.main:app --reload --port 8100
   ```
   The backend API docs will be available at `http://localhost:8100/docs`.

### C. Frontend Setup
1. Open a new terminal in the frontend directory:
   ```bash
   cd frontend
   npm install
   ```
2. Run the React Vite dev server:
   ```bash
   npm run dev
   ```
   The frontend UI will be available at `http://localhost:5100`. By default, the Vite proxy configuration directs all `/api` requests to the backend at `http://localhost:8100`.

---

## 3. Running Tests

### A. Backend Tests (Pytest)
Run unit and integration tests for the backend (including chunkers, parsers, and endpoint mock tests):
```bash
cd backend
source venv/bin/activate
pytest
```

### B. Frontend Tests (Vitest)
Run frontend UI component and factory tests:
```bash
cd frontend
npm run test
```

---

## 4. Single-Container Docker Deployment (Production)

To compile the React static assets and serve them directly from FastAPI on a single port (`8100`) inside a single Docker container, use Docker Compose.

1. Build and run the single-container instance:
   ```bash
   docker compose up --build
   ```
2. Access the application in your browser at:
   `http://localhost:8100`

The container mounts a persistent Docker volume `keys_prompts_volume` to retain your saved API keys and prompt configurations across restarts.
