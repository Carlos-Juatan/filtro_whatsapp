# Research Document: Extração Exata de P&R no WhatsApp com Chunking e Robustez

## 1. Janelamento (Chunking) com Overlap e Deduplicação

### Decisão
Implementar o janelamento da lista de mensagens `RawMessage` em lotes de 100 mensagens por chunk com um overlap de 20 mensagens consecutivas.

### Racional
Conversas do WhatsApp podem ser extensas e enviar milhares de mensagens de uma única vez para a LLM causa estouro de context window, alto custo e respostas JSON incompletas/truncadas. Ao dividir em lotes de 100 mensagens:
- A LLM foca em poucas mensagens por chamada, garantindo alta precisão na identificação dos pares.
- O overlap de 20 mensagens evita que uma pergunta no final de um lote perca sua resposta que se encontra nas primeiras linhas do lote seguinte.
- Mapeamentos duplicados `(question_id, answer_id)` gerados pela área de sobreposição são deduplicados deterministicamente no backend por um `set` de tuplas antes da reconstrução final.

---

## 2. Filtragem Prévia de Cortesia e Placeholders (Mídia/Omitidos)

### Decisão
Ignorar mensagens de cortesia sem dúvida expressa (ex: "Bom dia, envio MSG para pedir uma informação...") e descartar mensagens de mídia omitida ou arquivos não revelados (`<Ficheiro não revelado>`, `<Mídia omitida>`, `<Media omitted>`) tanto como candidatos a pergunta quanto como resposta.

### Racional
- Reduz o ruído nos chunks enviados à LLM, evitando falsos positivos.
- Placeholders de arquivos não possuem conteúdo útil legível de pergunta ou resposta para a finalidade da ferramenta.
- A instrução é reforçada diretamente no System Prompt da LLM e opcionalmente pré-filtrada se o conteúdo corresponder estritamente a expressões de mídia conhecida.

---

## 3. Resiliência contra JSON Malformado e Truncamento (`max_tokens` + Retries)

### Decisão
Configurar `max_tokens=4000` na chamada da API da OpenAI (`AsyncOpenAI`) e envelopar a execução com um mecanismo de retry automático (até 2 tentativas com backoff simples) capturando exceções `json.JSONDecodeError`.

### Racional
O erro `Unterminated string starting at line ...` ocorre quando a LLM atinge o limite de tokens de saída ou se a transmissão do payload JSON for interrompida, gerando uma string JSON truncada.
- Definir `max_tokens=4000` dá margem ampla para retornos de até centenas de pares por chunk de 100 mensagens.
- O retry automático resolve oscilações esporádicas de geração do modelo.
