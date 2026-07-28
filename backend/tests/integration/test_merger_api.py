"""
Integration tests for the /api/merger/consolidate endpoint.

T024: Updated integration tests with AI fallback awareness
T025: SC-001 parametric zero-duplicate verification
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import app

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _no_key_patch():
    """Patch key storage to return no keys so AI is skipped (deterministic tests)."""
    return patch("src.services.key_storage.KeyStorageService.get_all", return_value=[])


# ──────────────────────────────────────────────────────────────────────────────
# T024: Updated API integration tests
# ──────────────────────────────────────────────────────────────────────────────

def test_consolidate_endpoint_json():
    """POST /consolidate with a JSON file returns a valid MergeJobResult."""
    json_content = b'{"qna_pairs": [{"perguntaPadronizada": "Q1?", "respostaConsolidada": "A1", "frequencia": 1}]}'

    with _no_key_patch():
        response = client.post(
            "/api/merger/consolidate",
            data={"input_format": "json"},
            files=[("files", ("test.json", json_content, "application/json"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_files_processed"] == 1
    assert data["total_qna_extracted"] == 1
    assert data["total_qna_merged"] == 1
    assert len(data["qna_pairs"]) == 1
    assert data["qna_pairs"][0]["perguntaPadronizada"] == "Q1?"
    assert data["json_output_filename"] is not None
    assert data["txt_output_filename"] is not None
    # AI-skip warning should be present since no key was configured
    assert any("ignorada" in w.lower() or "algorítmica" in w.lower() for w in data["warnings"])


def test_consolidate_endpoint_txt():
    """POST /consolidate with a TXT file returns a valid MergeJobResult."""
    txt_content = b"[meta] (Frequencia: 1)\nQ: Q1?\nA: A1"

    with _no_key_patch():
        response = client.post(
            "/api/merger/consolidate",
            data={"input_format": "txt"},
            files=[("files", ("test.txt", txt_content, "text/plain"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_files_processed"] == 1
    assert data["total_qna_extracted"] == 1
    assert data["total_qna_merged"] == 1
    assert len(data["qna_pairs"]) == 1
    assert data["qna_pairs"][0]["perguntaPadronizada"] == "Q1?"


def test_download_endpoint():
    """GET /download/{filename} must return the previously generated file."""
    json_content = b'{"qna_pairs": [{"perguntaPadronizada": "Q2", "respostaConsolidada": "A2", "frequencia": 1}]}'

    with _no_key_patch():
        response = client.post(
            "/api/merger/consolidate",
            data={"input_format": "json"},
            files=[("files", ("test2.json", json_content, "application/json"))],
        )
    assert response.status_code == 200
    data = response.json()
    filename = data["json_output_filename"]

    dl_response = client.get(f"/api/merger/download/{filename}")
    assert dl_response.status_code == 200
    assert "Q2" in dl_response.text


def test_consolidate_endpoint_with_ai_warning_in_response():
    """When no key is configured, response.warnings must contain the AI-skip message."""
    json_content = b'{"qna_pairs": [{"perguntaPadronizada": "Pergunta A?", "respostaConsolidada": "Resposta A.", "frequencia": 1}]}'

    with _no_key_patch():
        response = client.post(
            "/api/merger/consolidate",
            data={"input_format": "json"},
            files=[("files", ("warn_test.json", json_content, "application/json"))],
        )

    assert response.status_code == 200
    warnings = response.json()["warnings"]
    assert any("nenhuma" in w.lower() or "algorítmica" in w.lower() for w in warnings), (
        "Expected AI-skip warning in response.warnings when no key is configured."
    )


def test_consolidate_merges_duplicate_questions():
    """Duplicate questions in the same batch must be merged into a single entry."""
    json_content = json.dumps({
        "qna_pairs": [
            {"perguntaPadronizada": "Como funciona?", "respostaConsolidada": "Funciona assim.", "frequencia": 1},
            {"perguntaPadronizada": "como funciona?", "respostaConsolidada": "Funciona de outro jeito.", "frequencia": 2},
        ]
    }).encode()

    with _no_key_patch():
        response = client.post(
            "/api/merger/consolidate",
            data={"input_format": "json"},
            files=[("files", ("dup_test.json", json_content, "application/json"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_qna_extracted"] == 2
    assert data["total_qna_merged"] == 1, "Duplicate questions must be merged into one."
    assert data["qna_pairs"][0]["frequencia"] == 3, "Frequencies must be summed."


# ──────────────────────────────────────────────────────────────────────────────
# T025: SC-001 — Zero-duplicate parametric verification
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "scenario_name,qna_input",
    [
        (
            "exact_duplicates",
            [
                {"perguntaPadronizada": "Qual é o preço?", "respostaConsolidada": "R$ 100.", "frequencia": 1},
                {"perguntaPadronizada": "Qual é o preço?", "respostaConsolidada": "O preço é R$ 100,00.", "frequencia": 3},
                {"perguntaPadronizada": "Como faço para cancelar?", "respostaConsolidada": "Cancele pelo app.", "frequencia": 2},
            ],
        ),
        (
            "case_and_punctuation_duplicates",
            [
                {"perguntaPadronizada": "O serviço funciona?", "respostaConsolidada": "Sim!", "frequencia": 1},
                {"perguntaPadronizada": "o serviço funciona", "respostaConsolidada": "Sim, funciona.", "frequencia": 2},
                {"perguntaPadronizada": "O serviço funciona?!", "respostaConsolidada": "Funciona perfeitamente.", "frequencia": 1},
                {"perguntaPadronizada": "Qual o horário?", "respostaConsolidada": "Das 8h às 18h.", "frequencia": 5},
            ],
        ),
        (
            "no_duplicates_unique",
            [
                {"perguntaPadronizada": "Pergunta Alpha?", "respostaConsolidada": "Resposta Alpha.", "frequencia": 1},
                {"perguntaPadronizada": "Pergunta Beta?", "respostaConsolidada": "Resposta Beta.", "frequencia": 1},
                {"perguntaPadronizada": "Pergunta Gamma?", "respostaConsolidada": "Resposta Gamma.", "frequencia": 1},
            ],
        ),
        (
            "mixed_languages_no_cross_match",
            [
                {"perguntaPadronizada": "What is the price?", "respostaConsolidada": "It's $100.", "frequencia": 1},
                {"perguntaPadronizada": "Qual é o preço?", "respostaConsolidada": "R$ 100.", "frequencia": 2},
            ],
        ),
    ],
)
def test_sc001_zero_duplicate_pergunta_padronizada_after_consolidation(
    scenario_name: str, qna_input: list
):
    """
    SC-001: After a full consolidation run, the output must contain
    ZERO duplicate `perguntaPadronizada` values.

    This is the primary acceptance criterion for the Q&A merger feature.
    """
    payload = json.dumps({"qna_pairs": qna_input}).encode()

    with _no_key_patch():
        response = client.post(
            "/api/merger/consolidate",
            data={"input_format": "json"},
            files=[("files", (f"{scenario_name}.json", payload, "application/json"))],
        )

    assert response.status_code == 200, (
        f"[{scenario_name}] Consolidation endpoint returned {response.status_code}."
    )

    data = response.json()
    assert data["success"] is True, f"[{scenario_name}] success must be True."

    output_pairs = data["qna_pairs"]
    questions = [p["perguntaPadronizada"] for p in output_pairs]

    # SC-001: No two entries may share the same perguntaPadronizada
    seen: set = set()
    duplicates: list = []
    for q in questions:
        if q in seen:
            duplicates.append(q)
        seen.add(q)

    assert len(duplicates) == 0, (
        f"[{scenario_name}] SC-001 VIOLATED: Found duplicate perguntaPadronizada values "
        f"in output after consolidation: {duplicates}"
    )
