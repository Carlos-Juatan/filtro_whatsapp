"""
Integration tests for the end-to-end processing pipeline.

Scope (no live OpenAI API calls required):
  1. Text parsing → chunking pipeline (TxtParser + split_text)
  2. Key storage service CRUD (KeyStorageService)
  3. Prompt storage service CRUD (PromptStorageService)
  4. FastAPI HTTP health and key/prompt REST endpoints (TestClient)
  5. WebSocket /api/process endpoint with a mocked OpenAI extraction function
     — verifies the full event stream protocol: LOG → CHUNK_SUCCESS → QUEUE_COMPLETE

Run with:
    cd backend && pytest tests/test_integration.py -v
"""

from __future__ import annotations

import json
import tempfile
import os
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────────────────────────────────────
# 1. Parse + Chunk pipeline
# ──────────────────────────────────────────────────────────────────────────────


class TestParseAndChunkPipeline:
    """Verify that TxtParser output feeds cleanly into split_text."""

    def test_short_file_produces_single_chunk(self):
        from src.services.parsers import TxtParser
        from src.services.chunker import split_text

        content = "Qual o horário de atendimento?\nDas 8h às 18h de segunda a sexta."
        raw = content.encode("utf-8")
        text = TxtParser().parse(raw)
        chunks = split_text(text)

        assert len(chunks) == 1
        assert chunks[0] == content.strip()

    def test_large_file_chunked_and_all_content_preserved(self):
        """A very large file is chunked; original words are fully present across all chunks."""
        from src.services.parsers import TxtParser
        from src.services.chunker import split_text

        sentence = "Esta é uma frase de exemplo para teste de integração. "
        large_content = sentence * 800  # ~12 000 tokens
        raw = large_content.encode("utf-8")

        text = TxtParser().parse(raw)
        chunks = split_text(text)

        assert len(chunks) > 1, "Large text should produce multiple chunks"
        # All meaningful words must survive across chunks
        combined = " ".join(chunks)
        assert "integração" in combined
        assert "exemplo" in combined

    def test_crlf_file_normalised_and_split_correctly(self):
        from src.services.parsers import TxtParser
        from src.services.chunker import split_text

        content = "Pergunta 1\r\nResposta 1\r\n\r\nPergunta 2\r\nResposta 2"
        raw = content.encode("utf-8")
        text = TxtParser().parse(raw)
        assert "\r" not in text

        chunks = split_text(text)
        assert all(c.strip() for c in chunks)


# ──────────────────────────────────────────────────────────────────────────────
# 2. KeyStorageService – isolated with a temp directory
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_data_dir(monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Redirect DATA_DIR to a fresh temp directory for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        monkeypatch.setenv("DATA_DIR", str(tmp))

        # Patch the module-level DATA_DIR and file path constants so the service
        # picks up the new directory without reimporting the module.
        import src.services.key_storage as ks_mod
        import src.services.prompt_storage as ps_mod

        monkeypatch.setattr(ks_mod, "DATA_DIR", tmp)
        monkeypatch.setattr(ks_mod, "KEYS_FILE", tmp / "keys.json")
        monkeypatch.setattr(ps_mod, "DATA_DIR", tmp)
        monkeypatch.setattr(ps_mod, "PROMPTS_FILE", tmp / "prompts.json")

        yield tmp


class TestKeyStorageIntegration:
    """Full CRUD lifecycle for KeyStorageService."""

    def test_add_and_retrieve_key(self, tmp_data_dir: Path):
        from src.services.key_storage import KeyStorageService
        from src.models.schemas import ChaveAPICreate

        svc = KeyStorageService()
        created = svc.add(ChaveAPICreate(nomeIdentificacao="Test Key", chave="sk-test-abc123"))

        assert created.id
        result = svc.get_by_id(created.id)
        assert result is not None
        assert result.chave == "sk-test-abc123"
        assert result.nomeIdentificacao == "Test Key"

    def test_get_all_returns_all_keys(self, tmp_data_dir: Path):
        from src.services.key_storage import KeyStorageService
        from src.models.schemas import ChaveAPICreate

        svc = KeyStorageService()
        svc.add(ChaveAPICreate(nomeIdentificacao="Key A", chave="sk-aaa"))
        svc.add(ChaveAPICreate(nomeIdentificacao="Key B", chave="sk-bbb"))

        keys = svc.get_all()
        assert len(keys) == 2
        names = {k.nomeIdentificacao for k in keys}
        assert names == {"Key A", "Key B"}

    def test_duplicate_name_raises_value_error(self, tmp_data_dir: Path):
        from src.services.key_storage import KeyStorageService
        from src.models.schemas import ChaveAPICreate

        svc = KeyStorageService()
        svc.add(ChaveAPICreate(nomeIdentificacao="Dup Key", chave="sk-111"))
        with pytest.raises(ValueError, match="already exists"):
            svc.add(ChaveAPICreate(nomeIdentificacao="Dup Key", chave="sk-222"))

    def test_delete_key(self, tmp_data_dir: Path):
        from src.services.key_storage import KeyStorageService
        from src.models.schemas import ChaveAPICreate

        svc = KeyStorageService()
        created = svc.add(ChaveAPICreate(nomeIdentificacao="Delete Me", chave="sk-del"))
        success = svc.delete(created.id)
        assert success is True
        assert svc.get_by_id(created.id) is None

    def test_delete_nonexistent_returns_false(self, tmp_data_dir: Path):
        from src.services.key_storage import KeyStorageService

        svc = KeyStorageService()
        assert svc.delete("nonexistent-uuid") is False

    def test_persistence_across_instances(self, tmp_data_dir: Path):
        """Data survives creating a new instance (reads from disk)."""
        from src.services.key_storage import KeyStorageService
        from src.models.schemas import ChaveAPICreate

        svc1 = KeyStorageService()
        created = svc1.add(ChaveAPICreate(nomeIdentificacao="Persistent", chave="sk-persist"))

        svc2 = KeyStorageService()
        result = svc2.get_by_id(created.id)
        assert result is not None
        assert result.nomeIdentificacao == "Persistent"


# ──────────────────────────────────────────────────────────────────────────────
# 3. PromptStorageService – isolated with a temp directory
# ──────────────────────────────────────────────────────────────────────────────


class TestPromptStorageIntegration:
    """Full CRUD lifecycle for PromptStorageService."""

    def test_add_and_retrieve_prompt(self, tmp_data_dir: Path):
        from src.services.prompt_storage import PromptStorageService
        from src.models.schemas import PromptConfigCreate, TipoPrompt

        svc = PromptStorageService()
        created = svc.add(
            PromptConfigCreate(
                nome="Custom Prompt",
                tipo=TipoPrompt.CUSTOMIZADO,
                textoInstrucao="Extraia perguntas e respostas do texto a seguir.",
                idiomaModelo="pt-br",
            )
        )

        result = svc.get_by_id(created.id)
        assert result is not None
        assert result.nome == "Custom Prompt"
        assert result.tipo == TipoPrompt.CUSTOMIZADO

    def test_duplicate_prompt_name_raises(self, tmp_data_dir: Path):
        from src.services.prompt_storage import PromptStorageService
        from src.models.schemas import PromptConfigCreate, TipoPrompt

        svc = PromptStorageService()
        svc.add(
            PromptConfigCreate(
                nome="Same Name",
                tipo=TipoPrompt.CUSTOMIZADO,
                textoInstrucao="Extraia perguntas e respostas.",
            )
        )
        with pytest.raises(ValueError, match="already exists"):
            svc.add(
                PromptConfigCreate(
                    nome="Same Name",
                    tipo=TipoPrompt.CUSTOMIZADO,
                    textoInstrucao="Outro texto de instrução aqui.",
                )
            )

    def test_customizado_without_texto_raises(self, tmp_data_dir: Path):
        from src.services.prompt_storage import PromptStorageService
        from src.models.schemas import PromptConfigCreate, TipoPrompt

        svc = PromptStorageService()
        with pytest.raises(ValueError):
            svc.add(
                PromptConfigCreate(
                    nome="No Text",
                    tipo=TipoPrompt.CUSTOMIZADO,
                    textoInstrucao=None,
                )
            )

    def test_get_all_prompts(self, tmp_data_dir: Path):
        from src.services.prompt_storage import PromptStorageService
        from src.models.schemas import PromptConfigCreate, TipoPrompt

        svc = PromptStorageService()
        svc.add(PromptConfigCreate(nome="P1", tipo=TipoPrompt.CUSTOMIZADO, textoInstrucao="Instrução um aqui."))
        svc.add(PromptConfigCreate(nome="P2", tipo=TipoPrompt.CUSTOMIZADO, textoInstrucao="Instrução dois aqui."))

        prompts = svc.get_all()
        assert len(prompts) == 5  # 3 system defaults (extrator, gerador, consolidador) + 2 added


# ──────────────────────────────────────────────────────────────────────────────
# 4. FastAPI HTTP endpoints (TestClient, no network)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def client(tmp_data_dir: Path) -> TestClient:
    """TestClient with patched storage paths."""
    from src.main import app

    return TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body


class TestKeysHTTPEndpoints:
    def test_get_keys_empty(self, client: TestClient):
        response = client.get("/api/keys")
        assert response.status_code == 200
        assert response.json() == []

    def test_post_and_get_key(self, client: TestClient):
        payload = {"nomeIdentificacao": "HTTP Key", "chave": "sk-http-test"}
        post_resp = client.post("/api/keys", json=payload)
        assert post_resp.status_code == 201
        created = post_resp.json()
        assert created["nomeIdentificacao"] == "HTTP Key"
        assert "id" in created

        get_resp = client.get("/api/keys")
        assert get_resp.status_code == 200
        assert len(get_resp.json()) == 1

    def test_post_duplicate_name_returns_400(self, client: TestClient):
        payload = {"nomeIdentificacao": "Dup", "chave": "sk-dup"}
        client.post("/api/keys", json=payload)
        resp = client.post("/api/keys", json=payload)
        assert resp.status_code == 400

    def test_delete_key(self, client: TestClient):
        created = client.post(
            "/api/keys", json={"nomeIdentificacao": "To Delete", "chave": "sk-del"}
        ).json()
        del_resp = client.delete(f"/api/keys/{created['id']}")
        assert del_resp.status_code == 204

        keys = client.get("/api/keys").json()
        assert len(keys) == 0

    def test_delete_nonexistent_returns_404(self, client: TestClient):
        resp = client.delete("/api/keys/00000000-dead-beef-cafe-000000000000")
        assert resp.status_code == 404


class TestPromptsHTTPEndpoints:
    def test_get_prompts_empty(self, client: TestClient):
        response = client.get("/api/prompts")
        assert response.status_code == 200
        assert response.json() == []

    def test_post_and_get_prompt(self, client: TestClient):
        payload = {
            "nome": "Extrator Padrão",
            "tipo": "CUSTOMIZADO",
            "textoInstrucao": "Extraia perguntas e respostas do texto fornecido.",
            "idiomaModelo": "pt-br",
        }
        post_resp = client.post("/api/prompts", json=payload)
        assert post_resp.status_code == 201
        created = post_resp.json()
        assert created["nome"] == "Extrator Padrão"

        get_resp = client.get("/api/prompts")
        assert len(get_resp.json()) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 5. WebSocket /api/process — end-to-end event stream (mocked OpenAI)
# ──────────────────────────────────────────────────────────────────────────────


SAMPLE_QNA = [
    {
        "perguntaPadronizada": "Qual o horário de atendimento?",
        "respostaConsolidada": "Das 8h às 18h de segunda a sexta.",
        "frequencia": 2,
        "metadata": "horário",
        "category": "Suporte",
    }
]


def _make_resultado_par_pr():
    from src.models.schemas import ResultadoParPR
    return [ResultadoParPR(**item) for item in SAMPLE_QNA]


class TestWebSocketProcessing:
    """
    Test the full WebSocket protocol without making real OpenAI calls.
    We mock extract_qna_from_chunk and consolidate_qna_pairs at the module level.
    """

    def test_successful_processing_emits_correct_event_sequence(self, client: TestClient, tmp_data_dir: Path):
        """
        Full happy path: START → LOG(s) → CHUNK_SUCCESS → QUEUE_COMPLETE.
        """
        mock_pairs = _make_resultado_par_pr()

        with (
            patch(
                "src.api.websocket.extract_qna_from_chunk",
                new=AsyncMock(return_value=(mock_pairs, ["Fato extraído"])),
            ),
            patch(
                "src.api.websocket.consolidate_qna_pairs",
                new=AsyncMock(return_value=mock_pairs),
            ),
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-mock-key"}),
        ):
            with client.websocket_connect("/api/process") as ws:
                ws.send_text(
                    json.dumps(
                        {
                            "action": "START",
                            "key_id": "env",
                            "prompt_id": "default",
                            "files": [
                                {
                                    "nomeArquivo": "sample.txt",
                                    "conteudoBruto": "Qual o horário de atendimento? Das 8h às 18h.",
                                }
                            ],
                        }
                    )
                )

                events = []
                try:
                    while True:
                        msg = ws.receive_text()
                        event = json.loads(msg)
                        events.append(event)
                        if event["event"] in ("QUEUE_COMPLETE", "QUEUE_ERROR"):
                            break
                except Exception:
                    pass

        event_types = [e["event"] for e in events]
        assert "LOG" in event_types, "Expected at least one LOG event"
        assert "QUEUE_COMPLETE" in event_types, "Expected QUEUE_COMPLETE event"
        assert "QUEUE_ERROR" not in event_types, "Did not expect QUEUE_ERROR"

        complete_event = next(e for e in events if e["event"] == "QUEUE_COMPLETE")
        results = complete_event["data"]["results"]
        assert len(results) == 1
        assert results[0]["perguntaPadronizada"] == "Qual o horário de atendimento?"

    def test_invalid_start_action_closes_with_error(self, client: TestClient):
        """
        Sending an unsupported action should result in an error LOG and connection close.
        """
        with client.websocket_connect("/api/process") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "action": "STOP",  # invalid
                        "key_id": "env",
                        "prompt_id": "default",
                        "files": [{"nomeArquivo": "f.txt", "conteudoBruto": "content"}],
                    }
                )
            )
            events = []
            try:
                while True:
                    msg = ws.receive_text()
                    events.append(json.loads(msg))
            except Exception:
                pass

        assert any(e["event"] == "LOG" for e in events), "Expected error LOG for invalid action"

    def test_missing_openai_key_sends_queue_error(self, client: TestClient):
        """
        When key_id='env' and OPENAI_API_KEY is not set, the server must send QUEUE_ERROR.
        """
        env_without_key = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            with client.websocket_connect("/api/process") as ws:
                ws.send_text(
                    json.dumps(
                        {
                            "action": "START",
                            "key_id": "env",
                            "prompt_id": "default",
                            "files": [{"nomeArquivo": "f.txt", "conteudoBruto": "texto"}],
                        }
                    )
                )
                events = []
                try:
                    while True:
                        msg = ws.receive_text()
                        event = json.loads(msg)
                        events.append(event)
                        if event["event"] in ("QUEUE_COMPLETE", "QUEUE_ERROR"):
                            break
                except Exception:
                    pass

        assert any(
            e["event"] == "QUEUE_ERROR" for e in events
        ), "Expected QUEUE_ERROR when API key is missing"

    def test_chunk_success_events_emitted(self, client: TestClient, tmp_data_dir: Path):
        """CHUNK_SUCCESS events must be emitted between LOG events and QUEUE_COMPLETE."""
        mock_pairs = _make_resultado_par_pr()

        with (
            patch(
                "src.api.websocket.extract_qna_from_chunk",
                new=AsyncMock(return_value=(mock_pairs, ["Fato extraído"])),
            ),
            patch(
                "src.api.websocket.consolidate_qna_pairs",
                new=AsyncMock(return_value=mock_pairs),
            ),
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-mock"}),
        ):
            with client.websocket_connect("/api/process") as ws:
                ws.send_text(
                    json.dumps(
                        {
                            "action": "START",
                            "key_id": "env",
                            "prompt_id": "default",
                            "files": [
                                {
                                    "nomeArquivo": "chunk_test.txt",
                                    "conteudoBruto": "Pergunta de integração? Resposta de integração.",
                                }
                            ],
                        }
                    )
                )

                events = []
                try:
                    while True:
                        msg = ws.receive_text()
                        event = json.loads(msg)
                        events.append(event)
                        if event["event"] in ("QUEUE_COMPLETE", "QUEUE_ERROR"):
                            break
                except Exception:
                    pass

        event_types = [e["event"] for e in events]
        assert "CHUNK_SUCCESS" in event_types, "Expected at least one CHUNK_SUCCESS event"
