import re
from typing import List, Optional, Tuple
from src.models.exact_qa import RawMessage

# Regex patterns for common WhatsApp export formats:
HEADER_REGEXES = [
    re.compile(r'^\[(\d{1,4}[/\.-]\d{1,4}[/\.-]\d{1,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s*([^:]+):\s*(.*)$'),
    re.compile(r'^(\d{1,4}[/\.-]\d{1,4}[/\.-]\d{1,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*-\s*([^:]+):\s*(.*)$'),
    re.compile(r'^\[(\d{1,4}[/\.-]\d{1,4}[/\.-]\d{1,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s*(.*)$'),
    re.compile(r'^(\d{1,4}[/\.-]\d{1,4}[/\.-]\d{1,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*-\s*(.*)$'),
]


def _match_header(line: str) -> Optional[Tuple[Optional[str], Optional[str], str]]:
    """Tenta casar uma linha com os padrões conhecidos de cabeçalho do WhatsApp."""
    for idx, pattern in enumerate(HEADER_REGEXES):
        match = pattern.match(line)
        if match:
            groups = match.groups()
            if idx in (0, 1):
                timestamp, sender, text = groups[0], groups[1], groups[2]
                return timestamp.strip(), sender.strip(), text
            else:
                timestamp, text = groups[0], groups[1]
                if ":" in text:
                    sender, body = text.split(":", 1)
                    return timestamp.strip(), sender.strip(), body.strip()
                return timestamp.strip(), None, text.strip()
    return None


def parse_whatsapp_chat(raw_text: str) -> List[RawMessage]:
    """
    Processa o texto bruto da conversa do WhatsApp, dividindo em mensagens individuais.
    Se o arquivo contiver cabeçalhos WhatsApp padrão (timestamps), divide por cabeçalho
    e agrupa linhas seguintes. Caso contrário, divide por linha individual.
    Atribui IDs sequenciais únicos no formato MSG-XXXX.
    """
    lines = raw_text.splitlines()
    if not lines:
        return []

    # Verifica se há pelo menos um cabeçalho WhatsApp padrão nas primeiras linhas
    has_headers = any(_match_header(line) is not None for line in lines[:50])

    messages: List[RawMessage] = []
    msg_counter = 1

    if has_headers:
        current_timestamp: Optional[str] = None
        current_sender: Optional[str] = None
        current_lines: List[str] = []

        def flush_current_msg():
            nonlocal msg_counter, current_lines, current_timestamp, current_sender
            if current_lines:
                content = "\n".join(current_lines)
                msg_id = f"MSG-{msg_counter:04d}"
                messages.append(RawMessage(
                    id=msg_id,
                    timestamp=current_timestamp,
                    sender=current_sender,
                    content=content
                ))
                msg_counter += 1
                current_lines = []
                current_timestamp = None
                current_sender = None

        for line in lines:
            header_match = _match_header(line)
            if header_match:
                flush_current_msg()
                ts, sender, text = header_match
                current_timestamp = ts
                current_sender = sender
                current_lines.append(text)
            else:
                if current_lines:
                    current_lines.append(line)
                elif line.strip():
                    current_lines.append(line)

        flush_current_msg()
    else:
        # Sem cabeçalhos padrão: trata cada linha não vazia como mensagem separada
        for line in lines:
            if line.strip():
                msg_id = f"MSG-{msg_counter:04d}"
                messages.append(RawMessage(
                    id=msg_id,
                    timestamp=None,
                    sender=None,
                    content=line.strip()
                ))
                msg_counter += 1

    return messages
