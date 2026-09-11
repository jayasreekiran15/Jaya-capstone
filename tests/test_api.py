# tests/test_api.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Assuming the FastAPI app instance is named 'app' and imported from src.api
from api.main import app

client = TestClient(app)

def test_ask_rejects_missing_question():
    # Act
    response = client.post("/ask", json={})
    
    # Assert
    assert response.status_code == 422
    
    # Ensure the error detail points to the missing 'question' field
    errors = response.json().get("detail", [])
    assert any("question" in err.get("loc", []) for err in errors)

def test_health_returns_ok():
    # Act
    response = client.get("/health")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
