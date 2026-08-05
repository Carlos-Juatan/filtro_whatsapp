# REST & Service Contracts: Prompts Management

## GET `/api/prompts`

Retorna a lista de prompts cadastrados, com suporte a filtragem por ferramenta.

### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `ferramenta` | `string` (`extrator` \| `gerador` \| `consolidador`) | Não | Filtra os prompts pela ferramenta especificada. Se omitido, retorna todos. |

### Exemplo de Resposta `200 OK`

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000001",
    "nome": "Padrão do Sistema",
    "tipo": "FIXO",
    "textoInstrucao": "Você é um especialista em extração...",
    "palavrasChave": [],
    "idiomaModelo": "pt-br",
    "modeloOpenAI": "gpt-4o-mini",
    "ferramenta": "extrator"
  }
]
```

---

## GET `/api/prompts/default`

Retorna a instrução do prompt padrão do sistema.

### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `ferramenta` | `string` (`extrator` \| `gerador` \| `consolidador`) | Não | Ferramenta cujo prompt padrão deve ser retornado (padrão: `extrator`). |

### Exemplo de Resposta `200 OK`

```json
{
  "textoInstrucao": "Você é um especialista..."
}
```

---

## POST `/api/prompts`

Cria um novo prompt customizado vinculado a uma ferramenta específica.

### Body Schema (`PromptConfigCreate`)

```json
{
  "nome": "Meu Prompt Extrator (Cópia)",
  "textoInstrucao": "Instruções customizadas para a extração...",
  "palavrasChave": ["faq", "suporte"],
  "idiomaModelo": "pt-br",
  "modeloOpenAI": "gpt-4o-mini",
  "ferramenta": "extrator"
}
```

### Resposta `201 Created`

Retorna o objeto `PromptConfig` criado contendo o `id` gerado e `tipo: "CUSTOMIZADO"`.

---

## DELETE `/api/prompts/{prompt_id}`

Exclui um prompt customizado.

### Respostas

- `204 No Content`: Excluído com sucesso.
- `403 Forbidden`: Tentativa de excluir um prompt padrão (`FIXO`).
- `404 Not Found`: ID de prompt não encontrado.
