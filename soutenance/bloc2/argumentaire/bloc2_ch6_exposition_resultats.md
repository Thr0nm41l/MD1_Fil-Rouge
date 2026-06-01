# BLOC 2 — Chapitre 6 : Exposition des Résultats

> Template sections 6.1 (API de prédiction), 6.2 (Dashboard de visualisation)

---

## 6.1 API de prédiction

### Architecture de l'API FastAPI

**Framework :** FastAPI 0.100+ avec Pydantic v2
**Déploiement :** Kubernetes namespace `datalake` — `helmcharts/apiservice-deployment.yaml`
**Pool de connexions :** `psycopg2.pool.ThreadedConnectionPool` (min=2, max=10) — `apiservice/db.py`
**RLS :** `SET LOCAL app.user_id` injecté via `set_user_context(conn, user_id)` avant chaque requête sensible

### 9 Routers déployés

| Router | Endpoints actifs | Statut | Epic CDC |
|---|---|---|---|
| `containers` | C1–C20 (CRUD, géospatial, filtres par zone/statut) | ✅ | E3 |
| `zones` | Z1–Z5 (CRUD, GeoJSON) | ✅ | E3 |
| `history` | H5–H7 (série temporelle, agrégats par conteneur) | ✅ | E4 |
| `routes` | T1–T9 (CRUD routes + étapes, distance en m via ST_Length) | ✅ | E8 |
| `analytics` | A1–A10 + KPIs + heatmap + choroplèthe | ✅ | E6 |
| `dashboard` | DA3–DA5 (layout config, KPI cards, export snapshot) | ✅ | E7 |
| `gamification` | GAM3–GAM11 (leaderboard, badges, défis) | ⚠️ Stubs | E9 |
| `ml` | ML5 (`POST /ml/predict`) | ⚠️ Stub 503 | E10 |
| `reports` | R4–R5 (`POST /reports/generate`, `GET /reports/{id}/download`) | ⚠️ Stubs | E7 |

### Endpoint ML — `/ml/predict`

**Statut actuel :** stub retournant HTTP 503 (`apiservice/routers/ml.py`)

```python
@router.post("/predict")
def predict_fill_rate(body: PredictRequest):
    raise HTTPException(
        status_code=503,
        detail="ML model not yet trained. Run the ML1–ML4 notebooks..."
    )
```

**Input schema :**
```python
class PredictRequest(BaseModel):
    container_id: int
    horizon_hours: int = 24
```

**Output schema (une fois activé) :**
```json
{
    "container_id": 42,
    "horizon_hours": 24,
    "predicted_fill_rate": 73.5,
    "predicted_at": "2026-06-01T14:30:00",
    "model_version": "hgb_v1.0"
}
```

**Pipeline d'inférence (Online Serving) :**
Le modèle chargé une fois au démarrage du pod (`_load_model()` si `MODEL_PATH` existe), puis pour chaque requête :
1. **Feature extraction** : 5 requêtes SQL pour les lags + rolling + métadonnées conteneur + densité zone
2. **Prediction** : `_model.predict(pd.DataFrame([feats])[_feature_cols])`
3. **Clamping** : `max(0.0, min(100.0, predicted))` — contrainte physique [0, 100]
4. **Persistence** : INSERT dans `ml_predictions` (container_id, horizon_hours, predicted_fill_rate, model_version)

**Déploiement du modèle (Option A recommandée pour soutenance) :**
```dockerfile
COPY ml/models/model.pkl  /ml/models/model.pkl
COPY ml/models/metadata.json /ml/models/metadata.json
ENV MODEL_PATH=/ml/models/model.pkl
```
Rebuild image + `kubectl rollout restart deployment/apiservice -n datalake`

**Documentation Swagger :** `http://api.localhost/docs` (Traefik ingress) — interface OpenAPI auto-générée par FastAPI, incluant les schémas Pydantic et les exemples de réponse.

### Endpoints analytics actifs — Détail technique

#### `GET /analytics/kpis`

6 KPI cards avec valeur courante + variation % vs période précédente :

```python
# Comparaison période courante vs période précédente équivalente
curr = _period_stats(conn, from_dt, to_dt, zone_id)
prev = _period_stats(conn, prev_from, prev_to, zone_id)
# variation = (curr - prev) / prev × 100
```

KPIs exposés : `volume_collected_l`, `collection_count`, `avg_fill_rate_pct`, `overflow_count`, `total_distance_km`, `active_containers`

#### `GET /analytics/choropleth`

GeoJSON polygon par zone avec densité et taux de remplissage moyen — source Leaflet/Mapbox :

```python
SELECT zone_id, zone_name,
       ST_AsGeoJSON(polygon) AS polygon_json,
       density_km2, avg_fill_rate
FROM get_choropleth_data()
```

#### `GET /analytics/heatmap`

Matrice (day_of_week × hour_of_day) des mesures — source heatmap JavaScript :

```python
SELECT day_of_week, hour_of_day, cnt
FROM get_heatmap_data(%s, %s)   -- from_dt, to_dt
```

#### `GET /analytics/costs-roi`

Coût mensuel et économies estimées (optimisation tournées) :

```python
_COST_PER_KM = 1.20   # €/km
_SAVINGS_RATE = 0.20  # 20 % de réduction distance vs baseline non-optimisé
_CO2_PER_KM   = 0.27  # kg CO₂/km (camion de collecte)
```

---

## 6.2 Dashboard de visualisation

### Grafana — Dashboards opérationnels

**Outil :** Grafana (inclus dans `prometheus-community/kube-prometheus-stack`)
**Namespace :** `monitoring`
**Accès :** `http://grafana.localhost` (Traefik ingress)
**Datasources configurées :**
- `Prometheus` — métriques infra (Kubernetes, pods, Redis, PostgreSQL)
- `PostgreSQL` — données métier directement depuis `aggregated_daily_stats` et `fill_history`

**Dashboards disponibles :**

| Dashboard | Source | Métriques |
|---|---|---|
| Infrastructure K8s | Prometheus | CPU/RAM par pod, RestartCount, PVC usage |
| Airflow health | Prometheus (`ServiceMonitor` airflow-webserver) | DAG success/failure rate, task duration |
| PostgreSQL | Prometheus (`postgres-exporter`) | Connexions actives, cache hit ratio, transactions/s |
| Fill history (métier) | PostgreSQL (`aggregated_daily_stats`) | Taux de remplissage moyen par jour, évolution temporelle |
| Alertes actives | AlertManager | Threshold breach count, conteneurs critiques |

### Frontend React — Consommation des endpoints API

Le frontend React (non déployé dans le cluster, mais documenté) consomme les endpoints FastAPI pour les 10 graphiques analytics (A1–A10) du CDC :

| Graphique | Endpoint API | Type |
|---|---|---|
| A1 — Évolution volume collecté | `GET /analytics/volume-evolution` | Stacked area chart |
| A2 — Distribution par type | `GET /analytics/type-distribution` | Donut chart |
| A3 — Collections par zone | `GET /analytics/zone-collections` | Horizontal bar chart |
| A4 — Distribution fill rate | `GET /analytics/fill-distribution` | Histogram |
| A5 — Évolution fill rate | `GET /analytics/fill-evolution?moving_avg=true` | Line chart + MA7 |
| A6 — Performance routes | `GET /analytics/route-performance` | Scatter/bubble chart |
| A7 — Incidents timeline | `GET /analytics/incidents` | Timeline |
| A8 — Heatmap collectes | `GET /analytics/heatmap` | Heatmap (jour × heure) |
| A9 — Carte choroplèthe | `GET /analytics/choropleth` | Leaflet choroplèthe |
| A10 — Coûts et ROI | `GET /analytics/costs-roi` | Mixed bar + line chart |
| DA3 — KPI cards | `GET /analytics/kpis` | KPI cards avec variations |

**Séparation des concerns API vs Dashboard :**
- Grafana = dashboards opérationnels infra + monitoring pipeline (audience : ops/ingénieurs)
- FastAPI = données analytiques métier structurées pour consommation frontend (audience : managers, citoyens, agents)

### Documentation MkDocs

**Accès :** `http://docs.localhost` (namespace `documentation`)
**Contenu :** Documentation technique complète — chaque DAG, chaque phase API, l'architecture K8s, le schéma BDD, les notebooks ML — générée avec MkDocs Material.

---

*Sources : `apiservice/routers/analytics.py`, `apiservice/routers/ml.py`, `documentation/api/phase3-analytics.md`, `documentation/helmcharts/grafana.md`, `ml/ROADMAP.md §ML5`*
