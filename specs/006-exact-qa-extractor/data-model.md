# Data Model: Extração Exata de P&R no WhatsApp

## Entidades Principais

### RawMessage
Representa uma mensagem bruta indexada pelo parser determinístico.
- `id` (str, obrigatório): Identificador único no formato `MSG-XXXX` (ex: `MSG-0001`).
- `timestamp` (str, opcional): Data/hora extraída do cabeçalho da mensagem.
- `sender` (str, opcional): Autor/remetente da mensagem.
- `content` (str, obrigatório): Conteúdo exato e intocado da mensagem (preservando pontuação, emojis e quebras de linha).

### ChunkConfig
Parâmetros de configuração para o fatiamento de mensagens.
- `chunk_size` (int, padrão = 100): Quantidade de mensagens por lote enviado à LLM.
- `overlap` (int, padrão = 20): Mensagens de sobreposição entre chunks adjacentes.

### LLMQAPairMapping
Mapeamento retornado pela LLM para cada par de P&R.
- `question_id` (str, obrigatório): ID da mensagem correspondente à pergunta (ex: `MSG-0010`).
- `answer_id` (str, obrigatório): ID da mensagem correspondente à resposta (ex: `MSG-0012`).

### ExactQAPair
Representação final do par P&R reconstruído com 100% de fidelidade textual.
- `id` (str, obrigatório): Identificador do par no resultado (ex: `PAIR-0001`).
- `question_id` (str, obrigatório): ID da pergunta original.
- `question_text` (str, obrigatório): Texto da pergunta obtido por lookup direto em `RawMessage`.
- `answer_id` (str, obrigatório): ID da resposta original.
- `answer_text` (str, obrigatório): Texto da resposta obtido por lookup direto em `RawMessage`.
- `metadata` (dict): Informações adicionais (timestamps e senders de ambos).

### ExtractionResult
Objeto de saída contendo a consolidação dos pares reconstruídos.
- `filename` (str): Nome do arquivo exportado do WhatsApp.
- `total_messages_parsed` (int): Total de mensagens indexadas pelo parser.
- `total_pairs_extracted` (int): Total de pares reconstruídos com sucesso.
- `pairs` (List[ExactQAPair]): Lista dos pares de pergunta e resposta exatos.
