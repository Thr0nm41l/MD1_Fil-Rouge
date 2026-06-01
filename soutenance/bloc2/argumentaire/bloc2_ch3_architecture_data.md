# BLOC 2 — Chapitre 3 : Architecture Data

> Template sections 3.1 (architecture en couches), 3.2 (Feature Store)

---

## 3.1 Architecture en couches et flux de données

### Vue d'ensemble — Cluster Kubernetes (5 namespaces)

```
┌─── airflow ────────────────────┐   ┌─── datalake ──────────────────┐
│  Scheduler + 2 Workers Celery  │   │  PostgreSQL 15 + PostGIS      │
│  Redis (task queue)            │   │  pgAdmin 4                    │
│  DAGs : seed_data, livesim,    │◄──┤  FastAPI (9 routers)          │
│         ops_containers,        │   │  (apiservice deployment)      │
│         clean_xcoms            │   └───────────────────────────────┘
└────────────────────────────────┘
┌─── monitoring ─────────────────────────────────────┐
│  Prometheus + AlertManager + Node Exporter         │
│  Grafana (datasources : PostgreSQL + Prometheus)   │
└────────────────────────────────────────────────────┘
┌─── traefik ──────┐   ┌─── documentation ──────┐
│  Ingress Traefik │   │  MkDocs (docs.localhost)│
└──────────────────┘   └─────────────────────────┘
```

**6 Helm releases :** postgresql (bitnami), pgadmin (runix), airflow (apache), kube-prometheus-stack (prometheus-community), traefik (traefik), mkdocs (custom)
**Storage total :** ~22 Gi PVC `hostPath` Minikube
**DNS interne :** `postgres-postgresql.datalake.svc.cluster.local:5432`

### Couche Bronze — Ingestion brute

**Table :** `public.fill_history`

| Caractéristique | Valeur |
|---|---|
| Partitionnement | `PARTITION BY RANGE (measured_at)` — 36 partitions mensuelles (2024–2026) + `_default` |
| Clé primaire | `(key_history, measured_at)` — partition key obligatoire dans toute contrainte unique |
| Séquence | `BIGINT DEFAULT nextval('fill_history_key_seq')` avec `CACHE 100` |
| Volume actuel | ~1,44 M lignes (30 jours × 2 000 conteneurs × ~144 ticks/jour) |
| Flag qualité | `is_outlier BOOLEAN DEFAULT false` — 1 % des mesures simulées flaggées |
| Idempotence | `ON CONFLICT DO NOTHING` sur `(container_id, measured_at)` arrondi à la minute |

**Index Bronze :**
```sql
-- Pattern dominant : série temporelle par conteneur (H5 du CDC)
CREATE INDEX fill_history_container_time_idx
    ON fill_history (container_id, measured_at DESC);
-- Partitiel — outliers courants
CREATE INDEX fill_history_outlier_idx
    ON fill_history (container_id, measured_at DESC)
    WHERE is_outlier = true;
```

**Triggers actifs sur Bronze :**
- `fill_history_update_container` (AFTER INSERT) : synchronise `containers.fill_rate`, `status`, `last_updated`
- `fill_history_alert` (AFTER INSERT) : génère une `notification` si `fill_rate > fill_threshold_pct`

### Couche Silver — Nettoyage et enrichissement

La Silver Layer est implicite — elle n'est pas matérialisée en table séparée mais appliquée à l'agrégation :

```sql
-- Filtre Silver dans CALL aggregate_hourly(ts)
WHERE NOT is_outlier
  AND c.is_active = true
```

L'enrichissement géospatial est assuré via JOIN `containers → zones` lors des requêtes d'agrégation, et automatiquement via le trigger `containers_assign_zone` (BEFORE INSERT/UPDATE sur `containers.location`) qui résout `zone_id` par `ST_Within(location, polygon)`.

**Validation Pydantic (Silver à l'ingestion API) :**
```python
class MeasureCreate(BaseModel):
    fill_rate: float = Field(..., ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=-50, le=80)
    battery_pct: Optional[float] = Field(None, ge=0, le=100)
```

### Couche Gold — Agrégats KPIs

**Tables Gold :**

| Table | Granularité | Contenu | Upsert |
|---|---|---|---|
| `aggregated_hourly_stats` | (container_id, bucket_hour) | avg/min/max_fill_rate, measurement_count | `ON CONFLICT (container_id, bucket_hour) DO UPDATE` |
| `aggregated_daily_stats` | (container_id, day_bucket) | avg/min/max_fill_rate, overflow_count, collection_count | `ON CONFLICT (container_id, day_bucket) DO UPDATE` |
| `ml_predictions` | (container_id, predicted_at) | predicted_fill_rate, actual_fill_rate, model_version | INSERT |

**Procédures idempotentes :**
```sql
CALL aggregate_hourly(ts TIMESTAMP);   -- upsert sur l'heure du tick
CALL aggregate_daily(day DATE);        -- upsert sur le jour du tick
```

Appelées après chaque tick par le DAG `lasc__livesim_fill` (`run_aggregations` task) et après le bootstrap par `lasc__seed_data` sur l'ensemble des 30 jours.

### Flux de données end-to-end

```
Sources IoT (simulées)
        │
        ▼ execute_values (psycopg2.extras)
Bronze : fill_history (PARTITION BY measured_at)
        │ AFTER INSERT triggers
        ├──► containers.fill_rate / status / last_updated   [Silver propagation]
        ├──► notifications (threshold breach)
        │
        ▼ CALL aggregate_hourly / aggregate_daily
Gold : aggregated_hourly_stats / aggregated_daily_stats
        │
        ▼ ThreadedConnectionPool (max=10)
FastAPI /analytics/* → Frontend React + Grafana
```

**Partitionnement et archivage :**
La stratégie d'archivage future repose sur `DETACH PARTITION` (partition pruning instantané, sans DELETE scan), documentée dans `documentation/database/setup_complete.md §"What is intentionally outside the SQL script"`. Cette approche est fonctionnellement équivalente à la politique de rétention Delta Lake.

---

## 3.2 Feature Store et gestion des features

### Feature Store custom — `training_features.parquet`

Le projet n'utilise pas de Feature Store dédié (Feast, Tecton, Hopsworks) mais implémente une solution custom basée sur un fichier Parquet versionnée dans `ml/data/`.

| Aspect Feature Store | Implémentation ECOTRACK |
|---|---|
| **Stockage** | `ml/data/training_features.parquet` — sortie du notebook `01_eda_feature_engineering.ipynb` |
| **Versionnage** | Implicite par date de run (`trained_at` dans `metadata.json`) |
| **Features calculées** | 14 features (voir tableau ci-dessous) |
| **Point d'accès** | Lecture directe via `pd.read_parquet()` dans les notebooks d'entraînement |
| **Partage projets** | Non applicable — périmètre mono-projet |

### Catalogue des 14 features

| Famille | Feature | Type | Source |
|---|---|---|---|
| Temporelles | `hour` | int | `measured_at.dt.hour` |
| Temporelles | `day_of_week` | int | `measured_at.dt.dayofweek` |
| Temporelles | `day_of_month` | int | `measured_at.dt.day` |
| Temporelles | `is_weekend` | binary | `day_of_week >= 5` |
| Temporelles | `is_peak_hour` | binary | `hour ∈ {7,8,9,17,18,19}` |
| Lags | `fill_rate_1h_ago` | float | `shift(6)` — 6 ticks × 10 min |
| Lags | `fill_rate_24h_ago` | float | `shift(144)` |
| Lags | `fill_rate_7d_ago` | float | `shift(1008)` |
| Rolling | `fill_rate_24h_avg` | float | `rolling(144, min_periods=12).mean()` |
| Rolling | `fill_rate_7d_avg` | float | `rolling(1008, min_periods=144).mean()` |
| Rolling | `fill_rate_change_rate` | float | `(fill_rate - shift(6)) / 6` — Δ/tick |
| Conteneur | `capacity_liters` | float | `containers.capacity_liters` |
| Conteneur | `type_id` | int | `containers.type_id` |
| Géospatiale | `density_km2` | float | `COUNT(containers) / ST_Area(polygon) × 1e6` |

**Variable cible :** `fill_rate` à T+24h, matérialisée par `g.shift(-144)` (144 ticks × 10 min = 24 h).

### Gestion du Feature Store à l'inférence

À l'inférence (endpoint `/ml/predict`), les features ne sont pas lues depuis le Parquet mais recalculées en temps réel depuis la base :

```python
# Lag features — lookup des 5 dernières valeurs significatives
SELECT fill_rate FROM fill_history
WHERE container_id = %(id)s AND measured_at <= NOW() - INTERVAL '55 min'
ORDER BY measured_at DESC LIMIT 1   -- fill_rate_1h_ago
```

Cette approche (Online Feature Serving) garantit la cohérence entre les features d'entraînement et d'inférence, au prix de 5 requêtes SQL par prédiction. Le pipeline de feature engineering est entièrement documenté dans `ml/ROADMAP.md §ML1`.

---

*Sources : `database/setup_complete.sql`, `documentation/helmcharts/k8s-architecture.md`, `ml/ROADMAP.md`, `ml/models/metadata.json`, `apiservice/routers/ml.py`*
