import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_consolidate_endpoint_json():
    json_content = b'{"qna_pairs": [{"perguntaPadronizada": "Q1?", "respostaConsolidada": "A1", "frequencia": 1}]}'
    
    response = client.post(
        "/api/merger/consolidate",
        data={"input_format": "json"},
        files=[("files", ("test.json", json_content, "application/json"))]
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

def test_consolidate_endpoint_txt():
    txt_content = b'[meta] (Frequencia: 1)\nQ: Q1?\nA: A1'
    
    response = client.post(
        "/api/merger/consolidate",
        data={"input_format": "txt"},
        files=[("files", ("test.txt", txt_content, "text/plain"))]
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
    # Create a merge to get an output file
    json_content = b'{"qna_pairs": [{"perguntaPadronizada": "Q2", "respostaConsolidada": "A2", "frequencia": 1}]}'
    
    response = client.post(
        "/api/merger/consolidate",
        data={"input_format": "json"},
        files=[("files", ("test2.json", json_content, "application/json"))]
    )
    assert response.status_code == 200
    data = response.json()
    filename = data["json_output_filename"]
    
    # Try to download it
    dl_response = client.get(f"/api/merger/download/{filename}")
    assert dl_response.status_code == 200
    assert "Q2" in dl_response.text
