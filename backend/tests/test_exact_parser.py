"""
Tests for exact_parser.py

Covers (T009):
  - Standard WhatsApp header formats (bracket and dash styles)
  - Multiline messages with emojis
  - Courtesy messages without questions (parsed normally, not filtered)
  - Media/placeholder messages labeled with is_placeholder=True (T008)
  - Chat without headers (one-line-per-message mode)
  - Sequential ID assignment
  - Empty input
"""

import pytest
from src.services.exact_parser import parse_whatsapp_chat, _is_placeholder


# ---------------------------------------------------------------------------
# _is_placeholder helper
# ---------------------------------------------------------------------------

class TestIsPlaceholder:
    def test_media_omitted_pt(self):
        assert _is_placeholder("<Mídia omitida>") is True

    def test_media_omitted_en(self):
        assert _is_placeholder("<Media omitted>") is True

    def test_file_not_revealed(self):
        assert _is_placeholder("<Ficheiro não revelado>") is True

    def test_case_insensitive(self):
        assert _is_placeholder("<MÍDIA OMITIDA>") is True

    def test_with_extra_whitespace(self):
        assert _is_placeholder("  <mídia omitida>  ") is True

    def test_regular_message_is_not_placeholder(self):
        assert _is_placeholder("Qual o valor da consulta?") is False

    def test_empty_string(self):
        assert _is_placeholder("") is False


# ---------------------------------------------------------------------------
# Standard WhatsApp header parsing
# ---------------------------------------------------------------------------

class TestParseSimpleChat:
    def test_bracket_format_two_messages(self):
        chat_text = (
            "[10/05/2023, 14:30:15] Joao: Ola, qual o valor da consulta?\n"
            "[10/05/2023, 14:31:00] Maria: Boa tarde! A consulta custa R$ 150,00.\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2
        assert messages[0].id == "MSG-0001"
        assert messages[0].sender == "Joao"
        assert messages[0].content == "Ola, qual o valor da consulta?"
        assert messages[1].id == "MSG-0002"
        assert messages[1].sender == "Maria"
        assert messages[1].content == "Boa tarde! A consulta custa R$ 150,00."

    def test_dash_format(self):
        chat_text = (
            "10/05/2023, 14:30 - Dr. Carlos: Ola!\n"
            "10/05/2023, 14:32 - Tutora: Ola Doutor!\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2
        assert messages[0].sender == "Dr. Carlos"
        assert messages[1].sender == "Tutora"

    def test_sequential_ids(self):
        chat_text = (
            "[10/05/2023, 10:00] A: Um\n"
            "[10/05/2023, 10:01] B: Dois\n"
            "[10/05/2023, 10:02] A: Três\n"
        )
        msgs = parse_whatsapp_chat(chat_text)
        assert [m.id for m in msgs] == ["MSG-0001", "MSG-0002", "MSG-0003"]

    def test_empty_input(self):
        assert parse_whatsapp_chat("") == []

    def test_whitespace_only_input(self):
        assert parse_whatsapp_chat("   \n  \n") == []


# ---------------------------------------------------------------------------
# Multiline messages with emojis (T009)
# ---------------------------------------------------------------------------

class TestMultilineAndEmojis:
    def test_multiline_message_with_emoji(self):
        chat_text = (
            "10/05/2023, 14:30 - Dr. Carlos: Ola! Como esta o paciente?\n"
            "Ele teve febre? 🤒\n"
            "10/05/2023, 14:32 - Tutora: Ola Doutor!\n"
            "Sim, teve febre ontem a noite.\n"
            "Temperatura 39.2 C.\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2
        assert messages[0].content == "Ola! Como esta o paciente?\nEle teve febre? 🤒"
        assert messages[1].content == "Ola Doutor!\nSim, teve febre ontem a noite.\nTemperatura 39.2 C."

    def test_emoji_only_message(self):
        chat_text = (
            "[01/01/2024, 09:00] Pet Owner: 🐾❤️🐕\n"
            "[01/01/2024, 09:01] Clinic: Que fofo! 😊\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2
        assert messages[0].content == "🐾❤️🐕"
        assert messages[0].is_placeholder is False

    def test_unicode_and_accents_preserved(self):
        chat_text = "[01/01/2024, 09:00] Ana: Meu cão está com dor. Qual o próximo passo?\n"
        messages = parse_whatsapp_chat(chat_text)
        assert messages[0].content == "Meu cão está com dor. Qual o próximo passo?"


# ---------------------------------------------------------------------------
# Courtesy messages without questions (T009)
# ---------------------------------------------------------------------------

class TestCourtesyMessages:
    def test_greeting_message_parsed_but_not_filtered(self):
        """
        Courtesy messages are included in the index (not removed).
        The LLM/system prompt is responsible for ignoring them during classification.
        """
        chat_text = (
            "[10/05/2023, 08:00] Cliente: Bom dia!\n"
            "[10/05/2023, 08:01] Clinica: Bom dia! Como posso ajudar?\n"
            "[10/05/2023, 08:02] Cliente: Qual o horário de funcionamento?\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        # All 3 messages present — parser is non-filtering
        assert len(messages) == 3
        assert messages[0].content == "Bom dia!"
        assert messages[0].is_placeholder is False

    def test_thank_you_message_not_placeholder(self):
        chat_text = "[10/05/2023, 10:00] Joao: Muito obrigado!\n"
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 1
        assert messages[0].is_placeholder is False


# ---------------------------------------------------------------------------
# Placeholder / media messages (T008 via T009)
# ---------------------------------------------------------------------------

class TestPlaceholderMessages:
    def test_media_omitida_labeled(self):
        chat_text = (
            "[10/05/2023, 14:00] Joao: <Mídia omitida>\n"
            "[10/05/2023, 14:01] Clinica: Recebi a imagem!\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2
        assert messages[0].is_placeholder is True
        assert messages[1].is_placeholder is False

    def test_ficheiro_placeholder_labeled(self):
        chat_text = (
            "[10/05/2023, 14:00] Joao: <Ficheiro não revelado>\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 1
        assert messages[0].is_placeholder is True

    def test_media_omitted_en_labeled(self):
        chat_text = (
            "[10/05/2023, 14:00] Joao: <Media omitted>\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert messages[0].is_placeholder is True

    def test_placeholder_ids_not_skipped_in_index(self):
        """Placeholders must still receive sequential IDs to preserve full message index."""
        chat_text = (
            "[10/05/2023, 14:00] A: Pergunta real?\n"
            "[10/05/2023, 14:01] B: <Mídia omitida>\n"
            "[10/05/2023, 14:02] A: Outra pergunta?\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 3
        assert [m.id for m in messages] == ["MSG-0001", "MSG-0002", "MSG-0003"]
        assert messages[1].is_placeholder is True


# ---------------------------------------------------------------------------
# Chat without WhatsApp headers
# ---------------------------------------------------------------------------

class TestChatWithoutHeaders:
    def test_simple_lines(self):
        chat_text = (
            "Ola, gostaria de agendar um banho.\n"
            "Claro! Qual o nome do pet?\n"
        )
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2
        assert messages[0].id == "MSG-0001"
        assert messages[0].content == "Ola, gostaria de agendar um banho."
        assert messages[1].id == "MSG-0002"
        assert messages[1].content == "Claro! Qual o nome do pet?"

    def test_blank_lines_ignored(self):
        chat_text = "\nMensagem 1\n\nMensagem 2\n\n"
        messages = parse_whatsapp_chat(chat_text)
        assert len(messages) == 2

    def test_no_header_placeholder_labeled(self):
        chat_text = "<Media omitted>\nResposta normal\n"
        messages = parse_whatsapp_chat(chat_text)
        assert messages[0].is_placeholder is True
        assert messages[1].is_placeholder is False
