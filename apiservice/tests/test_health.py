"""
Tests — GET /health
CDC criterion: API disponible, réponse structurée (Epic E5).
"""


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body_structure(client):
    body = client.get("/health").json()
    assert "status" in body
    assert body["status"] == "ok"


def test_health_message_present(client):
    body = client.get("/health").json()
    assert "message" in body
    assert isinstance(body["message"], str)
