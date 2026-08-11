# Data Model: Extração Exata de Perguntas e Respostas do WhatsApp

## Entities

### 1. RawMessage (Mensagem Bruta)
Representa uma mensagem extraída do arquivo `.txt` do WhatsApp pelo parser determinístico.

- `id`: `str` (obrigatório, ex: `"MSG-0001"`) - Identificador único sequencial.
- `timestamp`: `Optional[str]` - Data/hora extraída da linha de cabeçalho da mensagem (se presente).
- `sender`: `Optional[str]` - Nome/número do remetente (se presente).
- `content`: `str` (obrigatório) - Texto bruto e intacto da mensagem (incluindo emojis, quebras de linha e erros de digitação).

### 2. LLMQAPairMapping (Mapeamento de IDs da IA)
Estrutura de resposta retornada pela LLM após análise das mensagens.

- `question_id`: `str` (obrigatório) - ID da mensagem identificada como pergunta.
- `answer_id`: `str` (obrigatório) - ID da mensagem identificada como resposta correspondente.

### 3. ExactQAPair (Par Extraído Exato)
Objeto final gerado pela reconstrução exata através de lookup nos IDs.

- `id`: `str` (obrigatório) - Identificador do par de Q&A.
- `question_id`: `str` (obrigatório) - ID da mensagem de pergunta original.
- `question_text`: `str` (obrigatório) - Texto 100% idêntico à mensagem bruta original da pergunta.
- `answer_id`: `str` (obrigatório) - ID da mensagem de resposta original.
- `answer_text`: `str` (obrigatório) - Texto 100% idêntico à mensagem bruta original da resposta.
- `metadata`: `dict` - Informações adicionais (ex: remetente da pergunta, remetente da resposta, timestamps).

### 4. ExtractionResult (Resultado Completo da Sessão)
Container de resultados de um arquivo processado.

- `filename`: `str` - Nome do arquivo carregado.
- `total_messages_parsed`: `int` - Total de mensagens identificadas pelo parser.
- `total_pairs_extracted`: `int` - Total de pares Pergunta/Resposta válidos reconstruídos.
- `pairs`: `List[ExactQAPair]` - Lista dos pares reconstruídos.
