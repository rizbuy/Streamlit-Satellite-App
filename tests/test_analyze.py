import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "sehat", "message": "API siap memproses data citra satelit"}

def test_upload_bands_missing_index():
    # Mengirim request tanpa parameter form yang dibutuhkan
    response = client.post("/analyze/upload-bands")
    # FastAPI form validation akan mengembalikan 422 Unprocessable Entity
    assert response.status_code == 422

def test_upload_bands_invalid_index():
    # Mengirim index yang tidak ada di registry
    response = client.post(
        "/analyze/upload-bands",
        data={"index_name": "INVALID_INDEX"}
    )
    # Sistem kita melempar 400 untuk index yang tidak dikenal
    assert response.status_code == 400
    assert "tidak dikenal" in response.json()["detail"]
