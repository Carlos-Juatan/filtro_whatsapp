import pytest
from src.services.exact_parser import parse_whatsapp_chat


def test_parse_simple_chat():
    chat_text = """[10/05/2023, 14:30:15] Joao: Ola, qual o valor da consulta?
[10/05/2023, 14:31:00] Maria: Boa tarde! A consulta custa R$ 150,00.
"""
    messages = parse_whatsapp_chat(chat_text)
    assert len(messages) == 2
    assert messages[0].id == "MSG-0001"
    assert messages[0].sender == "Joao"
    assert messages[0].content == "Ola, qual o valor da consulta?"
    assert messages[1].id == "MSG-0002"
    assert messages[1].sender == "Maria"
    assert messages[1].content == "Boa tarde! A consulta custa R$ 150,00."


def test_parse_multiline_messages_and_emojis():
    chat_text = """10/05/2023, 14:30 - Dr. Carlos: Ola! Como esta o paciente?
Ele teve febre? 🤒
10/05/2023, 14:32 - Tutora: Ola Doutor!
Sim, teve febre ontem a noite.
Temperatura 39.2 C.
"""
    messages = parse_whatsapp_chat(chat_text)
    assert len(messages) == 2
    assert messages[0].id == "MSG-0001"
    assert messages[0].sender == "Dr. Carlos"
    assert messages[0].content == "Ola! Como esta o paciente?\nEle teve febre? 🤒"
    assert messages[1].id == "MSG-0002"
    assert messages[1].sender == "Tutora"
    assert messages[1].content == "Ola Doutor!\nSim, teve febre ontem a noite.\nTemperatura 39.2 C."


def test_parse_chat_without_header():
    chat_text = """Ola, gostaria de agendar um banho.
Claro! Qual o nome do pet?
"""
    messages = parse_whatsapp_chat(chat_text)
    assert len(messages) == 2
    assert messages[0].id == "MSG-0001"
    assert messages[0].content == "Ola, gostaria de agendar um banho."
    assert messages[1].id == "MSG-0002"
    assert messages[1].content == "Claro! Qual o nome do pet?"
