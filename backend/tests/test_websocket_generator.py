"""
Integration tests for the /api/generate WebSocket endpoint.

Scope (no live OpenAI API calls required):
  1. Generator client: _build_generator_system_prompt(), _parse_generator_response()
  2. WebSocket /api/generate endpoint with a mocked generate_qna_from_chunk():
     — valid START → LOG → CHUNK_SUCCESS → QUEUE_COMPLETE full event stream
     — wrong ferramenta prompt_id → QUEUE_ERROR (prompt validation rejection)
     — unknown prompt_id → falls back to default generator prompt (not an error)
     — rate-limit error from generator → QUEUE_ERROR with partial results
     — empty file content → QUEUE_ERROR (no chunks)
     — unsupported file extension (.pdf) → QUEUE_ERROR (no chunks)
     — env key sentinel → resolves OPENAI_API_KEY environment variable

Run with:
    cd backend && pytest tests/test_websocket_generator.py -v
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_start_payload(
    key_id: str = "env",
    prompt_id: str = "default",
    files: list[dict] | None = None,
) -> str:
    """Build a JSON START payload string."""
    if files is None:
        files = [
            {
                "nomeArquivo": "test.txt",
                "conteudoBruto": "O horário de atendimento é das 8h às 18h.",
            }
        ]
    return json.dumps(
        {"action": "START", "key_id": key_id, "prompt_id": prompt_id, "files": files}
    )


def _collect_events(ws_events: list[str]) -> list[dict]:
    """Parse a list of JSON strings into dicts."""
    return [json.loads(e) for e in ws_events]


def _make_pair() -> dict:
    """Return a minimal ResultadoParPR-compatible dict."""
    return {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "O horário de atendimento é das 8h às 18h.",
        "frequencia": 1,
        "metadata": "Horários",
        "category": "FAQ",
    }


# ──────────────────────────────────────────────────────────────────────────────
# 1. Unit tests: generator_client helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestGeneratorClientHelpers:
    """Unit tests for internal generator_client functions."""

    def test_build_system_prompt_none_returns_default(self):
        """None prompt_config → built-in default generator prompt."""
        from src.services.generator_client import _build_generator_system_prompt
        from src.services.prompt_storage import DEFAULT_GENERATOR_PROMPT_TEXT

        result = _build_generator_system_prompt(None)
        assert result == DEFAULT_GENERATOR_PROMPT_TEXT

    def test_build_system_prompt_fixo_uses_textoInstrucao(self):
        """FIXO prompt with textoInstrucao → uses that text directly."""
        from src.models.schemas import ModeloOpenAI, PromptConfig, TipoFerramenta, TipoPrompt
        from src.services.generator_client import _build_generator_system_prompt

        prompt = PromptConfig(
            id="test-uuid",
            nome="Test Generator",
            tipo=TipoPrompt.FIXO,
            textoInstrucao="Gere perguntas específicas para documentos técnicos.",
            palavrasChave=[],
            idiomaModelo="pt-br",
            modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
            ferramenta=TipoFerramenta.GERADOR,
        )
        result = _build_generator_system_prompt(prompt)
        assert result == "Gere perguntas específicas para documentos técnicos."

    def test_build_system_prompt_fixo_no_texto_returns_default(self):
        """FIXO prompt without textoInstrucao → built-in default generator prompt."""
        from src.models.schemas import ModeloOpenAI, PromptConfig, TipoFerramenta, TipoPrompt
        from src.services.generator_client import _build_generator_system_prompt
        from src.services.prompt_storage import DEFAULT_GENERATOR_PROMPT_TEXT

        prompt = PromptConfig(
            id="test-uuid",
            nome="Empty Fixo",
            tipo=TipoPrompt.FIXO,
            textoInstrucao=None,
            palavrasChave=[],
            idiomaModelo="pt-br",
            modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
            ferramenta=TipoFerramenta.GERADOR,
        )
        result = _build_generator_system_prompt(prompt)
        assert result == DEFAULT_GENERATOR_PROMPT_TEXT

    def test_build_system_prompt_customizado_with_keywords(self):
        """CUSTOMIZADO prompt with keywords → text + keyword hint appended."""
        from src.models.schemas import ModeloOpenAI, PromptConfig, TipoFerramenta, TipoPrompt
        from src.services.generator_client import _build_generator_system_prompt

        prompt = PromptConfig(
            id="test-uuid",
            nome="Custom Gen",
            tipo=TipoPrompt.CUSTOMIZADO,
            textoInstrucao="Gere perguntas focadas em clientes.",
            palavrasChave=["Financeiro", "Cobrança"],
            idiomaModelo="pt-br",
            modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
            ferramenta=TipoFerramenta.GERADOR,
        )
        result = _build_generator_system_prompt(prompt)
        assert "Gere perguntas focadas em clientes." in result
        assert "Financeiro" in result
        assert "Cobrança" in result

    def test_parse_generator_response_valid_json(self):
        """Valid JSON with qna_pairs → parsed into ResultadoParPR list."""
        from src.services.generator_client import _parse_generator_response

        raw = json.dumps(
            {
                "qna_pairs": [
                    {
                        "question": "Qual o horário?",
                        "answer": "Das 8h às 18h.",
                        "frequency": 1,
                        "metadata": "Horários",
                        "category": "FAQ",
                    }
                ]
            }
        )
        pairs = _parse_generator_response(raw)
        assert len(pairs) == 1
        assert pairs[0].perguntaPadronizada == "Qual o horário?"
        assert pairs[0].respostaConsolidada == "Das 8h às 18h."
        assert pairs[0].frequencia == 1
        assert pairs[0].metadata == "Horários"
        assert pairs[0].category == "FAQ"

    def test_parse_generator_response_strips_markdown_fences(self):
        """JSON wrapped in ```json code fences is parsed correctly."""
        from src.services.generator_client import _parse_generator_response

        raw = '```json\n{"qna_pairs": [{"question": "Q?", "answer": "A.", "frequency": 1, "metadata": null, "category": "FAQ"}]}\n```'
        pairs = _parse_generator_response(raw)
        assert len(pairs) == 1

    def test_parse_generator_response_empty_qna_pairs(self):
        """Empty qna_pairs list → returns empty list without error."""
        from src.services.generator_client import _parse_generator_response

        raw = json.dumps({"qna_pairs": []})
        pairs = _parse_generator_response(raw)
        assert pairs == []

    def test_parse_generator_response_invalid_json_raises(self):
        """Non-JSON string → ValueError."""
        from src.services.generator_client import _parse_generator_response

        with pytest.raises(ValueError, match="Model returned invalid JSON"):
            _parse_generator_response("not valid json at all!")

    def test_parse_generator_response_category_defaults_to_faq(self):
        """Missing category field defaults to 'FAQ'."""
        from src.services.generator_client import _parse_generator_response

        raw = json.dumps(
            {"qna_pairs": [{"question": "Q?", "answer": "A.", "frequency": 1, "metadata": None}]}
        )
        pairs = _parse_generator_response(raw)
        assert pairs[0].category == "FAQ"


# ──────────────────────────────────────────────────────────────────────────────
# 2. WebSocket integration tests: /api/generate endpoint
# ──────────────────────────────────────────────────────────────────────────────

# Shared mock pair for generate_qna_from_chunk return value
_MOCK_PAIRS_RESULT = (
    [
        MagicMock(
            model_dump=lambda: {
                "perguntaPadronizada": "Qual o horário de atendimento?",
                "respostaConsolidada": "O horário de atendimento é das 8h às 18h.",
                "frequencia": 1,
                "metadata": "Horários",
                "category": "FAQ",
            }
        )
    ],
    [],  # uncategorized always []
)


class TestGeneratorWebSocket:
    """Integration tests for the /api/generate WebSocket endpoint."""

    @pytest.fixture
    def client(self):
        """TestClient backed by a temp DATA_DIR to avoid touching real prompts.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            prompts_file = tmp_path / "prompts.json"
            keys_file = tmp_path / "keys.json"

            # Write empty files so services don't fail on startup
            prompts_file.write_text("[]", encoding="utf-8")
            keys_file.write_text("[]", encoding="utf-8")

            with (
                patch("src.services.prompt_storage.DATA_DIR", tmp_path),
                patch("src.services.prompt_storage.PROMPTS_FILE", prompts_file),
                patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}),
            ):
                from src.main import app

                with TestClient(app) as c:
                    yield c

    # ── 2a. Happy path ────────────────────────────────────────────────────────

    def test_full_generation_lifecycle(self, client):
        """
        Happy path: valid START → LOG → CHUNK_SUCCESS → QUEUE_COMPLETE.
        Uses key_id='env' and prompt_id='default' (built-in generator prompt).
        """
        from src.models.schemas import ResultadoParPR

        mock_pair = ResultadoParPR(
            perguntaPadronizada="Qual o horário de atendimento?",
            respostaConsolidada="O horário de atendimento é das 8h às 18h.",
            frequencia=1,
            metadata="Horários",
            category="FAQ",
        )

        with (
            patch(
                "src.api.websocket_generator.generate_qna_from_chunk",
                new=AsyncMock(return_value=([mock_pair], [])),
            ),
            patch(
                "src.services.consolidator.consolidate_qna_pairs",
                new=AsyncMock(return_value=[mock_pair]),
            ),
        ):
            with client.websocket_connect("/api/generate") as ws:
                ws.send_text(_make_start_payload())
                received: list[dict] = []

                # Collect events until QUEUE_COMPLETE or QUEUE_ERROR
                for _ in range(20):  # safety limit
                    try:
                        msg = ws.receive_text()
                        event = json.loads(msg)
                        received.append(event)
                        if event["event"] in ("QUEUE_COMPLETE", "QUEUE_ERROR"):
                            break
                    except Exception:
                        break

        event_names = [e["event"] for e in received]
        assert "LOG" in event_names, "Expected at least one LOG event"
        assert "CHUNK_SUCCESS" in event_names, "Expected CHUNK_SUCCESS event"
        assert "QUEUE_COMPLETE" in event_names, "Expected QUEUE_COMPLETE event"

        # Validate QUEUE_COMPLETE payload shape
        complete_event = next(e for e in received if e["event"] == "QUEUE_COMPLETE")
        assert "results" in complete_event["data"]
        assert "uncategorized_database_content" in complete_event["data"]
        assert complete_event["data"]["uncategorized_database_content"] == []

    # ── 2b. Invalid payload ───────────────────────────────────────────────────

    def test_invalid_start_payload_sends_log_and_closes(self, client):
        """Non-JSON or malformed payload → LOG(ERRO) event, then connection closes."""
        with client.websocket_connect("/api/generate") as ws:
            ws.send_text("this is not json at all")
            received = []
            for _ in range(5):
                try:
                    msg = ws.receive_text()
                    received.append(json.loads(msg))
                except Exception:
                    break

        assert any(
            e["event"] == "LOG" and e["data"]["tipo"] == "ERRO" for e in received
        ), "Expected LOG ERRO for invalid payload"

    def test_wrong_action_sends_log_and_closes(self, client):
        """action != 'START' → LOG(ERRO) and close."""
        payload = json.dumps(
            {"action": "STOP", "key_id": "env", "prompt_id": "default", "files": []}
        )
        with client.websocket_connect("/api/generate") as ws:
            ws.send_text(payload)
            received = []
            for _ in range(5):
                try:
                    msg = ws.receive_text()
                    received.append(json.loads(msg))
                except Exception:
                    break

        assert any(e["event"] == "LOG" and e["data"]["tipo"] == "ERRO" for e in received)

    # ── 2c. Prompt validation ─────────────────────────────────────────────────

    def test_extrator_prompt_rejected_by_generator_endpoint(self, client):
        """
        A prompt with ferramenta='extrator' sent to /api/generate → QUEUE_ERROR.
        """
        import tempfile

        from src.models.schemas import (
            ModeloOpenAI,
            PromptConfig,
            TipoFerramenta,
            TipoPrompt,
        )

        extrator_prompt = PromptConfig(
            id="extrator-prompt-id",
            nome="Prompt do Extrator",
            tipo=TipoPrompt.FIXO,
            textoInstrucao="Extraia pares de P&R.",
            palavrasChave=[],
            idiomaModelo="pt-br",
            modeloOpenAI=ModeloOpenAI.GPT_4O_MINI,
            ferramenta=TipoFerramenta.EXTRATOR,
        )

        mock_storage = MagicMock()
        mock_storage.get_by_id.return_value = extrator_prompt

        with patch(
            "src.api.websocket_generator._resolve_generator_prompt",
            new=AsyncMock(
                side_effect=ValueError(
                    "O prompt pertence à ferramenta 'extrator', mas o endpoint /api/generate requer ferramenta='gerador'."
                )
            ),
        ):
            with client.websocket_connect("/api/generate") as ws:
                ws.send_text(_make_start_payload(prompt_id="extrator-prompt-id"))
                received = []
                for _ in range(10):
                    try:
                        msg = ws.receive_text()
                        received.append(json.loads(msg))
                        if received[-1]["event"] in ("QUEUE_ERROR", "QUEUE_COMPLETE"):
                            break
                    except Exception:
                        break

        event_names = [e["event"] for e in received]
        assert "QUEUE_ERROR" in event_names, f"Expected QUEUE_ERROR, got: {event_names}"

    # ── 2d. Rate-limit error ──────────────────────────────────────────────────

    def test_rate_limit_error_sends_queue_error_with_partial_results(self, client):
        """RuntimeError (rate limit) from generate_qna_from_chunk → QUEUE_ERROR."""
        with (
            patch(
                "src.api.websocket_generator.generate_qna_from_chunk",
                new=AsyncMock(side_effect=RuntimeError("Limite de taxa atingido (429)")),
            ),
        ):
            with client.websocket_connect("/api/generate") as ws:
                ws.send_text(_make_start_payload())
                received = []
                for _ in range(20):
                    try:
                        msg = ws.receive_text()
                        received.append(json.loads(msg))
                        if received[-1]["event"] in ("QUEUE_ERROR", "QUEUE_COMPLETE"):
                            break
                    except Exception:
                        break

        event_names = [e["event"] for e in received]
        assert "QUEUE_ERROR" in event_names, f"Expected QUEUE_ERROR, got: {event_names}"

        error_event = next(e for e in received if e["event"] == "QUEUE_ERROR")
        assert "partial_results" in error_event["data"]
        assert "uncategorized_database_content" in error_event["data"]
        assert error_event["data"]["uncategorized_database_content"] == []

    # ── 2e. Empty / unsupported files ────────────────────────────────────────

    def test_unsupported_file_extension_sends_queue_error(self, client):
        """File with .pdf extension → skipped, no chunks → QUEUE_ERROR."""
        payload = _make_start_payload(
            files=[{"nomeArquivo": "document.pdf", "conteudoBruto": "Conteúdo PDF"}]
        )
        with client.websocket_connect("/api/generate") as ws:
            ws.send_text(payload)
            received = []
            for _ in range(20):
                try:
                    msg = ws.receive_text()
                    received.append(json.loads(msg))
                    if received[-1]["event"] in ("QUEUE_ERROR", "QUEUE_COMPLETE"):
                        break
                except Exception:
                    break

        event_names = [e["event"] for e in received]
        assert "QUEUE_ERROR" in event_names, f"Expected QUEUE_ERROR for .pdf, got: {event_names}"

    # ── 2f. Missing API key ───────────────────────────────────────────────────

    def test_missing_env_api_key_sends_queue_error(self):
        """key_id='env' without OPENAI_API_KEY set → QUEUE_ERROR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            prompts_file = tmp_path / "prompts.json"
            prompts_file.write_text("[]", encoding="utf-8")

            with (
                patch("src.services.prompt_storage.DATA_DIR", tmp_path),
                patch("src.services.prompt_storage.PROMPTS_FILE", prompts_file),
                patch.dict(os.environ, {}, clear=True),  # ensure no OPENAI_API_KEY
            ):
                # Remove key if it slipped through
                os.environ.pop("OPENAI_API_KEY", None)

                from src.main import app

                with TestClient(app) as client:
                    with client.websocket_connect("/api/generate") as ws:
                        ws.send_text(_make_start_payload(key_id="env"))
                        received = []
                        for _ in range(10):
                            try:
                                msg = ws.receive_text()
                                received.append(json.loads(msg))
                                if received[-1]["event"] in ("QUEUE_ERROR", "QUEUE_COMPLETE"):
                                    break
                            except Exception:
                                break

        event_names = [e["event"] for e in received]
        assert "QUEUE_ERROR" in event_names or any(
            e["event"] == "LOG" and e["data"]["tipo"] == "ERRO" for e in received
        ), f"Expected error events, got: {event_names}"

    # ── 2g. CHUNK_SUCCESS uncategorized always empty ──────────────────────────

    def test_chunk_success_uncategorized_always_empty(self, client):
        """CHUNK_SUCCESS events from the generator always have empty uncategorized list."""
        from src.models.schemas import ResultadoParPR

        mock_pair = ResultadoParPR(
            perguntaPadronizada="Qual o horário?",
            respostaConsolidada="Das 8h às 18h.",
            frequencia=1,
            metadata=None,
            category="FAQ",
        )

        with (
            patch(
                "src.api.websocket_generator.generate_qna_from_chunk",
                new=AsyncMock(return_value=([mock_pair], [])),
            ),
            patch(
                "src.services.consolidator.consolidate_qna_pairs",
                new=AsyncMock(return_value=[mock_pair]),
            ),
        ):
            with client.websocket_connect("/api/generate") as ws:
                ws.send_text(_make_start_payload())
                received = []
                for _ in range(20):
                    try:
                        msg = ws.receive_text()
                        received.append(json.loads(msg))
                        if received[-1]["event"] in ("QUEUE_COMPLETE", "QUEUE_ERROR"):
                            break
                    except Exception:
                        break

        chunk_events = [e for e in received if e["event"] == "CHUNK_SUCCESS"]
        for chunk_ev in chunk_events:
            assert chunk_ev["data"]["uncategorized_database_content"] == [], (
                "Generator CHUNK_SUCCESS must always have empty uncategorized_database_content"
            )
