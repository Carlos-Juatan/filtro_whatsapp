import pytest
import io
import json
from services.qna_parser_factory import QnAParserFactory, InputFormat
from models.merger import QnAPair

def test_json_parser_valid():
    parser = QnAParserFactory.get_parser(InputFormat.json)
    json_data = """
    {
      "qna_pairs": [
        {
          "perguntaPadronizada": "Test Q",
          "respostaConsolidada": "Test A",
          "frequencia": 2,
          "metadata": "meta1",
          "category": "cat1"
        }
      ]
    }
    """
    file = io.StringIO(json_data)
    result = parser.parse(file)
    assert len(result) == 1
    assert result[0].perguntaPadronizada == "Test Q"
    assert result[0].respostaConsolidada == "Test A"
    assert result[0].frequencia == 2
    assert result[0].metadata == "meta1"

def test_json_parser_list_root():
    parser = QnAParserFactory.get_parser(InputFormat.json)
    json_data = """
    [
      {
        "perguntaPadronizada": "Test Q2",
        "respostaConsolidada": "Test A2",
        "frequencia": 1
      }
    ]
    """
    file = io.StringIO(json_data)
    result = parser.parse(file)
    assert len(result) == 1
    assert result[0].perguntaPadronizada == "Test Q2"

def test_json_parser_malformed_skips_invalid():
    parser = QnAParserFactory.get_parser(InputFormat.json)
    json_data = """
    {
      "qna_pairs": [
        {
          "perguntaPadronizada": "Test Q1",
          "respostaConsolidada": "Test A1",
          "frequencia": 2
        },
        {
          "perguntaPadronizada": "Missing fields"
        }
      ]
    }
    """
    file = io.StringIO(json_data)
    result = parser.parse(file)
    assert len(result) == 1
    assert result[0].perguntaPadronizada == "Test Q1"

def test_json_parser_invalid_json():
    parser = QnAParserFactory.get_parser(InputFormat.json)
    json_data = """{ "malformed": """
    file = io.StringIO(json_data)
    with pytest.raises(ValueError):
        parser.parse(file)

def test_txt_parser_valid():
    parser = QnAParserFactory.get_parser(InputFormat.txt)
    txt_data = """[Metadata Example] (Frequência: 3)
Q: What is this?
A: This is a test.

Q: Second Q
A: Second A
"""
    file = io.StringIO(txt_data)
    result = parser.parse(file)
    assert len(result) == 2
    assert result[0].perguntaPadronizada == "What is this?"
    assert result[0].respostaConsolidada == "This is a test."
    assert result[0].frequencia == 3
    assert result[0].metadata == "Metadata Example"
    
    assert result[1].perguntaPadronizada == "Second Q"
    assert result[1].respostaConsolidada == "Second A"
    assert result[1].frequencia == 1
    assert result[1].metadata is None

def test_txt_parser_malformed():
    parser = QnAParserFactory.get_parser(InputFormat.txt)
    txt_data = """Just some random text
that doesn't match our format.
Q: Only Q
"""
    file = io.StringIO(txt_data)
    result = parser.parse(file)
    assert len(result) == 0

def test_txt_parser_multiline():
    parser = QnAParserFactory.get_parser(InputFormat.txt)
    txt_data = """Q: Multiline Q
still part of Q
A: Multiline A
still part of A
"""
    file = io.StringIO(txt_data)
    result = parser.parse(file)
    assert len(result) == 1
    assert result[0].perguntaPadronizada == "Multiline Q\nstill part of Q"
    assert result[0].respostaConsolidada == "Multiline A\nstill part of A"
