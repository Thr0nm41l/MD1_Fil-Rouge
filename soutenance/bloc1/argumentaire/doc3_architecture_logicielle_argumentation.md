# Document 3 — Architecture Logicielle : Argumentation de l'Architecture Implémentée

> Ce document met en regard l'architecture Data Lake & Pipelines préconisée par le template M1 DATA avec l'architecture réelle déployée sur le cluster Kubernetes ECOTRACK.

---

## II-A. Architecture Data Lake (3 Layers) — Ce qui a changé et pourquoi

### Proposition du template

Bronze Layer : MinIO, JSON/Parquet, partitionnement `/year/month/day/`, rétention 2 ans.
Silver Layer : Delta Lake (ACID), nettoyage, enrichissement GPS → adresse.
Gold Layer : TimescaleDB, marts pré-calculés (`taux_remplissage`, `tournees_optimisees`).

### Solution implémentée

La structure 3 layers est conservée conceptuellement mais entièrement hébergée dans PostgreSQL 15 :

| Layer template | Équivalent PostgreSQL | Table(s) | Caractéristique clé |
|---|---|---|---|
| Bronze (raw) | `fill_history` | `public.fill_history` | Range partitionnée par mois, `is_outlier` flag |
| Silver (cleaned) | Vues + filtre `NOT is_outlier` | Utilisée dans `aggregate_*` | Filtrage implicite à l'agrégation |
| Gold (aggregated) | `aggregated_hourly_stats`, `aggregated_daily_stats`, `ml_predictions` | 3 tables OLAP | Upsert idempotent par procédures stockées |

**Argument — Partitionnement natif PostgreSQL 15 :**

La table `fill_history` utilise `PARTITION BY RANGE (measured_at)` avec des partitions mensuelles pré-créées pour 2024, 2025 et 2026, plus une partition `_default`. Le composite index `(container_id, measured_at DESC)` couvre le pattern de requête dominant — série temporelle par conteneur — ce qui permet des requêtes < 100ms sur 1,44M lignes (objectif H1 du CDC).

La clé primaire composée `(key_history, measured_at)` est une contrainte PostgreSQL pour les tables partitionnées : la partition key doit figurer dans toute contrainte unique, ce qui explique ce choix documenté dans `documentation/database/setup_complete.md`.

**Argument — Rétention et archivage :**

La stratégie d'archivage retenue est le détachement de partitions (`DETACH PARTITION`), instantané sans DELETE scan, identifié dans `setup_complete.md §"What is intentionally outside the SQL script"` comme tâche de maintenance Airflow future. Cette approche est fonctionnellement équivalente à la politique de rétention Delta Lake.

---

## II-B. Architecture Pipeline ETL — Ce qui a changé et pourquoi

### Proposition du template

Streaming : Kafka (3 brokers, replication 2), Spark Structured Streaming, latence < 2s.
Batch : Airflow (7 DAGs quotidiens), Spark 3.5 (3 workers), Bronze→Silver (2h), Silver→Gold (1h).

### Solution implémentée

L'architecture pipeline repose sur **4 DAGs Airflow** sans Kafka ni Spark :

#### Pipeline de simulation continue (remplace Kafka + Spark Streaming)

**DAG `lasc__livesim_fill`** — schedule `*/10 * * * *`

```
start ──► simulate_fill ──► run_aggregations ──► end
```

- `simulate_fill` : lit `containers.fill_rate` + `device.battery_pct`, calcule le tick suivant (modèle physique par type), insère ~2 000 lignes dans `fill_history` via `execute_values`, batch-update `device.battery_pct`
- `run_aggregations` : appelle `CALL aggregate_hourly(ts)` + `CALL aggregate_daily(day)` pour le tick courant
- Durée par run : **< 5 secondes** pour 2 000 conteneurs
- Triggers SQL actifs : `fill_history_update_container` (sync `containers.fill_rate/status`) et `fill_history_alert` (création `notifications`)

**Argument :** Cette architecture remplace Kafka + Spark Structured Streaming pour une source simulée. Les triggers PostgreSQL fournissent la propagation immédiate des états — équivalent fonctionnel du pipeline Spark avec zéro dépendance supplémentaire.

#### Pipeline de bootstrap (remplace import CSV / batch initial)

**DAG `lasc__seed_data`** — schedule None (manuel)

Graph de tâches : `start → [check_skip_users, seed_zones] → ... → run_aggregations → end`

- Génère 1 440 000 lignes de `fill_history` en ~10 min
- `session_replication_role = 'replica'` désactive les triggers pour le bulk insert
- Post-insert : `UPDATE containers ... FROM (DISTINCT ON container_id, measured_at DESC)` pour resynchroniser les états
- Appelle ensuite `aggregate_hourly` et `aggregate_daily` sur l'ensemble des 30 jours

#### Pipeline opérationnel (remplace les DAGs "collecte" du template)

**DAG `lasc__ops_containers`** — schedule None (API-triggered)

Déclenché par `POST /api/v1/dags/lasc__ops_containers/dagRuns` depuis l'API FastAPI. Deux opérations : `battery` (reset capteur à 100%) et `unload` (vider conteneur + insère dans `collections`). Max 5 runs concurrents pour gérer les appels API simultanés.

**Argument — 4 DAGs vs 7 DAGs quotidiens :**

Le template préconise 7 DAGs quotidiens (Bronze→Silver, Silver→Gold, rapports, etc.). ECOTRACK consolide ces responsabilités :
- Bronze→Silver : implicit (flag `is_outlier` + filtre dans aggregations)
- Silver→Gold : `aggregate_hourly` + `aggregate_daily` en procédures idempotentes appelées par `lasc__livesim_fill` et `lasc__seed_data`
- Rapports : déclenchés à la demande via `POST /reports/generate` (FastAPI BackgroundTasks)

---

## II-C. Architecture Serving — Conforme au template

### API Analytics (FastAPI)

L'API FastAPI est déployée dans le namespace `datalake` via `helmcharts/apiservice-deployment.yaml`. Architecture interne :

| Composant | Implémentation | Fichier |
|---|---|---|
| Pool de connexions | `psycopg2.pool.ThreadedConnectionPool` (min=2, max=10) | `apiservice/db.py` |
| Dépendance FastAPI | `get_db()` → `Depends(get_db)` | `apiservice/db.py` |
| RLS session | `set_user_context(conn, user_id)` → `SET LOCAL app.user_id` | `apiservice/db.py` |
| Sérialisation GeoJSON | `geojson_feature()`, `geojson_collection()` (via `ST_AsGeoJSON`) | `apiservice/utils.py` |
| Pagination | `paginate_query()` → `LIMIT/OFFSET` + `COUNT(*)` séparé | `apiservice/utils.py` |

**9 routers déployés :**

| Router | Endpoints actifs | Épics couverts |
|---|---|---|
| `containers` | C1–C20 | E3 |
| `zones` | Z1–Z5 | E3 |
| `history` | H5–H7 | E4 |
| `routes` | T1–T9 | E8 |
| `analytics` | A1–A10 + KPIs | E6 |
| `dashboard` | DA3–DA5 | E7 |
| `gamification` | GAM3–GAM11 (stubs) | E9 |
| `ml` | ML5 (stub 503) | E10 |
| `reports` | R4–R5 (stubs) | E7 |

### Dashboards BI

La datasource PostgreSQL de Grafana interroge directement `aggregated_daily_stats` et `fill_history` en SQL, couvrant les dashboards opérationnels en temps réel avec refresh configurable. Les 10 graphiques analytics (A1–A10) du CDC sont exposés via FastAPI et consommés par le frontend.

---

## II-D. Data Quality & Observability — Ce qui a changé et pourquoi

### Proposition du template

Great Expectations (tests qualité automatisés quotidiens), alertes si qualité < 95%, lineage Bronze → Silver → Gold, profiling statistique automatique.

### Solution implémentée

| Aspect qualité | Template | Implémentation | Mécanisme |
|---|---|---|---|
| Validation à l'ingestion | Pydantic + Great Expectations | Contraintes SQL + Pydantic schemas | `CHECK`, `NOT NULL`, `UNIQUE`, FK |
| Détection outliers | Great Expectations | Flag `is_outlier BOOLEAN` | 1 % des mesures simulées, filtré en agrégation |
| Alertes seuil dépassé | Monitoring Great Expectations | Trigger `fill_history_alert` | `AFTER INSERT` → `notifications` |
| Lineage | Tracking Bronze→Silver→Gold | Implicit (partitions → aggregations) | DAG graph Airflow + stored procedures |
| Profiling | Monte Carlo / GE | `pg_stat_statements` (extension activée) | Tracking perf requêtes en continu |

**Argument :** `pg_stat_statements` est activé dans `setup_complete.sql` §2 Extensions, ce qui couvre le benchmark des requêtes (tâche G10, TEST3 du CDC). Les contraintes SQL (`fill_rate BETWEEN 0 AND 100`, `status IN (...)`) rejettent les données invalides dès l'insertion, éliminant le besoin d'une couche Great Expectations séparée sur le périmètre de 2 000 capteurs simulés.

---

## III. Schémas d'Architecture — Synthèse de l'implémenté

### Architecture globale (5 namespaces Kubernetes)

```
┌─── airflow ────────────────────┐   ┌─── datalake ──────────────────┐
│  Scheduler + 2 Workers Celery  │   │  PostgreSQL 15 + PostGIS      │
│  Redis (task queue)            │   │  pgAdmin 4                    │
│  DAGs : seed_data, livesim,    │◄──┤  FastAPI (9 routers)          │
│         ops_containers,        │   │  (apiservice deployment)      │
│         clean_xcoms            │   └───────────────────────────────┘
└────────────────────────────────┘
┌─── monitoring ────────────────────────────────────┐
│  Prometheus + AlertManager + Node Exporter        │
│  Grafana (datasource PostgreSQL + Prometheus)     │
└───────────────────────────────────────────────────┘
┌─── traefik ──────┐   ┌─── documentation ──────┐
│  Ingress Traefik │   │  MkDocs (docs.localhost)│
└──────────────────┘   └─────────────────────────┘
```

### Flux de données end-to-end

```
lasc__livesim_fill (*/10 min)
        │
        ▼ execute_values (~2 000 rows)
fill_history (partitioned by month)
        │ AFTER INSERT triggers
        ├──► containers.fill_rate / status / last_updated
        ├──► notifications (threshold breach)
        │
        ▼ CALL aggregate_hourly / aggregate_daily
aggregated_hourly_stats / aggregated_daily_stats
        │
        ▼ SQL queries (ThreadedConnectionPool)
FastAPI /analytics/* endpoints ──► Frontend (React)
                                ──► Grafana dashboards
```

---

## IV. Scalabilité et Performance — Objectifs et résultats mesurés

| Objectif template | Valeur cible | Résultat implémenté | Source |
|---|---|---|---|
| Temps réponse API | < 200ms P95 | Pool psycopg2 (max=10), requêtes sur agrégats | `apiservice/db.py` |
| Latence ingestion | < 2s end-to-end | < 5s pour 2 000 conteneurs / tick | `documentation/dags/lasc__livesim_fill.md` |
| Requêtes spatiales | < 200ms sur 2 000 conteneurs | GIST index sur `containers.location` + `zones.polygon` | `setup_complete.sql` §9 Indexes |
| Qualité données | > 95% | Contraintes SQL + `is_outlier` filter | `setup_complete.sql` §11 Triggers |
| Disponibilité | 99,5% | Kubernetes + Celery (retry=1 sur `livesim_fill`) | `helmcharts/airflow-values.yaml` |

---

*Fichier d'argumentation — Document 3 Architecture Logicielle / filière M1 DATA & ANALYTICS*
*Sources : `documentation/helmcharts/k8s-architecture.md`, `documentation/dags/lasc__livesim_fill.md`, `documentation/api/foundation.md`, `documentation/api/phase3-analytics.md`, `documentation/database/setup_complete.md`*
