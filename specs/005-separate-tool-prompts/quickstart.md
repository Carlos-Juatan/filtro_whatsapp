# Quickstart: Separação de Prompts por Ferramenta

## Execução e Testes

### 1. Testes do Backend

Para executar a suíte de testes do backend validando a segregação por ferramenta:

```bash
cd backend
pytest tests/test_prompts.py
```

### 2. Testes do Frontend

Para rodar os testes dos componentes frontend React (incluindo renderização de prompts por ferramenta e fluxo de duplicação):

```bash
cd frontend
npm test -- --run
```

### 3. Validação Manual na Interface

1. Abra as **Configurações > Prompts e Idiomas**.
2. Alterne entre as abas ou filtros de ferramenta (Extrator, Gerador, Consolidador).
3. Verifique que cada ferramenta exibe exclusivamente o seu prompt padrão (`FIXO`) e seus respectivos prompts customizados.
4. Clique no ícone de **Duplicar/Editar** em um prompt padrão e confirme que a nova cópia é criada com a nomenclatura `<Nome Padrão> (Cópia)` na lista daquela ferramenta específica.
