# Feature Specification: Gerador de Perguntas a partir de Conteúdo Não Classificado

**Feature Branch**: `003-gerador-perguntas`  
**Created**: 2026-07-15  
**Status**: Draft  
**Input**: User description: "eu tenho vários arquivos .txt de conteúdo não classificado e quero criar uma nova função no menu principal separada das outras funções que vai usar ia para gerar perguntas usando esse conteúdo como respostas criando assim pares de perguntas e respostas usando e podendo extrair em .json e .txt usando a mesma estrutura da ferramenta anterior de extrair os pares"

## Clarifications

### Session 2026-07-15
- Q: Como o Gerador de Perguntas deve fatiar os arquivos de texto (.txt) de entrada antes de enviá-los para a API da OpenAI? → A: Fatiamento Hierárquico Baseado em Tokens (Padrão) utilizando a lógica existente com `tiktoken` e limite de 8.000 tokens.
- Q: Como deve funcionar a configuração de prompt para o Gerador de Perguntas? → A: Reutilizar o sistema de prompts existente (PromptConfig), adicionando separação por tipo de ferramenta para evitar mistura de prompts entre o Extrator e o Gerador na interface.
- Q: O Gerador de Perguntas deve usar uma nova rota de WebSocket ou estender a atual? → A: Novo Endpoint de WebSocket (/api/generate) no backend para manter o código modular e isolado.
- Q: Como o sistema deve definir os campos de Categoria (category) e Metadados (metadata) para os pares gerados? → A: Manter a compatibilidade com o extrator, onde 'metadata' contém a categoria da dúvida e 'category' é definido como 'FAQ' por padrão.
- Q: Qual campo e valores adicionar ao modelo PromptConfig para separar os prompts? → A: Campo 'ferramenta' com Enum ("extrator" | "gerador"), com padrão "extrator" para compatibilidade, garantindo a existência de um prompt padrão do sistema específico para o Gerador de Perguntas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Geração de Perguntas por IA a partir de Conteúdo Não Classificado (Priority: P1)

Como usuário, desejo realizar o upload de múltiplos arquivos de texto contendo conteúdo declarativo não classificado, fazendo com que o sistema envie esses textos para a inteligência artificial para que ela gere perguntas pertinentes para cada fato/afirmação presente no texto, tratando a afirmação original como a resposta, e agrupando o par resultante de Pergunta e Resposta em uma tabela.

**Why this priority**: Esta é a funcionalidade principal da nova ferramenta. Sem a capacidade de gerar perguntas associadas às afirmações de entrada e agrupá-las em formato de P&R, o objetivo do usuário não é atendido.

**Independent Test**: Pode ser testado carregando um arquivo contendo afirmações fáceis (ex: "A mensalidade do plano premium é 50 reais.") e verificando se:
- O sistema processa o arquivo e a IA gera uma pergunta correspondente (ex: "Qual o valor da mensalidade do plano premium?").
- O par de P&R é inserido em uma tabela com a pergunta gerada no campo correspondente e a afirmação original no campo de resposta.

**Acceptance Scenarios**:

1. **Given** que o usuário está no módulo "Gerador de Perguntas" e possui uma chave de API ativa, **When** ele faz o upload de um arquivo com afirmações declarativas e inicia o processamento, **Then** o sistema gera perguntas correspondentes para cada fato do arquivo, mapeando a afirmação original como a resposta.
2. **Given** que o processamento gerou pares de P&R, **When** existem fatos duplicados ou semanticamente muito similares nos arquivos de entrada, **Then** o sistema agrupa os pares semelhantes, consolidando-os sob uma pergunta comum e incrementando a contagem de frequência correspondente.

---

### User Story 2 - Menu Principal de Navegação Separado (Priority: P1)

Como usuário, desejo alternar facilmente entre o "Extrator de P&R" (ferramenta existente) e o "Gerador de Perguntas" (nova ferramenta) por meio de um menu de navegação ou abas principais na interface do sistema, mantendo os fluxos de trabalho e dados de cada ferramenta independentes.

**Why this priority**: É essencial para garantir que o usuário perceba e utilize a nova função de forma independente e limpa, sem misturar os fluxos de entrada (conversas do WhatsApp no extrator vs. base de afirmações declarativas no gerador).

**Independent Test**: Pode ser testado clicando nos botões de navegação no cabeçalho ou menu principal e confirmando se a interface se altera completamente para exibir a tela correspondente de cada ferramenta.

**Acceptance Scenarios**:

1. **Given** que o usuário abriu a aplicação, **When** ele visualiza o topo da página, **Then** ele vê um menu principal com opções claramente identificadas para "Extrair P&R" e "Gerar Perguntas".
2. **Given** que o usuário está no meio de um fluxo de visualização de resultados no "Extrator de P&R", **When** ele clica no menu para ir para o "Gerador de Perguntas", **Then** a interface troca para a tela limpa do gerador sem perder o estado/dados da tela do extrator se ele decidir voltar.

---

### User Story 3 - Exportação de Resultados no Mesmo Formato Anterior (Priority: P1)

Como usuário, desejo baixar os pares de perguntas e respostas gerados no novo módulo nos mesmos formatos TXT e JSON suportados pela ferramenta original, para que eu possa integrá-los e importá-los em outros sistemas sem necessidade de readequar o esquema de dados.

**Why this priority**: Permite a compatibilidade direta e o intercâmbio de dados entre as ferramentas e os sistemas de importação de banco de dados do usuário.

**Independent Test**: Pode ser testado gerando alguns pares no novo módulo, baixando o arquivo JSON e o arquivo TXT, e verificando se a estrutura física e as chaves de dados coincidem exatamente com a estrutura gerada pelo extrator de pares padrão.

**Acceptance Scenarios**:

1. **Given** que o usuário concluiu a geração de 10 pares de P&R no novo módulo, **When** ele clica em exportar para JSON, **Then** o navegador faz o download de um arquivo contendo a estrutura com a chave principal `qna_pairs` e os campos `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata` e `category`.
2. **Given** a tabela de resultados de geração ativa, **When** o usuário clica em exportar para TXT, **Then** o download gera um arquivo de texto onde cada par é formatado com seu indicador de categoria, frequência, pergunta prefixada por "Q:" e resposta prefixada por "A:", separados por uma linha tracejada.

### Edge Cases

- **Entradas vazias ou sem afirmações factuais (EC-01)**: Se o usuário subir um arquivo .txt vazio ou que contenha apenas caracteres especiais e linhas em branco no Gerador de Perguntas, o sistema deve registrar um alerta amigável nos logs e desabilitar o botão de início ou ignorar o arquivo, sem quebrar a execução global da fila.
- **Erro de cota ou rede no meio da geração (EC-02)**: Se a API falhar no meio do processamento em lote de múltiplos arquivos, o processamento deve parar, um log vermelho deve indicar a interrupção, e o usuário deve ser capaz de visualizar e exportar os pares que já foram gerados com sucesso até o momento do erro.
- **Afirmações extremamente curtas ou incoerentes (EC-03)**: Se uma linha contiver apenas uma palavra solta ou algo sem sentido (ex: "ok" ou "teste"), a IA deve ignorar esse item ao invés de inventar uma pergunta sem base, mantendo a qualidade da base de dados.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST fornecer um menu de navegação principal (ou abas globais no topo do layout) separado das outras funções, permitindo alternar de forma limpa entre o "Extrator de P&R" e o "Gerador de Perguntas".
- **FR-002**: O módulo "Gerador de Perguntas" MUST permitir o upload de múltiplos arquivos `.txt` contendo afirmações declarativas, regras de negócio ou conteúdos não classificados.
- **FR-003**: O sistema MUST fatiar e processar os arquivos do gerador em uma fila sequencial ordenada (FIFO), enviando requisições à API de inteligência artificial de forma segura.
- **FR-004**: O sistema MUST usar a IA para ler o conteúdo declarativo de entrada, identificar as afirmações factuais relevantes e gerar uma pergunta correspondente para cada afirmação, retornando a pergunta gerada (como `question`) e a afirmação original (como `answer`) mapeadas.
- **FR-005**: O sistema MUST suportar a segmentação dos arquivos de entrada utilizando o fatiamento hierárquico baseado em tokens (limite de 8.000 tokens, preservando parágrafos e linhas).
- **FR-006**: O sistema MUST suportar configurações de prompt flexíveis para guiar a IA na geração de perguntas adequadas, reutilizando o modelo PromptConfig, porém adicionando diferenciação por tipo de ferramenta para evitar a mistura de prompts entre o Extrator e o Gerador.
- **FR-007**: O sistema MUST agrupar e consolidar semanticamente as perguntas geradas que forem idênticas ou muito semelhantes, somando suas frequências de ocorrência e unificando categorias, usando a mesma lógica de consolidação da ferramenta existente.
- **FR-008**: O par de P&R gerado no novo módulo MUST ser mapeado sob a mesma entidade interna e mesma estrutura JSON da ferramenta anterior, onde o campo `metadata` contém a categoria da dúvida/fato classificado pela IA, e o campo `category` é definido como 'FAQ' por padrão.
- **FR-009**: O frontend MUST disponibilizar os mesmos botões de exportação (TXT e JSON) na aba de resultados do novo módulo, gerando os arquivos com a mesma formatação e chaves da ferramenta de extração original.
- **FR-010**: O frontend MUST exibir logs em tempo real na tela para o processo de geração, com marcações de início, progresso de arquivos/lotes, conclusões de chunks e consolidação.
- **FR-011**: O backend MUST expor uma nova rota de WebSocket em `/api/generate` para processar exclusivamente as requisições do módulo Gerador de Perguntas.

### Key Entities *(include if feature involves data)*

- **ParPerguntaRespostaGerado (Em Memória)**: Par de pergunta gerada pela IA e resposta obtida da afirmação original.
  - `perguntaPadronizada`: Pergunta estruturada pela IA a partir do fato fornecido.
  - `respostaConsolidada`: A afirmação declarativa original que serviu de base.
  - `frequencia`: Frequência de ocorrência do fato ou da pergunta consolidada (inicialmente 1, cumulativa se agrupada).
  - `metadata`: Palavras-chave ou tags contextuais geradas pela IA.
  - `category`: Categoria temática atribuída ao par (ex: "Financeiro", "Atendimento").

- **PromptConfig (Modificado)**: Extensão do modelo existente para suportar segregação por ferramenta.
  - `ferramenta`: Identificador da ferramenta à qual o prompt se aplica (Enum: "extrator" ou "gerador", padrão: "extrator").

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O tempo de alternância de tela entre as duas ferramentas principais do menu não deve exceder 150ms.
- **SC-002**: 100% das exportações em JSON do novo módulo devem conter exatamente a mesma estrutura de chaves do extrator original (`qna_pairs` contendo itens com `perguntaPadronizada`, `respostaConsolidada`, `frequencia`, `metadata`, `category`), passando em testes de validação de esquema.
- **SC-003**: 100% dos pares gerados no novo módulo devem estar no idioma selecionado pelo usuário nas configurações do sistema.
- **SC-004**: O sistema deve conseguir processar lotes com arquivos totalizando até 500.000 caracteres no Gerador de Perguntas sem travar a interface ou causar vazamento de conexões no WebSocket.

## Assumptions

- O usuário usará chaves de API válidas e configuradas na central de configurações existente, que será compartilhada por ambos os módulos.
- Os arquivos carregados no Gerador de Perguntas estão no formato de texto simples (.txt) contendo afirmações úteis e informativas sobre o negócio.
- O modelo selecionado nas configurações padrão (ex: `gpt-4o-mini` ou `gpt-4o`) tem capacidade para entender afirmações factuais em linguagem natural e redigir perguntas gramaticalmente corretas no idioma especificado.
