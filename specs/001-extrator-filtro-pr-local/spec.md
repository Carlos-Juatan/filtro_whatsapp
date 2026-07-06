# Feature Specification: Extrator e Filtro de P&R (Local)

**Feature Branch**: `001-extrator-filtro-pr-local`  
**Created**: 2026-07-03  
**Status**: Draft  
**Input**: User description: "Feature Specification: Extrator e Filtro de P&R (Local)"

## Clarifications

### Session 2026-07-06
- Q: Which OpenAI model should the application use for text processing, and how should it be configured? → A: Configurable dropdown in settings (default to gpt-4o-mini, option for gpt-4o).
- Q: How should the API keys (`ChaveAPI`) be stored inside the persistent Docker volume? → A: Stored in plain text (JSON file) in the persistent Docker volume.
- Q: When processing a long document split into multiple chunks, how should the system handle transient rate limits (HTTP 429) from the OpenAI API? → A: Automatic retry with exponential backoff: retry the chunk request up to 3 times before failing the queue.
- Q: How should the system handle name collisions when a user adds or edits an API key (`ChaveAPI`) using an existing `nomeIdentificacao`? → A: Enforce unique names: reject saving and show a validation error if the name is already in use.
- Q: To avoid scope creep and define clear boundaries, what should be explicitly declared as out-of-scope for the first release of the system? → A: Out of scope: Non-OpenAI models, user authentication/multi-user isolation, and direct binary/complex document parsing (PDF, DOCX).
- Q: Qual deve ser a porta padrão do container Docker para o sistema? → A: Porta 8100 (substituindo a porta 8000 padrão).
- Q: Qual deve ser a porta padrão do servidor de desenvolvimento do frontend? → A: Porta 5100 (substituindo a porta 5173 padrão).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Processamento Local de P&R com Fatiamento e Fila (Priority: P1)

Como usuário, desejo realizar o upload de múltiplos arquivos de texto locais, fazendo com que o sistema os divida de forma inteligente em pedaços e processe-os sequencialmente usando a API de inteligência artificial configurada, visualizando o progresso em tempo real através de logs detalhados na tela.

**Why this priority**: Este é o motor de execução do sistema. Sem a habilidade de carregar arquivos, fatiá-los para respeitar limites de tokens e enviá-los em fila para a API, a ferramenta não possui utilidade principal.

**Independent Test**: Pode ser testado carregando um arquivo longo de texto, inserindo uma chave de API válida, iniciando o processo e verificando se:
- O arquivo é fatiado corretamente mantendo a integridade dos parágrafos/linhas.
- As requisições são feitas uma a uma em fila.
- A área de log exibe as mensagens de início, progresso de pedaços e conclusão em tempo real.

**Acceptance Scenarios**:

1. **Given** que o usuário carregou 2 arquivos (um curto e um longo contendo mais de 50.000 caracteres) e configurou uma chave de API válida, **When** ele clica em "Iniciar Filtragem", **Then** o sistema fatia o arquivo longo em pedaços menores (respeitando finais de parágrafo), coloca todos os pedaços na fila e os processa sequencialmente (um por vez), atualizando os logs na tela a cada requisição.
2. **Given** que a fila de processamento está ativa, **When** o processamento de um pedaço ou arquivo falha devido a erro da API, **Then** o sistema interrompe a fila imediatamente, registra o erro em destaque visual vermelho no log, mas preserva todos os resultados de P&R já extraídos com sucesso na tela e ativa os botões de exportação parcial.

---

### User Story 2 - Exibição de Resultados Agrupados e Exportação (Priority: P1)

Como usuário, desejo visualizar as perguntas e respostas extraídas agrupadas semântica e logicamente, com a contagem precisa de suas frequências, e exportar esses resultados em arquivos nos formatos TXT e JSON.

**Why this priority**: A consolidação e a exportação dos dados são fundamentais para que o usuário possa reutilizar a inteligência extraída em outros sistemas de suporte ou bases de conhecimento.

**Independent Test**: Pode ser testado executando o processamento de um arquivo pequeno de testes que contenha perguntas repetidas sob redações ligeiramente diferentes (ex: "Qual o horário de funcionamento?" e "Que horas vocês abrem?"), garantindo que sejam agrupadas em um único item padronizado com frequência = 2, e que os arquivos baixados (TXT e JSON) correspondam à estrutura exibida.

**Acceptance Scenarios**:

1. **Given** que o processamento da fila foi concluído, **When** a interface exibe a tabela de resultados, **Then** o sistema exibe cada pergunta padronizada, sua resposta consolidada e a contagem correta de frequência de ocorrência.
2. **Given** que a interface exibe a lista de resultados consolidados, **When** o usuário clica em "Baixar Relatório Visual (TXT)", **Then** o navegador faz o download de um arquivo `.txt` formatado legível para humanos.
3. **Given** que a interface exibe a lista de resultados consolidados, **When** o usuário clica em "Baixar Dados Estruturados (JSON)", **Then** o navegador faz o download de um arquivo `.json` válido contendo a lista de objetos estruturados com os campos `question`, `answer`, `metadata` e `category`.

---

### User Story 3 - Gestão e Seleção de Chaves de API em Volume Docker (Priority: P1)

Como usuário, desejo cadastrar minhas chaves de API da OpenAI no sistema sob nomes de identificação amigáveis, mantendo-as salvas localmente em um volume do Docker, para que eu possa selecioná-las facilmente antes de iniciar o processamento sem precisar digitá-las repetidamente.

**Why this priority**: Permite que a aplicação funcione de forma totalmente local e segura no ambiente do usuário, sem necessidade de banco de dados externo na nuvem nem risco de exposição de chaves fora de seu controle.

**Independent Test**: Pode ser testado adicionando uma nova chave no modal de configurações, atualizando a página do navegador (F5), e verificando se a chave continua listada e disponível para seleção na lista suspensa do processamento.

**Acceptance Scenarios**:

1. **Given** que o usuário abre o modal de gerenciamento de chaves, **When** ele insere um nome identificador ("OpenAI Produção") e o valor da chave de API e clica em salvar, **Then** a chave é persistida no volume Docker e passa a constar na lista de seleção.
2. **Given** que o usuário reinicia o container Docker, **When** ele acessa a lista de chaves, **Then** as chaves cadastradas anteriormente permanecem disponíveis, mas nenhuma outra informação de arquivos ou logs anteriores é exibida na tela.

---

### User Story 4 - Configuração de Prompt Personalizado e Seleção de Idioma (Priority: P2)

Como usuário, desejo personalizar o prompt de filtragem (escolhendo entre um prompt padrão fixo ou um prompt customizado persistido localmente) e configurar o idioma de resposta do modelo, para obter os resultados de P&R padronizados e traduzidos conforme minhas preferências.

**Why this priority**: Permite flexibilidade de filtragem para cenários comerciais específicos e garante a entrega em múltiplos idiomas mesmo quando a entrada é em outra língua.

**Independent Test**: Pode ser testado selecionando o idioma "en" (inglês) e um prompt personalizado no modal, rodando o extrator com um arquivo de entrada em português, e verificando se a saída gerada pela API está totalmente traduzida em inglês.

**Acceptance Scenarios**:

1. **Given** que o usuário está no modal de configurações, **When** ele seleciona um idioma de resposta (ex: "en") e salva, **Then** o sistema concatena essa diretriz como instrução mandatória no prompt final enviado à API da OpenAI.
2. **Given** que o usuário opta por configurar um "Prompt Customizado", **When** ele edita o texto e salva, **Then** as novas instruções de prompt são salvas no volume Docker e aplicadas no próximo processamento de arquivo.

---

### Edge Cases

- **Falha de API no meio do processamento (EC-01)**: Se a API da OpenAI falhar no 3º pedaço de um arquivo de 5 pedaços (e persistir após tentativas de reprocessamento, se aplicável), o processamento deve ser interrompido e a tela deve exibir uma mensagem vermelha indicando o erro. Os pares de P&R extraídos nos pedaços 1 e 2 devem continuar visíveis e exportáveis.
- **Arquivo Vazio ou sem P&R Identificáveis (EC-02)**: Se o upload for de um arquivo de texto sem diálogos/perguntas úteis, a resposta do modelo retornará vazia. O log do sistema deve registrar um aviso, mas a execução da fila não deve ser quebrada, continuando normalmente para o próximo arquivo/pedaço.
- **Chave de API inválida ou expirada (EC-03)**: O sistema deve capturar a mensagem de erro específica da OpenAI (ex: "Invalid API key") e exibi-la de forma limpa na área de log em vermelho, instruindo o usuário a revisar a chave.
- **Limite de Requisições / Rate Limiting (EC-04)**: Se a API da OpenAI retornar erro HTTP 429, o sistema tentará realizar retentativa automática com backoff exponencial (até 3 tentativas nos intervalos de 2s, 4s, 8s). Se a falha persistir após todas as tentativas, aplica-se a regra de interrupção (EC-01).

### Out of Scope / Fora de Escopo

- Suporte a modelos que não sejam da OpenAI (como Anthropic Claude, Google Gemini ou modelos locais via Ollama).
- Autenticação de usuários, controle de acesso ou suporte multi-tenant (o sistema é estritamente de usuário único local).
- Processamento direto de formatos de documentos binários ou complexos (como arquivos PDF, DOCX, XLSX). O sistema aceita apenas arquivos de texto simples (.txt) ou compatíveis.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST operar de forma estritamente local (localhost), com todos os logs, arquivos carregados e resultados finais mantidos apenas em memória durante a sessão (com exceção das chaves de API e prompts customizados salvos no volume Docker).
- **FR-002**: O sistema MUST persistir a lista de chaves de API (`ChaveAPI`) no volume Docker (em formato JSON em texto plano), permitindo a inclusão (com validação de unicidade do `nomeIdentificacao`), seleção e exclusão de chaves através da interface do usuário.
- **FR-003**: O sistema MUST persistir as configurações de prompts customizados (`PromptConfig`) no volume Docker.
- **FR-004**: O modal de configuração MUST disponibilizar um campo de seleção de idioma para as respostas do modelo (com padrão de fábrica definido como "pt-br") e um campo de seleção para o modelo OpenAI (com padrão definido como "gpt-4o-mini", com a opção de selecionar "gpt-4o").
- **FR-005**: O sistema MUST concatenar o idioma selecionado como uma diretriz obrigatória de saída no prompt enviado à API da OpenAI (ex: *"Retorne todas as perguntas e respostas estritamente no idioma: [Idioma Selecionado]"*).
- **FR-006**: O sistema MUST quebrar os arquivos de texto carregados em pedaços (*chunks*) baseados em limites seguros de tokens/caracteres, garantindo que as divisões ocorram em quebras de parágrafo ou de linha para preservar o contexto.
- **FR-007**: O sistema MUST gerenciar o processamento de pedaços e arquivos em uma fila sequencial ordenada (FIFO), enviando uma requisição por vez para a API da OpenAI.
- **FR-008**: O sistema MUST injetar instruções no prompt enviado à OpenAI exigindo a unificação semântica de perguntas similares sob uma mesma redação padronizada.
- **FR-009**: O sistema MUST acumular os resultados extraídos de todos os pedaços, recalcular a frequência total de cada pergunta encontrada e exibir esses dados agrupados na tela.
- **FR-010**: O sistema MUST disponibilizar a exportação dos dados consolidados em formato TXT (formatado para leitura humana) e em formato JSON (estruturado, contendo `question`, `answer`, `metadata` e `category`).
- **FR-011**: O sistema MUST exibir uma área de registro de logs (`ItemLog`) na tela, atualizada em tempo real com timestamp e indicando eventos informativos (INFO), sucessos (SUCESSO) ou erros (ERRO).
- **FR-012**: O sistema MUST tentar reprocessar automaticamente requisições que falharem por limite de taxa (HTTP 429) usando backoff exponencial de até 3 tentativas (intervalos de 2s, 4s, 8s). Se o erro persistir após 3 tentativas ou se for um erro de outra natureza, o sistema MUST interromper o processamento da fila imediatamente, exibindo o log de erro em vermelho e preservando os dados extraídos até então.

### Key Entities *(include if feature involves data)*

- **ChaveAPI (Persistida no volume Docker)**: Representa uma credencial da OpenAI configurada pelo usuário.
  - `id`: Identificador único gerado automaticamente.
  - `nomeIdentificacao`: Rótulo amigável atribuído à chave (deve ser único no sistema).
  - `chave`: A string correspondente à chave da API OpenAI (armazenada em texto plano no volume Docker).
- **PromptConfig (Persistida no volume Docker para customizados, em memória para o padrão)**: Representa a instrução de filtragem que guia o modelo.
  - `id`: Identificador único.
  - `nome`: Nome identificador do prompt.
  - `tipo`: "FIXO" (padrão do sistema) ou "CUSTOMIZADO" (editável pelo usuário).
  - `textoInstrucao`: O corpo do texto do prompt que instrui a IA na extração de P&R.
  - `palavrasChave`: Palavras-chave opcionais aplicadas como filtro no tipo FIXO.
  - `idiomaModelo`: Código/Nome do idioma de destino da resposta (ex: "pt-br", "en").
  - `modeloOpenAI`: Identificador do modelo da OpenAI a ser utilizado (padrão: "gpt-4o-mini", alternativa: "gpt-4o").
- **ArquivoProcessamento (Em Memória)**: Representa um arquivo carregado pelo usuário para extração.
  - `id`: Identificador único.
  - `nomeArquivo`: Nome original do arquivo.
  - `tamanho`: Tamanho do arquivo em bytes.
  - `conteudoBruto`: Texto completo original.
  - `chunks`: Lista de pedaços gerados a partir do fatiamento inteligente.
  - `status`: Estado atual na fila de execução ("PENDENTE", "PROCESSANDO", "CONCLUIDO", "ERRO").
- **ResultadoParPR (Em Memória)**: Par de pergunta e resposta extraído e agrupado pelo sistema.
  - `perguntaPadronizada`: Pergunta higienizada e unificada de forma semântica pela IA.
  - `respostaConsolidada`: Resposta resumida correspondente à intenção da pergunta.
  - `frequencia`: Contagem cumulativa de vezes que essa pergunta foi identificada.
  - `metadata`: Tags adicionais ou palavras de contexto associadas.
  - `category`: Categoria de agrupamento lógica associada à pergunta.
- **ItemLog (Em Memória)**: Registro de evento exibido na tela.
  - `timestamp`: Horário em formato HH:MM:SS.
  - `tipo`: Tipo do evento ("INFO", "SUCESSO", "ERRO").
  - `mensagem`: Descrição detalhada do evento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O fatiador inteligente deve processar arquivos de texto de até 1.000.000 de caracteres dividindo-os em pedaços de no máximo 10.000 caracteres (ou limites equivalentes baseados no modelo), sem quebrar palavras ao meio ou estourar os limites de requisição da API.
- **SC-002**: Toda exportação JSON deve passar por validação de esquema de dados antes do download, garantindo que o arquivo contenha uma lista de objetos contendo exatamente os campos: `question`, `answer`, `metadata` e `category`.
- **SC-003**: 100% dos pares de P&R exibidos ou exportados devem estar estritamente no idioma selecionado pelo usuário no modal de parametrização (se o idioma selecionado for "en", por exemplo, toda a saída deve ser em inglês).
- **SC-004**: O tempo de renderização visual na tela após a conclusão da fila para um volume de até 500 pares de P&R deve ser inferior a 200ms.
- **SC-005**: Ao recarregar a página (F5), todos os arquivos, logs e resultados acumulados em memória devem ser destruídos instantaneamente, garantindo a privacidade dos dados locais e restabelecendo o estado inicial limpo da aplicação.

## Assumptions

- O usuário possui acesso à internet para que a API local da aplicação se comunique diretamente com o endpoint da OpenAI.
- O ambiente Docker possui um volume persistente montado e configurado corretamente para reter arquivos de chaves de API e prompts.
- Os arquivos carregados estão em formato de texto simples (.txt) ou arquivos com codificação de texto compatível, sem criptografia ou formatação binária complexa.
