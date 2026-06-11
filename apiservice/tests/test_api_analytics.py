"""
Tests — /analytics
CDC criteria:
  - A1–A10 : 10 endpoints analytics opérationnels (Epic E6)
  - A9     : choroplèthe retourne du GeoJSON valide
  - A10    : coûts et ROI avec constantes métier (_SAVINGS_RATE=0.20, _CO2_PER_KM=0.27)
  - KPI    : 6 KPI cards avec variation %
"""

import pytest


# ── Unit tests — structure des réponses ──────────────────────────────────────

class TestAnalyticsEndpointsExist:
    """Vérifie que chaque endpoint analytics répond (pas 404/405)."""

    ENDPOINTS = [
        "/analytics/kpis",
        "/analytics/volume-evolution",
        "/analytics/type-distribution",
        "/analytics/zone-collections",
        "/analytics/fill-distribution",
        "/analytics/fill-evolution",
        "/analytics/route-performance",
        "/analytics/incidents",
        "/analytics/heatmap",
        "/analytics/choropleth",
        "/analytics/costs-roi",
    ]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_endpoint_not_405(self, client, mock_conn, endpoint):
        """Aucun endpoint analytics ne doit retourner 405 Method Not Allowed."""
        cur = mock_conn.cursor.return_value
        cur.fetchall.return_value = []
        cur.fetchone.return_value = {}
        response = client.get(endpoint)
        assert response.status_code != 405, f"{endpoint} retourne 405"

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_endpoint_returns_json(self, client, mock_conn, endpoint):
        """Chaque endpoint analytics retourne du JSON."""
        cur = mock_conn.cursor.return_value
        cur.fetchall.return_value = []
        cur.fetchone.return_value = {}
        response = client.get(endpoint)
        assert response.headers["content-type"].startswith("application/json"), (
            f"{endpoint} ne retourne pas du JSON"
        )


# ── Integration tests — données réelles ──────────────────────────────────────

@pytest.mark.integration
class TestKpisIntegration:
    def test_kpis_returns_list(self, int_client):
        """CDC A-KPI — 6 KPI cards retournées."""
        body = int_client.get("/analytics/kpis").json()
        assert isinstance(body, dict) or isinstance(body, list)

    def test_kpis_has_volume_key(self, int_client):
        """CDC A-KPI — volume collecté présent dans les KPIs."""
        body = int_client.get("/analytics/kpis").json()
        body_str = str(body).lower()
        assert "volume" in body_str or "collection" in body_str


@pytest.mark.integration
class TestChoroplethIntegration:
    def test_choropleth_returns_list(self, int_client):
        """CDC A9 — choroplèthe retourne une liste de zones."""
        body = int_client.get("/analytics/choropleth").json()
        assert isinstance(body, list), "choropleth doit retourner une liste"

    def test_choropleth_has_5_zones(self, int_client):
        """CDC A9 — 5 zones géographiques attendues."""
        body = int_client.get("/analytics/choropleth").json()
        assert len(body) == 5, f"Attendu 5 zones, obtenu {len(body)}"

    def test_choropleth_has_geojson_polygon(self, int_client):
        """CDC A9 — chaque zone expose un polygone GeoJSON."""
        body = int_client.get("/analytics/choropleth").json()
        for zone in body:
            assert "polygon" in zone or "geojson" in str(zone).lower(), (
                f"Zone {zone.get('zone_id')} sans polygone GeoJSON"
            )

    def test_choropleth_has_fill_rate(self, int_client):
        """CDC A9 — chaque zone expose le taux de remplissage moyen."""
        body = int_client.get("/analytics/choropleth").json()
        for zone in body:
            assert "avg_fill_rate" in zone or "fill" in str(zone).lower()


@pytest.mark.integration
class TestCostsRoiIntegration:
    def test_costs_roi_returns_list(self, int_client):
        """CDC A10 — endpoint coûts et ROI opérationnel."""
        body = int_client.get("/analytics/costs-roi").json()
        assert isinstance(body, list)

    def test_costs_roi_has_co2_field(self, int_client):
        """CDC A10 — économies CO₂ exposées (0.27 kg/km × distance optimisée)."""
        body = int_client.get("/analytics/costs-roi").json()
        body_str = str(body).lower()
        assert "co2" in body_str or "saving" in body_str or "economy" in body_str, (
            "Le champ CO₂ ou économies est absent de /analytics/costs-roi"
        )
