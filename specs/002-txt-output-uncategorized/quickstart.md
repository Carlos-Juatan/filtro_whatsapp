# Quickstart Additions: Exportar Conteúdo Não Classificado

This guide details how to verify the new Uncategorized Content Extraction and Exporting feature locally.

---

## 1. Local Testing

### A. Run Backend
Ensure your virtual environment is active and run the backend server:
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --port 8100
```

### B. Run Frontend
Run the React Vite dev server:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5100` in your web browser.

---

## 2. Verifying Feature Execution (E2E Manual Walkthrough)

To verify the extraction works end-to-end:

1. **Configure OpenAI API Key**: Go to settings and add your OpenAI API key (or ensure you have `OPENAI_API_KEY` set in your environment and use the "env" default option).
2. **Create/Use Prompt**:
   - Verify the "Padrão do Sistema" prompt is updated to instruct the model on extracting the `uncategorized_database_content` key.
   - Alternatively, create a Custom Prompt and verify that during processing, the extraction instruction suffix is appended automatically.
3. **Upload Conversation**:
   - Create a local test text file `test_conversa.txt` with declarations such as:
     ```text
     Atendente: Olá! Como posso ajudar?
     Cliente: Oi, gostaria de saber os horários e preços.
     Atendente: Nosso horário de funcionamento é das 8h às 18h de segunda a sexta.
     Cliente: Qual o preço do frete para o centro?
     Atendente: O frete é grátis para compras acima de R$ 100,00. Caso contrário, cobramos R$ 15,00.
     Atendente: Importante lembrar que não realizamos entregas aos domingos.
     ```
   - Upload this file in the UI.
4. **Trigger Processing**: Click the process button.
5. **Verify Tabbed UI & Display**:
   - After processing finishes, navigate to the results view.
   - You should see two tabs: "Perguntas & Respostas" and "Conteúdo Adicional / Base de Dados".
   - Select the second tab. You should see the extracted statements, such as:
     - `O horário de funcionamento é das 8h às 18h de segunda a sexta.`
     - `O frete é grátis para compras acima de R$ 100,00, caso contrário custa R$ 15,00.`
     - `Não são realizadas entregas aos domingos.`
6. **Verify Exporting**:
   - Click the "Baixar Conteúdo Adicional (TXT)" button.
   - Verify that the downloaded file `nao_classificados.txt` contains these statements separated by a single newline `\n`.


---

## 3. Running Backend Tests

Run the updated backend test suites:
```bash
cd backend
source venv/bin/activate
pytest tests/unit/test_openai_client.py
pytest tests/unit/test_consolidator.py
```
