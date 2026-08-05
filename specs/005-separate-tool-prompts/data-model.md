# Data Model & Domain Entities: Separação de Prompts por Ferramenta

## Entities & Enums

### 1. `TipoFerramenta` (Enum)
Categoriza as ferramentas disponíveis no sistema para isolamento de prompts.

| Valor | Descrição |
|---|---|
| `extrator` | Ferramenta de Extração de P&R a partir de conversas. |
| `gerador` | Ferramenta de Geração de Perguntas a partir de fatos declarativos. |
| `consolidador` | Ferramenta de Consolidação e Deduplicação de P&R. |

---

### 2. `PromptConfig` (Schema Pydantic / Interface TypeScript)

Estrutura de dados persistida em JSON que define um prompt no sistema.

| Campo | Tipo | Descrição | Regras de Validação / Padrão |
|---|---|---|---|
| `id` | `str` (UUID) | Identificador único do prompt. | Único; UUIDs fixos para os 3 prompts de sistema imutáveis. |
| `nome` | `str` | Nome amigável do prompt. | Tamanho entre 1 e 100 caracteres; Nome único por sistema. Ao copiar padrão: `<Nome Padrão> (Cópia)`. |
| `tipo` | `TipoPrompt` | `FIXO` ou `CUSTOMIZADO`. | `FIXO` = Imutável (Read-Only, não pode ser deletado). |
| `textoInstrucao` | `Optional[str]` | Conteúdo das instruções do LLM. | Obrigatório para prompts `CUSTOMIZADO` (min. 10 caracteres). |
| `palavrasChave` | `List[str]` | Filtros de palavras-chave. | Opcional, lista de strings. |
| `idiomaModelo` | `str` | Idioma de saída. | Padrão: `pt-br`. |
| `modeloOpenAI` | `ModeloOpenAI` | Modelo da OpenAI. | `gpt-4o-mini` ou `gpt-4o`. |
| `ferramenta` | `TipoFerramenta` | Ferramenta vinculada. | Obrigatório. Valores: `extrator`, `gerador`, `consolidador`. |

---

## State Transitions & Rules

1. **Tentativa de Deleção**:
   - `prompt.tipo == FIXO` ou `prompt.id in _PROTECTED_PROMPT_IDS` -> Retorna erro HTTP 403 / Impede deleção na UI.
   - `prompt.tipo == CUSTOMIZADO` -> Deletado com sucesso. Se era o prompt ativo na interface da ferramenta, o estado da UI redefine a seleção para o `PromptConfig` com `tipo == FIXO` e `ferramenta == activeTool`.

2. **Duplicação/Edição do Prompt Padrão**:
   - Evento: Clique em "Editar" no prompt padrão da Ferramenta X.
   - Ação: Formulário preenchido com `textoInstrucao = promptPadrao.textoInstrucao`, `nome = promptPadrao.nome + " (Cópia)"`, e `ferramenta = promptPadrao.ferramenta`.
