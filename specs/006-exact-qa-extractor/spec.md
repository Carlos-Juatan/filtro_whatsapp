# Feature Specification: Extração Exata de Perguntas e Respostas do WhatsApp

**Feature Branch**: `006-exact-qa-extractor`  
**Created**: 2026-08-11  
**Status**: Draft  
**Input**: User description: "nova ferramenta de extração de pergutnas e respostas do whatsapp, porém, essa ferramenta deve extrair exatamente como está escrito na conversa, identificar perguntas e extrair essa pergunta sem modificar o conteúdo da pergunta e extrair a resposta correspondente também sem modificar o conteúdo da resposta."

## Clarifications

### Session 2026-08-11
- Q: Como o sistema deve tratar perguntas que não possuem uma resposta correspondente no chat? → A: Ignorar perguntas sem resposta e não incluir no resultado final.
- Q: Como tratar saudações sem dúvida expressa e mensagens de mídia/placeholder como <Ficheiro não revelado>? → A: Ignorar mensagens com apenas saudações sem dúvida expressa e descartar conteúdos omitidos/placeholders (<Ficheiro não revelado>, <Mídia omitida>) tanto como pergunta quanto como resposta.
- Q: Como deve ser realizada a divisão da conversa em chunks para processamento pela LLM? → A: Dividir em lotes fixos de 100 mensagens por chunk com sobreposição (overlap) de 20 mensagens consecutivas entre chunks, deduplicando pares encontrados.
- Q: Como prevenir erros de sintaxe e retornos incompletos da LLM (ex: Unterminated string)? → A: Configurar max_tokens adequado (ex: 4000), validar integridade da resposta JSON retornada pela LLM e implementar mecanismo de retry automático em caso de exceção de parse JSON.




## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extração Exata de Pares Pergunta/Resposta (Priority: P1)

Como usuário analisando exportações do WhatsApp (.txt), eu quero carregar um arquivo de conversa e extrair automaticamente pares de (Pergunta, Resposta) mantendo rigorosamente o texto bruto original de cada mensagem, para que o conteúdo original não seja alterado ou parafraseado durante o processo.

**Why this priority**: É o valor central da ferramenta. A fidelidade textual do conteúdo original é o requisito primário exigido pelo usuário.

**Independent Test**: Pode ser testado enviando um arquivo .txt de conversa do WhatsApp contendo perguntas e respostas conhecidas, verificando se as mensagens retornadas nos pares coincidem 100% caractere por caractere com o arquivo original.

**Acceptance Scenarios**:

1. **Given** um arquivo .txt exportado do WhatsApp com mensagens numeradas/indexadas deterministicamente, **When** a ferramenta processa a classificação via IA e a reconstrução exata, **Then** o resultado exibe pares de pergunta e resposta onde o texto de cada mensagem é idêntico ao texto do .txt original.
2. **Given** uma pergunta no WhatsApp que possui formatação especial, emojis ou erros de digitação, **When** extraída pela ferramenta, **Then** todos os caracteres, emojis e erros de digitação originais são mantidos intactos tanto na pergunta quanto na resposta.

---

### User Story 2 - Indexação Determinística das Mensagens (Priority: P2)

Como sistema, eu preciso dividir as mensagens do arquivo .txt do WhatsApp e atribuir um identificador único sequencial para cada mensagem, para que a IA possa trabalhar apenas com referências de IDs sem manipular o texto das mensagens.

**Why this priority**: A separação por IDs garante a desacoplagem entre a inteligência de classificação (LLM) e o conteúdo bruto, viabilizando a reconstrução exata.

**Independent Test**: Pode ser testado isoladamente executando o parser em um .txt do WhatsApp e verificando a estrutura de mensagens e a geração de IDs únicos para cada linha/bloco de mensagem.

**Acceptance Scenarios**:

1. **Given** um arquivo .txt de conversa, **When** o parser determinístico é executado, **Then** cada mensagem da conversa recebe um ID único indexado e seu conteúdo textual bruto associado.

---

### User Story 3 - Mapeamento e Reconstrução por IDs (Priority: P3)

Como usuário, eu quero visualizar os pares identificados organizados em uma interface clara de visualização ou exportação, para que eu possa consumir os dados extraídos sem perda de contexto.

**Why this priority**: Permite ao usuário final consultar e exportar os resultados reconstruídos de forma estruturada.

**Independent Test**: Testar a junção dos IDs de pares de (Pergunta -> Resposta) retornados pela IA com o repositório de mensagens originais, garantindo que o objeto final de resultado seja construído corretamente.

**Acceptance Scenarios**:

1. **Given** a lista de mapeamento de IDs `(ID_pergunta -> ID_resposta)`, **When** o módulo de reconstrução exata é acionado, **Then** ele busca o texto bruto correspondente a cada ID e gera o par final.

---

### Edge Cases

- O que acontece quando uma pergunta não possui resposta clara na conversa do WhatsApp? O sistema ignora perguntas sem resposta e não as inclui no resultado final.
- Como o sistema lida com conversas que contêm mensagens de mídia (ex: `<Mídia omitida>`, fotos, áudios)? As mensagens de mídia continuam recebendo ID, porém se forem irrelevantes como pergunta/resposta, não serão pareadas.
- O que acontece com mensagens de várias linhas (quebras de linha dentro da mesma mensagem de chat)? O parser determinístico deve identificar corretamente o início e fim de cada mensagem para não quebrar mensagens em IDs errados.rretamente o início e fim de cada mensagem para não quebrar mensagens em IDs errados.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE realizar o parsing determinístico do arquivo `.txt` exportado do WhatsApp, dividindo-o em mensagens individuais e atribuindo um ID único para cada uma.
- **FR-002**: O sistema DEVE enviar o bloco indexado de mensagens (IDs e conteúdo) para a IA (LLM) para identificar o mapeamento de pares `(ID_pergunta -> ID_resposta)`.
- **FR-003**: A IA DEVE retornar exclusivamente os identificadores (IDs) correspondentes às perguntas e às suas respectivas respostas.
- **FR-004**: O sistema DEVE reconstruir os pares de Pergunta e Resposta copiando estritamente o texto BRUTO original armazenado no parser a partir dos IDs retornados, sem modificar nenhum caractere, pontuação ou formatação.
- **FR-005**: O sistema DEVE permitir a visualização e exportação dos pares extraídos mantendo a fidelidade 100% com o texto original.

### Key Entities

- **Mensagem Bruta**: Representa uma mensagem individual extraída do arquivo .txt (atributos: `id`, `timestamp`, `autor`, `texto_bruto`).
- **Mapeamento de Par (IA)**: Representa a associação detectada pelo modelo LLM (atributos: `id_pergunta`, `id_resposta`).
- **Par Extraído Exato**: O resultado final reconstruído (atributos: `id_pergunta`, `texto_pergunta_bruto`, `id_resposta`, `texto_resposta_bruto`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% de correspondência textual caractere a caractere entre as perguntas/respostas extraídas finais e o conteúdo bruto correspondente do arquivo `.txt` do WhatsApp.
- **SC-002**: Zero alucinação ou alteração sintática/gramatical na pergunta ou resposta final gerada pela aplicação (dado que a IA retorna apenas IDs).
- **SC-003**: Processamento bem-sucedido de arquivos de conversa do WhatsApp com até 10.000 mensagens sem corrupção na indexação de IDs.

## Assumptions

- O formato do arquivo de entrada é a exportação padrão de conversa de texto (`.txt`) do WhatsApp.
- A IA utilizada é capaz de compreender o contexto da conversa indexada por IDs e responder estritamente com o formato de IDs especificado.
- Perguntas sem respostas na conversa serão ignoradas ou não formarão pares válidos na saída final.
