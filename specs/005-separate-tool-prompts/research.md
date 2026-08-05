# Research: Separação e Isolamento de Gerenciamento de Prompts por Ferramenta

## Decisions & Technical Rationale

### 1. Extensão do Enum de Ferramentas (`TipoFerramenta`)

- **Decisão**: Expandir o enum `TipoFerramenta` (atualmente `EXTRATOR` e `GERADOR`) no backend (`schemas.py`) e frontend (`api.ts`) para incluir a terceira ferramenta da aplicação: `CONSOLIDADOR = "consolidador"`.
- **Justificativa**: A especificação (`spec.md`) e os requisitos funcionais (`FR-001`) determinam explicitamente o isolamento de prompts entre as 3 ferramentas do sistema (Extrator, Gerador e Consolidador).

### 2. Prompts Padrão Fixos por Ferramenta

- **Decisão**: 
  - Definir 3 UUIDs fixos e imutáveis em `prompt_storage.py` para representar os prompts do sistema (`_PROTECTED_PROMPT_IDS`):
    - `00000000-0000-0000-0000-000000000001`: Extrator de P&R (`TipoFerramenta.EXTRATOR`)
    - `00000000-0000-0000-0000-000000000002`: Gerador de Perguntas (`TipoFerramenta.GERADOR`)
    - `00000000-0000-0000-0000-000000000003`: Consolidador de P&R (`TipoFerramenta.CONSOLIDADOR`)
  - Atualizar os métodos de inicialização em `PromptStorageService` (`_ensure_extrator_default`, `_ensure_generator_default`, `_ensure_consolidator_default`) para garantir que os 3 prompts padrão sempre existam no arquivo JSON persistido.
  - Atualizar a rota `GET /api/prompts/default?ferramenta={tipo}` para aceitar o parâmetro opcional de ferramenta e retornar a instrução padrão correspondente à ferramenta especificada.

### 3. Duplicação de Prompt Padrão (Fluxo `Editar` -> `Duplicar (Cópia)`)

- **Decisão**:
  - Quando o usuário aciona a ação de editar no prompt padrão de qualquer ferramenta na interface frontend (`PromptSettings`), a nova cópia será automaticamente atribuída à ferramenta ativa e terá o nome ajustado para `<Nome Padrão> (Cópia)` (conforme aclaramento no `spec.md`).
  - O formulário de criação de prompt da aba `PromptSettings` aceitará um seletor/filtro de ferramenta ou renderizará o contexto da ferramenta selecionada.

### 4. Filtragem e Isolamento Estrito nas Telas e Seletores

- **Decisão**:
  - A API `GET /api/prompts?ferramenta={ferramenta}` já suporta o filtro por ferramenta. As telas de diálogo (`StartProcessModal`) e painéis de configuração passarão a utilizar a ferramenta ativa como argumento obrigatório de filtro ao listar prompts.
  - Ao excluir um prompt customizado ativo em um modal de execução, o estado de seleção voltará automaticamente para o prompt padrão (`FIXO`) daquela ferramenta.

---
## Alternatives Considered

1. **Compartilhar o endpoint `GET /api/prompts/default` sem parâmetros**:
   - *Rejeitado porque*: Não permitiria ao frontend obter a instrução do prompt padrão do Gerador ou Consolidador dinamicamente sem hardcode no frontend.
2. **Permitir mover prompts de uma ferramenta para outra**:
   - *Rejeitado porque*: A especificação estabelece que os prompts são restritos à finalidade e ferramenta específica para evitar envios de instrução incompatíveis.
