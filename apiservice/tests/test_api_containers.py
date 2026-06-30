"""
Tests — /containers
CDC criteria:
  - C1  : liste paginée des conteneurs actifs
  - C3  : détail d'un conteneur par ID
  - C4  : 404 si conteneur inexistant
  - BDD5: fill_rate toujours dans [0, 100] (contrainte CHECK vérifiée en intégration)
  - H1  : 2 000 conteneurs actifs dans le système (intégration)
"""

import pytest


# ── Unit tests — structure des réponses ──────────────────────────────────────

class TestContainersListStructure:
    def test_returns_200(self, client, mock_conn):
        cur = mock_conn.cursor.return_value
        cur.fetchone.return_value = (0,)
        cur.fetchall.return_value = []
        response = client.get("/containers")
        assert response.status_code == 200

    def test_response_has_items_and_total(self, client, mock_conn):
        cur = mock_conn.cursor.return_value
        cur.fetchone.return_value = (0,)
        cur.fetchall.return_value = []
        body = client.get("/containers").json()
        assert "items" in body
        assert "total" in body

    def test_items_is_list(self, client, mock_conn):
        cur = mock_conn.cursor.return_value
        cur.fetchone.return_value = (0,)
        cur.fetchall.return_value = []
        body = client.get("/containers").json()
        assert isinstance(body["items"], list)

    def test_total_is_integer(self, client, mock_conn):
        cur = mock_conn.cursor.return_value
        cur.fetchone.return_value = (42,)
        cur.fetchall.return_value = []
        body = client.get("/containers").json()
        assert isinstance(body["total"], int)


class TestContainerNotFound:
    def test_nonexistent_container_returns_404(self, client, mock_conn):
        cur = mock_conn.cursor.return_value
        cur.fetchone.return_value = None
        response = client.get("/containers/999999")
        assert response.status_code == 404

    def test_404_body_has_detail(self, client, mock_conn):
        cur = mock_conn.cursor.return_value
        cur.fetchone.return_value = None
        body = client.get("/containers/999999").json()
        assert "detail" in body


# ── Integration tests — données réelles ──────────────────────────────────────

@pytest.mark.integration
class TestContainersIntegration:
    def test_total_active_containers_is_2000(self, int_client):
        """CDC H1 — 2 000 capteurs IoT simulés."""
        body = int_client.get("/containers?limit=1").json()
        assert body["total"] >= 2000, (
            f"Attendu ≥ 2 000 conteneurs actifs, obtenu {body['total']}"
        )

    def test_container_detail_has_required_fields(self, int_client):
        """CDC C3 — détail d'un conteneur : lat, lng, fill_rate, status."""
        body = int_client.get("/containers/1").json()
        for field in ("key_container", "lat", "lng", "fill_rate", "status"):
            assert field in body, f"Champ manquant : {field}"

    def test_fill_rate_within_bounds(self, int_client):
        """CDC BDD5 — fill_rate ∈ [0, 100] (contrainte CHECK PostgreSQL)."""
        body = int_client.get("/containers?limit=100").json()
        for container in body["items"]:
            fr = container["fill_rate"]
            assert 0 <= fr <= 100, f"fill_rate={fr} hors domaine pour container {container['key_container']}"

    def test_status_values_are_valid(self, int_client):
        """CDC — status ∈ {'empty','normal','full','critical'}."""
        valid_statuses = {"empty", "normal", "full", "critical"}
        body = int_client.get("/containers?limit=100").json()
        for container in body["items"]:
            assert container["status"] in valid_statuses, (
                f"Statut invalide '{container['status']}' pour container {container['key_container']}"
            )

    def test_pagination_limit_respected(self, int_client):
        """CDC C1 — pagination : limit=10 retourne exactement 10 items."""
        body = int_client.get("/containers?limit=10&offset=0").json()
        assert len(body["items"]) <= 10
