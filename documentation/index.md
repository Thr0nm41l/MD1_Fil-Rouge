# Ecotrack — Documentation

Ecotrack is a smart waste management platform that monitors IoT-connected containers across Lyon districts, orchestrates data pipelines, and exposes metrics through a centralized observability stack.

This documentation covers the full project infrastructure: database schema, data pipelines, Kubernetes deployment, and operational how-to guides.

---

## Architecture Overview

The platform runs on a **Minikube Kubernetes cluster** split across three namespaces:

| Namespace | Contents |
|---|---|
| `airflow` | Workflow orchestration — scheduler, workers, API server |
| `datalake` | PostgreSQL database + pgAdmin management UI |
| `monitoring` | Prometheus, Grafana, AlertManager, Node Exporter |

See [Global K8S Architecture](helmcharts/k8s-architecture.md) for the full deployment diagram.

---

## Sections

### API Service

FastAPI REST API exposing all platform data to frontends, IoT devices, and the ML pipeline.

| Document | Contents |
|---|---|
| [API Overview](api/index.md) | File structure, environment variables, full endpoint status table |
| [Foundation](api/foundation.md) | Connection pool, GeoJSON helpers, pagination, Pydantic schemas |
| [Phase 1 — Containers & Zones](api/phase1-containers-zones.md) | CRUD, soft delete, IoT ingestion, spatial zone queries |
| [Phase 2 — IoT History & Routes](api/phase2-history-routes.md) | Time series, heatmap data, batch import/export, route sheets |
| [Phase 3 — Analytics & Dashboard](api/phase3-analytics.md) | 11 analytics endpoints, choropleth, dashboard config persistence |
| [Phase 4 — Gamification, ML & Reports](api/phase4-gamification-ml-reports.md) | Leaderboard, badges, ML prediction, async PDF/Excel reports |

---

### Data Pipelines (DAGs)

Airflow DAGs running on the `feature/serviceAPI` branch, synced via git-sync every 30 seconds.

| DAG | Purpose |
|---|---|
| [lasc__seed_data](dags/lasc__seed_data.md) | Populates the database with a realistic 30-day dataset (2 000 containers, ~1.44M IoT readings) |
| [masc__clean_xcoms](dags/masc__clean_xcoms.md) | Purges all XCom entries from the Airflow metadata database |
| [test__print_hello](dags/test__print_hello.md) | Smoke test — verifies end-to-end task execution |
| [test_list_tables_from_connection](dags/test_list_tables_from_connection.md) | Validates a PostgreSQL Airflow connection and lists schema tables |

---

### Database

| Document | Contents |
|---|---|
| [Database Architecture](database/setup_complete.md) | Full schema design — 17 OLTP tables, 4 OLAP tables, 5 gamification tables, triggers, RLS policies, PostGIS extensions |

---

### Infrastructure (Helmcharts)

| Document | Contents |
|---|---|
| [Global K8S Architecture](helmcharts/k8s-architecture.md) | Namespace layout, Helm releases, secrets map, PVC inventory, port-forward reference |
| [Airflow](helmcharts/airflow.md) | CeleryExecutor setup, workers, git-sync DAG sync, bundled Redis & PostgreSQL |
| [PostgreSQL + pgAdmin](helmcharts/postgres.md) | Shared datalake database, users, pgAdmin server definitions |
| [Prometheus](helmcharts/prometheus.md) | kube-prometheus-stack, ServiceMonitors, AlertManager, storage |
| [Grafana](helmcharts/grafana.md) | Pre-configured Prometheus & PostgreSQL datasources, Minikube workarounds |

---

### How-to Guides

| Guide | Contents |
|---|---|
| [Monitoring with Prometheus & Grafana](howto/monitoring.md) | PromQL queries, dashboard imports, alert configuration |
| [Grafana PostgreSQL Setup](howto/grafana-postgresql-setup.md) | Datasource configuration, example SQL panels, security recommendations |
| [Kubernetes Secrets](howto/k8s-secrets-doc.md) | Creating, retrieving, rotating, and using secrets in pods |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Thr0nm41l/MD1_Fil-Rouge.git
cd MD1_Fil-Rouge/helmcharts

# 2. Configure credentials
cp .env.example .env
# Edit .env with your passwords

# 3. Start the full infrastructure
./start_infra.sh
```

| Service | Port-forward command | URL |
|---|---|---|
| Airflow | `kubectl port-forward svc/airflow-api-server 8080:8080 -n airflow` | http://localhost:8080 |
| pgAdmin | `kubectl port-forward svc/pgadmin-pgadmin4 5050:80 -n datalake` | http://localhost:5050 |
| Grafana | `kubectl port-forward svc/grafana 3000:80 -n monitoring` | http://localhost:3000 |
| Prometheus | `kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring` | http://localhost:9090 |

```bash
# Tear down
./stop_infra.sh
```
