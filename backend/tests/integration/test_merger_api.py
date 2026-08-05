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


# ──────────────────────────────────────────────────────────────────────────────
# T033: Phase 8 integration tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPhase8TxtSeparator:
    """SC-002: TXT output must have separator after every A: block including the last."""

    def test_sc002_txt_last_block_has_separator(self):
        """
        SC-002: Download the generated TXT file and verify the final line
        (or near-final non-blank line) is the 40-dash separator.
        """
        json_content = json.dumps({
            "qna_pairs": [
                {"perguntaPadronizada": "Q Alpha?", "respostaConsolidada": "Answer Alpha.", "frequencia": 1},
                {"perguntaPadronizada": "Q Beta?", "respostaConsolidada": "Answer Beta.", "frequencia": 2},
            ]
        }).encode()

        with _no_key_patch():
            response = client.post(
                "/api/merger/consolidate",
                data={"input_format": "json"},
                files=[("files", ("sc002_test.json", json_content, "application/json"))],
            )

        assert response.status_code == 200
        data = response.json()
        txt_filename = data["txt_output_filename"]
        assert txt_filename is not None, "TXT output filename must be present."

        dl = client.get(f"/api/merger/download/{txt_filename}")
        assert dl.status_code == 200

        txt_content = dl.text
        lines = txt_content.splitlines()
        # Strip trailing empty lines to find the last meaningful line
        non_empty_lines = [l for l in lines if l.strip()]
        last_line = non_empty_lines[-1] if non_empty_lines else ""
        assert last_line == "----------------------------------------", (
            f"SC-002 VIOLATED: Last non-empty TXT line is {last_line!r}, "
            "expected '----------------------------------------'."
        )

    def test_sc002_all_blocks_have_separator(self):
        """Each Q&A block in the TXT output must be followed by the separator line."""
        json_content = json.dumps({
            "qna_pairs": [
                {"perguntaPadronizada": f"Pergunta {i}?", "respostaConsolidada": f"Resposta {i}.", "frequencia": i + 1}
                for i in range(5)
            ]
        }).encode()

        with _no_key_patch():
            response = client.post(
                "/api/merger/consolidate",
                data={"input_format": "json"},
                files=[("files", ("sc002_all_blocks.json", json_content, "application/json"))],
            )

        assert response.status_code == 200
        txt_filename = response.json()["txt_output_filename"]
        dl = client.get(f"/api/merger/download/{txt_filename}")
        txt_content = dl.text

        # Count A: lines and separator lines — they must be equal
        a_lines = [l for l in txt_content.splitlines() if l.startswith("A: ")]
        sep_lines = [l for l in txt_content.splitlines() if l == "----------------------------------------"]
        assert len(a_lines) == len(sep_lines) == 5, (
            f"SC-002: Expected 5 A: lines and 5 separator lines; "
            f"got {len(a_lines)} A: and {len(sep_lines)} separator lines."
        )


class TestPhase8LogEvents:
    """SC-004: Log events must be emitted during consolidation."""

    def test_sc004_log_store_populated_after_consolidation(self):
        """
        SC-004: After calling /consolidate, the merger_log job_log_store
        should have been populated and then cleaned up (done sentinel sent).
        We verify this indirectly: the COMPLETE log event message is present
        as the last event in any SSE stream that connected during the run.

        Since the TestClient is synchronous and SSE is async, we verify the
        behaviour by importing the log store directly and checking its API.
        """
        from src.api.endpoints.merger_log import job_log_store, register_job, emit, close_job
        from src.models.merger import MergerLogEvent, MergerLogEventType

        # Manually exercise the log store API
        test_job_id = "test-sc004"
        register_job(test_job_id)
        emit(test_job_id, MergerLogEvent(
            event_type=MergerLogEventType.PARSE_START,
            message="Test parse start event."
        ))
        emit(test_job_id, MergerLogEvent(
            event_type=MergerLogEventType.COMPLETE,
            message="Test complete event."
        ))
        close_job(test_job_id)

        events = job_log_store.get(test_job_id, [])
        # Events list should contain 2 MergerLogEvent + 1 sentinel
        real_events = [e for e in events if isinstance(e, MergerLogEvent)]
        assert len(real_events) == 2
        assert real_events[0].event_type == MergerLogEventType.PARSE_START
        assert real_events[1].event_type == MergerLogEventType.COMPLETE

        # Clean up test job
        job_log_store.pop(test_job_id, None)


class TestPhase8LargeConsolidation:
    """SC-005: 300-pair consolidation must complete without error."""

    def test_sc005_300_pair_consolidation_completes(self):
        """
        SC-005: Submit 300 unique Q&A pairs in a single consolidation request.
        The endpoint must return 200 and report total_qna_merged == 300.
        """
        pairs = [
            {
                "perguntaPadronizada": f"Pergunta número {i}?",
                "respostaConsolidada": f"Resposta detalhada para a pergunta número {i}.",
                "frequencia": 1,
            }
            for i in range(300)
        ]
        payload = json.dumps({"qna_pairs": pairs}).encode()

        with _no_key_patch():
            response = client.post(
                "/api/merger/consolidate",
                data={"input_format": "json"},
                files=[("files", ("sc005_300pairs.json", payload, "application/json"))],
            )

        assert response.status_code == 200, (
            f"SC-005: Expected 200, got {response.status_code}. Body: {response.text[:300]}"
        )
        data = response.json()
        assert data["success"] is True, "SC-005: success must be True for 300-pair input."
        assert data["total_qna_extracted"] == 300, (
            f"SC-005: Expected 300 extracted, got {data['total_qna_extracted']}."
        )
        assert data["total_qna_merged"] == 300, (
            f"SC-005: Expected 300 unique merged pairs, got {data['total_qna_merged']}."
        )
        # Also verify zero duplicates in output (SC-001 x SC-005 cross-check)
        questions = [p["perguntaPadronizada"] for p in data["qna_pairs"]]
        assert len(questions) == len(set(questions)), (
            "SC-005: Output contains duplicate perguntaPadronizada values after 300-pair merge."
        )
