# Feature Specification: Separação e Isolamento de Gerenciamento de Prompts por Ferramenta

**Feature Branch**: `005-separate-tool-prompts`  
**Created**: 2026-08-05  
**Status**: Draft  
**Input**: User description: "Vamos corrigir a configuração de prompt, porque na ferramenta 1 existe o prompt padrão que não pode ser apagado. Quando você clica em edit, você vai copiar ele. Você tem uma cópia para editar. Isso está funcionando. Porém, as outras duas ferramentas devem ter o mesmo sistema de prompt. Onde você vai ter a prompt padrão, que não pode ser apagado. Se clicar em editar, você pode adicionar uma cópia desse prompt na lista dessa nova ferramenta. Ou seja, cada ferramenta deve ter uma lista de prompt for aquela ferramenta específica. Não misturando os prompt de ferramentas diferentes. Atualmente somente a primeira ferramenta de extração de conversas está funcionando essa ferramenta. Porém, as três ferramentas devem ter a mesma função separadas uma da outra. O prompt de uma ferramenta não deve ficar na lista de prompt da outra ferramenta. Elas devem ser separadas."

## Clarifications

### Session 2026-08-05

- Q: Qual deve ser o nome padrão atribuído à nova cópia gerada ao editar o prompt padrão? → A: Option A - Sufixar o nome original: `<Nome Padrão> (Cópia)`.
- Q: Qual prompt deve ser selecionado se o prompt customizado ativo for excluído ou se não houver customizados? → A: Option A - Voltar a seleção para o prompt padrão da respectiva ferramenta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerenciamento e Duplicação de Prompt Padrão por Ferramenta (Priority: P1)

Como usuário do sistema, quero que cada uma das três ferramentas (Extração de Conversas, Filtro/Classificação e Consolidador/Outra ferramenta) possua sua própria lista isolada de prompts, com um prompt padrão imutável (Read-Only) em cada uma, para que eu possa criar cópias editáveis de prompts específicos de cada ferramenta sem misturar os conteúdos.

**Why this priority**: É a funcionalidade central solicitada. Atualmente, somente a ferramenta 1 funciona corretamente com o fluxo de cópia ao editar o prompt padrão, enquanto as ferramentas 2 e 3 compartilham ou não possuem a mesma segregação de lista de prompts por ferramenta.

**Independent Test**: Pode ser testado acessando a aba/configuração de cada uma das 3 ferramentas, verificando que cada ferramenta mostra apenas os seus prompts específicos, que o prompt padrão de cada uma não pode ser excluído nem alterado diretamente, e que clicar em "Editar" no prompt padrão gera uma cópia editável adicionada exclusivamente à lista daquela ferramenta.

**Acceptance Scenarios**:

1. **Given** que o usuário está na interface da Ferramenta 1 (Extração de Conversas), **When** visualiza a lista de prompts, **Then** apenas os prompts associados à Ferramenta 1 são exibidos, incluindo o prompt padrão da Ferramenta 1 marcado como imutável.
2. **Given** que o usuário está na interface da Ferramenta 2, **When** visualiza a lista de prompts, **Then** apenas os prompts associados à Ferramenta 2 são exibidos, incluindo o prompt padrão imutável da Ferramenta 2.
3. **Given** que o usuário está na interface da Ferramenta 3, **When** visualiza a lista de prompts, **Then** apenas os prompts associados à Ferramenta 3 são exibidos, incluindo o prompt padrão imutável da Ferramenta 3.
4. **Given** que o usuário clica em "Editar" no prompt padrão de qualquer uma das três ferramentas, **When** a ação é confirmada/executada, **Then** uma nova cópia editável nomeada como `<Nome Padrão> (Cópia)` é criada e armazenada exclusivamente na lista correspondente àquela ferramenta.
5. **Given** que o usuário exclui o prompt customizado atualmente selecionado em uma ferramenta, **When** a exclusão é concluída, **Then** a seleção de prompt ativo da ferramenta retorna automaticamente para o seu prompt padrão.

---

### User Story 2 - Isolamento Estrito de Listas de Prompts entre Ferramentas (Priority: P2)

Como usuário do sistema, quero garantir que prompts criados ou modificados para uma ferramenta específica não apareçam nas seleções ou listas de outras ferramentas, para evitar ambiguidades ou envios de prompts incorretos durante a execução.

**Why this priority**: Garante a integridade e a consistência das operações, evitando que prompts de extração sejam aplicados na consolidação ou vice-versa.

**Independent Test**: Pode ser testado criando um prompt customizado na Ferramenta 1 e alternando para as Ferramentas 2 e 3 para confirmar que o novo prompt não é visível ou selecionável nelas.

**Acceptance Scenarios**:

1. **Given** que um novo prompt customizado é criado na Ferramenta 2, **When** o usuário navega para a Ferramenta 1 ou Ferramenta 3, **Then** o prompt customizado criado na Ferramenta 2 não aparece na lista de seleção.

---

### User Story 3 - Acesso à Ferramenta de Consolidação na Interface (Priority: P1)

Como usuário do sistema, quero ter um botão de acesso no cabeçalho (header) e na navegação mobile para a ferramenta "Consolidador", para que eu possa acessar sua interface, visualizar seu painel e configurar seus prompts isolados.

**Why this priority**: Sem esse acesso na interface, é impossível atingir a separação e o isolamento de prompts para a Ferramenta 3, pois ela se torna inacessível para o usuário final.

**Independent Test**: Pode ser testado visualizando o cabeçalho superior e a barra mobile para verificar se a opção "Consolidador" está visível e, ao clicar, abre o painel correto.

**Acceptance Scenarios**:

1. **Given** que o usuário está na tela inicial, **When** ele visualiza o cabeçalho (ou barra mobile), **Then** ele deve ver três botões de navegação: "Extrator", "Gerador" e "Consolidador".
2. **Given** que o usuário clica em "Consolidador", **When** a ação é concluída, **Then** a interface deve renderizar o painel específico da ferramenta de Consolidação (ConsolidatorPanel).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE manter uma segregação estrita de prompts por ferramenta (Ferramenta 1, Ferramenta 2 e Ferramenta 3).
- **FR-002**: O sistema DEVE fornecer um prompt padrão imutável (somente leitura) para cada uma das três ferramentas.
- **FR-003**: O sistema NÃO DEVE permitir a exclusão ou alteração direta do prompt padrão de nenhuma ferramenta.
- **FR-004**: Ao acionar a opção de editar no prompt padrão de qualquer ferramenta, o sistema DEVE criar uma cópia editável desse prompt nomeada com o sufixo `(Cópia)` e atribuí-la exclusivamente à lista de prompts da respectiva ferramenta.
- **FR-005**: Ao listar os prompts em qualquer tela ou componente de seleção, o sistema DEVE filtrar e retornar exclusivamente os prompts associados à ferramenta ativa no momento.
- **FR-006**: O sistema DEVE persistir a associação de cada prompt à sua respectiva ferramenta ao criar, atualizar ou carregar prompts.
- **FR-007**: Se o prompt customizado ativo em uma ferramenta for excluído, o sistema DEVE redefinir a seleção ativa automaticamente para o prompt padrão daquela ferramenta.

### Key Entities *(include if feature involves data)*

- **Prompt**: Representa o modelo de instruções para IA. Possui atributos de identificação, nome/título, conteúdo textual, indicador se é padrão (imutável/system default) e identificador da ferramenta à qual pertence (ToolType/ToolCategory).
- **Tool / Ferramenta**: Representa a ferramenta específica (ex: Extração, Filtro, Consolidador) que consome um conjunto delimitado de prompts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das três ferramentas possuem listas de prompts independentes e isoladas, sem cruzamento de prompts entre elas.
- **SC-002**: 100% das tentativas de editar um prompt padrão resultam na geração bem-sucedida de uma cópia editável pertencente exclusivamente à ferramenta correspondente.
- **SC-003**: 0% de vazamento de prompts de uma ferramenta na interface ou nos seletores de outra ferramenta.

## Assumptions

- Cada ferramenta possui regras ou objetivos distintos de IA, necessitando de prompts padrão específicos e adequados à sua função.
- O mecanismo de cópia ao clicar em "editar" existente na Ferramenta 1 serve como modelo comportamental padrão para as Ferramentas 2 e 3.
- As ferramentas referidas são as três etapas/ferramentas do fluxo da aplicação (Extração, Filtro/Classificação e Consolidação).
