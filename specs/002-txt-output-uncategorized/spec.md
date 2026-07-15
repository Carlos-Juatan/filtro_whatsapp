# Feature Specification: Exportar Conteúdo Não Classificado para Base de Dados

**Feature Branch**: `002-txt-output-uncategorized`  
**Created**: 2026-07-15  
**Status**: Draft  
**Input**: User description: "quero atualizar a saida dos arquivos para que tenha mais 1 documento .txt onde terá o conteúdo da conversa que não foi classificada como pergunta nem resposta mas que contem conteúdo que pode ser usado para a base do banco de dados"

## Clarifications

### Session 2026-07-15

- Q: Como deve ser realizada a desduplicação do conteúdo não classificado? → A: Correspondência exata de texto (case-insensitive, ignorando espaços em branco nas extremidades).
- Q: Como deve ser exportado o conteúdo não classificado ao processar múltiplos arquivos em lote? → A: Consolidado em um único arquivo `.txt` contendo os resultados de todos os arquivos do lote.
- Q: Como garantir que prompts customizados extraiam conteúdo não classificado? → A: Anexar automaticamente a instrução de extração do conteúdo não classificado ao final de todos os prompts customizados nos bastidores.
- Q: Qual deve ser o formato do conteúdo dentro do arquivo `.txt` exportado? → A: Uma afirmação por linha (separadas por `\n`), sem marcadores ou prefixos.
- Q: Como tratar o conteúdo não classificado em caso de erro na fila de processamento? → A: Incluir o conteúdo não classificado parcialmente extraído no payload de erro do WebSocket para que o usuário possa visualizar/baixar o que foi recuperado.
- Q: Os dados não categorizados devem ser exportados no JSON principal de perguntas e respostas? → A: Não, devem ser exportados apenas no novo arquivo .txt.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extração de Fatos e Informações Úteis Não Classificadas (Priority: P1)

Como usuário, desejo que a inteligência artificial analise as conversas e extraia informações úteis, regras de negócio, dados de contato, horários ou preços que não foram estruturados na forma de perguntas e respostas, para que eu possa enriquecer minha base de conhecimento com fatos declarativos.

**Why this priority**: Esta funcionalidade estende a capacidade do extrator, capturando informações declarativas importantes que seriam ignoradas pela filtragem estrita de Perguntas e Respostas.

**Independent Test**: Pode ser testado realizando o upload de uma conversa que contenha afirmações como "Nosso horário de funcionamento é das 8h às 18h de segunda a sexta" ou "A taxa de entrega é R$ 15,00", sem perguntas explícitas anteriores, e verificando se essas afirmações são extraídas na lista de conteúdo não classificado.

**Acceptance Scenarios**:

1. **Given** que o usuário iniciou o processamento de uma conversa com regras e afirmações explícitas, **When** o processamento é concluído, **Then** o sistema exibe os fatos extraídos na aba de resultados sob a seção de Conteúdo Não Classificado / Base de Conhecimento.
2. **Given** um trecho de conversa contendo apenas saudações irrelevantes (como "olá", "tudo bem"), **When** o processamento é concluído, **Then** o sistema não gera itens vazios ou triviais na lista de conteúdo não classificado.

---

### User Story 2 - Exportação de Arquivo TXT Adicional (Priority: P1)

Como usuário, desejo baixar um arquivo `.txt` contendo a lista consolidada das afirmações e conteúdos informativos extraídos das conversas para importá-lo ou registrá-lo diretamente na minha base de dados.

**Why this priority**: A exportação desse conteúdo é a entrega de valor final pedida pelo usuário. Sem a possibilidade de exportar esse arquivo `.txt`, o usuário não consegue alimentar sua base de dados externa facilmente.

**Independent Test**: Pode ser testado clicando no novo botão de exportação da aba de resultados e validando se o arquivo `.txt` baixado contém a lista limpa das informações não classificadas, separadas por quebras de linha.

**Acceptance Scenarios**:

1. **Given** que o processamento gerou 5 itens de conteúdo não classificados, **When** o usuário clica em "Baixar Conteúdo Adicional (TXT)", **Then** o navegador realiza o download de um arquivo `.txt` contendo os 5 itens (afirmações puras, uma por linha, sem marcadores, separadas por `\n`).

---

### User Story 3 - Interface de Visualização Integrada (Priority: P2)

Como usuário, desejo visualizar na tela os conteúdos não classificados extraídos paralelamente às perguntas e respostas de forma organizada, antes de realizar a exportação.

**Why this priority**: Facilita a auditoria visual rápida dos dados pela interface do usuário antes de realizar o download físico.

**Independent Test**: Pode ser verificado abrindo a aba de resultados e certificando-se de que há uma visualização dedicada (ex: lista ou tabela lateral) exibindo as afirmações extraídas.

**Acceptance Scenarios**:

1. **Given** que o processamento foi concluído, **When** o usuário acessa a tela de resultados, **Then** ele vê uma divisão na tela (ex: abas internas ou painéis) para alternar entre a tabela de Perguntas e Respostas e a lista de Conteúdo Não Classificado para Base de Dados.

### Edge Cases

- **Ausência de Conteúdo Adicional (EC-01)**: Se uma conversa contiver apenas perguntas e respostas puras sem informações declarativas extras, a lista de conteúdo não classificado retornará vazia. O sistema deve tratar isso exibindo uma mensagem informativa como "Nenhum conteúdo não classificado encontrado" na seção correspondente, e desabilitar ou ajustar o botão de exportação associado.
- **Duplicidade de Informações nos Chunks (EC-02)**: Se a mesma afirmação declarativa aparecer em múltiplos chunks (ou arquivos), o sistema deve desduplicar essa lista antes de exibir ou exportar, para evitar conteúdo redundante na base de dados final.
- **Erro na Fila de Processamento (EC-03)**: Se ocorrer um erro irrecuperável durante o processamento da fila, o sistema deve retornar o conteúdo não classificado parcialmente extraído até o momento do erro, permitindo ao usuário visualizá-lo e baixá-lo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST atualizar o prompt padrão do sistema (`DEFAULT_SYSTEM_PROMPT_TEXT`) e a lógica de geração de prompts (incluindo prompts customizados, anexando a instrução nos bastidores) para instruir o modelo a extrair, além das perguntas e respostas (`qna_pairs`), uma lista de strings contendo fatos úteis, regras de negócio ou informações relevantes que não estejam no formato P&R mas que sirvam para a base do banco de dados na chave JSON `uncategorized_database_content`.
- **FR-002**: O sistema MUST estender os esquemas do WebSocket (`WSChunkSuccessData`, `WSQueueCompleteData`, `WSQueueErrorData`) para incluir o campo `uncategorized_database_content` (uma lista de strings).
- **FR-003**: O sistema MUST estender o retorno do processo de extração (`extract_qna_from_chunk`) para suportar e coletar tanto os pares de P&R quanto o conteúdo não classificado extraído de cada chunk.
- **FR-004**: O sistema MUST desduplicar o conteúdo não classificado acumulado de todos os chunks após o processamento utilizando correspondência exata de texto (case-insensitive, ignorando espaços em branco nas extremidades).
- **FR-005**: O frontend MUST exibir na tela de resultados a lista de conteúdo não classificado em uma seção ou aba dedicada para fácil visualização pelo usuário.
- **FR-006**: O frontend MUST disponibilizar um botão adicional para download de um único arquivo `.txt` contendo a lista consolidada de todas as informações não classificadas obtidas de todos os arquivos do lote, com nome padrão contendo sufixo identificador (ex: `resultados_base_conhecimento.txt` ou `nao_classificados.txt`).

### Key Entities

- **ConteúdoNãoClassificado (Em Memória)**: Lista de strings contendo as afirmações extraídas de forma autônoma pela IA.
  - Representa fatos úteis, instruções operacionais, preços, contatos ou horários que não seguem a dinâmica direta de pergunta e resposta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O fatiador e consolidador devem processar e retornar a lista de conteúdos não classificados sem introduzir um aumento superior a 15% no tempo total de processamento em comparação com a execução padrão do mesmo lote que realiza apenas a extração exclusiva de Q&A.
- **SC-002**: A exportação do arquivo `.txt` adicional deve ser concluída em menos de 100ms a partir do clique no botão.
- **SC-003**: A exportação do conteúdo não classificado consolidado deve ser feita apenas no arquivo .txt adicional, não devendo ser incluído no arquivo JSON principal de perguntas e respostas.
- **SC-004**: 100% dos registros extraídos para o conteúdo não classificado devem respeitar o idioma definido nas configurações de idioma do prompt configurado.

## Assumptions

- O modelo LLM selecionado (gpt-4o-mini ou gpt-4o) tem capacidade cognitiva para separar corretamente o que é pergunta e resposta do que são afirmações factuais úteis.
- O formato final de importação desejado pelo usuário para essa base adicional de texto é compatível com uma lista de frases úteis separadas por quebras de linha em formato `.txt`.
