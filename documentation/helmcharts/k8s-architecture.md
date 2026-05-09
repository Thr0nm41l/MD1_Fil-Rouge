# Kubernetes Architecture

This document describes the overall Kubernetes architecture of the MD1 Fil-Rouge infrastructure as deployed on Minikube.

---

## Cluster

The entire infrastructure runs on a **single-node Minikube cluster**. All workloads are co-located on that node; there is no node affinity or inter-node scheduling at this stage.

### Prerequisites

| Tool | Minimum version |
|---|---|
| Docker Engine | 29.1.3 |
| Minikube | 1.48 |
| kubectl | 1.15 |
| Helm | 4.1.0 |

The `metrics-server` Minikube addon must be enabled for Airflow worker autoscaling:

```bash
minikube addons enable metrics-server
```

---

## Namespace Layout

The cluster is divided into five namespaces, each grouping related concerns:

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Minikube Cluster                            │
│                                                                      │
│  ┌──────────────────────┐  ┌───────────────────────────────────────┐ │
│  │  airflow             │  │  datalake                             │ │
│  ├──────────────────────┤  ├───────────────────────────────────────┤ │
│  │ • API Server         │  │ • PostgreSQL (bitnami)                │ │
│  │ • Scheduler          │  │ • pgAdmin 4 (runix)                   │ │
│  │ • Workers (×2)       │  │ • API Service                         │ │
│  │ • Triggerer          │  │                                       │ │
│  │ • [PostgreSQL]       │  │ (internal sub-services:)              │ │
│  │ • [Redis]            │  │                                       │ │
│  └──────────────────────┘  └───────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  monitoring                                                 │     │
│  ├─────────────────────────────────────────────────────────────┤     │
│  │ • Prometheus          • Grafana                             │     │
│  │ • AlertManager        • Node Exporter                       │     │
│  │ • Kube State Metrics                                        │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌─────────────────────┐  ┌────────────────────────────────────┐     │
│  │  traefik            │  │  documentation                     │     │
│  ├─────────────────────┤  ├────────────────────────────────────┤     │
│  │ • Traefik (ingress) │  │ • MkDocs                           │     │
│  └─────────────────────┘  └────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

| Namespace | Purpose |
|---|---|
| `airflow` | Workflow orchestration and DAG execution |
| `datalake` | Persistent data store, database management UI, and API service |
| `monitoring` | Metrics collection, alerting, and visualization |
| `traefik` | Ingress controller — routes all external HTTP traffic |
| `documentation` | MkDocs documentation site |

---

## Helm Releases

| Release name | Chart | Namespace | Description |
|---|---|---|---|
| `traefik` | `traefik/traefik` | `traefik` | Ingress controller — single entry point for all HTTP traffic |
| `postgres` | `bitnami/postgresql` | `datalake` | Shared project PostgreSQL instance |
| `pgadmin` | `runix/pgadmin4` | `datalake` | Web UI for PostgreSQL administration |
| `airflow` | `apache-airflow/airflow` | `airflow` | Full Airflow deployment (includes bundled PostgreSQL + Redis subcharts) |
| `prometheus` | `prometheus-community/kube-prometheus-stack` | `monitoring` | Metrics collection, AlertManager, Node Exporter, Kube State Metrics |
| `grafana` | `grafana/grafana` | `monitoring` | Dashboard and visualization layer |

Two additional workloads are deployed directly with `kubectl apply` (no Helm release):

| Workload | Namespace | Description |
|---|---|---|
| `apiservice` | `datalake` | Custom REST API service |
| `mkdocs` | `documentation` | MkDocs documentation site |

---

## Inter-Service Communication

All cross-namespace communication uses Kubernetes in-cluster DNS (`<service>.<namespace>.svc.cluster.local`). External access from the developer machine goes through Traefik, which is exposed as a `LoadBalancer` service and made reachable via `sudo minikube tunnel`.

### Key DNS endpoints

| Service | DNS | Port |
|---|---|---|
| PostgreSQL (datalake) | `postgres-postgresql.datalake.svc.cluster.local` | 5432 |
| Airflow PostgreSQL (internal) | `airflow-postgresql.airflow.svc.cluster.local` | 5432 |
| Prometheus | `prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local` | 9090 |
| Airflow API server | `airflow-api-server.airflow.svc.cluster.local` | 8080 |

### Data flow

```
GitHub (git-sync)
        │
        ▼ DAGs
┌───────────────┐     task queue      ┌──────────┐
│  Scheduler    │ ──────────────────► │  Redis   │
└───────┬───────┘                     └─────┬────┘
        │ task state                        │ consume
        ▼                                   ▼
┌───────────────┐                    ┌───────────────┐
│  Airflow PG   │                    │   Workers     │
│  (metadata)   │◄───────────────────│   (×2)        │
└───────────────┘   write results    └───────────────┘

┌───────────────┐     SQL queries     ┌───────────────┐
│  DAGs / tasks │ ──────────────────► │  PostgreSQL   │
│               │                     │  (datalake)   │
└───────────────┘                     └───────┬───────┘
                                              │
                                    ┌─────────▼──────┐
                                    │   pgAdmin 4    │
                                    └────────────────┘

┌───────────────────────────────────────────────────────┐
│                    monitoring namespace               │
│                                                       │
│  Prometheus ◄── ServiceMonitors (postgres, redis,     │
│      │           airflow webserver)                   │
│      │          Node Exporter, Kube State Metrics     │
│      ▼                                                │
│  AlertManager        Grafana ◄── Prometheus datasource│
│                              ◄── PostgreSQL datasource│
└───────────────────────────────────────────────────────┘
```

---

## Kubernetes Secrets

All credentials originate from the `.env` file (never committed to Git) and are materialised as Kubernetes `Opaque` secrets by `start_infra.sh` using `--dry-run=client | kubectl apply` for idempotency.

| Secret | Namespace | Consumer |
|---|---|---|
| `postgres-credentials` | datalake | `bitnami/postgresql` chart |
| `pgadmin-credentials` | datalake | `runix/pgadmin4` chart |
| `airflow-postgres-credentials` | airflow | Airflow bundled PostgreSQL subchart |
| `airflow-metadata-credentials` | airflow | Airflow metadata DB connection |
| `airflow-result-backend-credentials` | airflow | Celery result backend |
| `airflow-fernet-key` | airflow | Airflow connection encryption |
| `grafana-admin-credentials` | monitoring | Grafana UI login |
| `grafana-datasource-credentials` | monitoring | Grafana → PostgreSQL datasource password |

The `.env.example` file documents all required variables:

```
POSTGRES_ADMIN_PASSWORD   — PostgreSQL superuser password
AIRFLOW_DB_USER           — Airflow DB username
AIRFLOW_DB_PASSWORD       — Airflow DB password
AIRFLOW_FERNET_KEY        — Fernet key (stable across restarts)
AIRFLOW_API_KEY           — Airflow REST API secret
PGADMIN_EMAIL             — pgAdmin login email
PGADMIN_PASSWORD          — pgAdmin login password
GRAFANA_ADMIN_USER        — Grafana admin username
GRAFANA_ADMIN_PASSWORD    — Grafana admin password
```

---

## Persistent Volumes

All stateful workloads use `PersistentVolumeClaims`. On Minikube, these are backed by `hostPath` volumes on the node.

| Workload | Namespace | PVC size |
|---|---|---|
| PostgreSQL (datalake) | datalake | 5 Gi |
| pgAdmin 4 | datalake | 5 Gi |
| Airflow bundled PostgreSQL | airflow | 3 Gi |
| Prometheus | monitoring | 5 Gi |
| AlertManager | monitoring | 2 Gi |
| Grafana | monitoring | 2 Gi |

**Total provisioned storage: ~22 Gi**

To inspect all PVCs:

```bash
kubectl get pvc --all-namespaces
```

To delete all PVCs (destructive — removes all persisted data):

```bash
kubectl delete pvc --all -n datalake
kubectl delete pvc --all -n airflow
kubectl delete pvc --all -n monitoring
```

---

## Observability Architecture

Prometheus is the single source of truth for metrics. Its service discovery is unrestricted (`serviceMonitorSelectorNilUsesHelmValues: false`), so it picks up `ServiceMonitor` objects from all namespaces.

```
datalake namespace          airflow namespace
┌──────────────┐            ┌──────────────┐
│ PostgreSQL   │──metrics──►│              │
│ Redis        │──metrics──►│              │
└──────────────┘            │  Airflow     │
                            │  webserver   │──metrics──┐
                            └──────────────┘           │
                                                        ▼
                                             ┌──────────────────┐
                                             │   Prometheus     │
                                             │  (monitoring)    │
                                             └────────┬─────────┘
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    ▼                 ▼                 ▼
                              AlertManager         Grafana        PromQL UI
```

Grafana has two datasources active simultaneously:
- **Prometheus** — for all time-series metrics (infrastructure + application)
- **PostgreSQL** — for direct SQL queries against the datalake, enabling mixed metric/data dashboards

---

## Developer Access

All UIs are reachable via hostname-based routing through Traefik. Run this once in a separate terminal to expose the LoadBalancer:

```bash
sudo minikube tunnel
```

| Service | URL |
|---|---|
| Airflow UI | http://airflow.localhost |
| pgAdmin | http://pgadmin.localhost |
| Grafana | http://grafana.localhost |
| Prometheus | http://prometheus.localhost |
| API Service | http://api.localhost |
| MkDocs | http://docs.localhost |
| Traefik dashboard | http://traefik.localhost/dashboard/ |

### Fallback: port-forward

If Traefik is unavailable, services can still be reached directly:

| Service | Command | URL |
|---|---|---|
| Airflow UI | `kubectl port-forward svc/airflow-api-server 8080:8080 -n airflow` | http://localhost:8080 |
| pgAdmin | `kubectl port-forward svc/pgadmin-pgadmin4 5050:80 -n datalake` | http://localhost:5050 |
| Grafana | `kubectl port-forward svc/grafana 3000:80 -n monitoring` | http://localhost:3000 |
| Prometheus | `kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring` | http://localhost:9090 |
| AlertManager | `kubectl port-forward svc/prometheus-kube-prometheus-alertmanager 9093:9093 -n monitoring` | http://localhost:9093 |

---

## Lifecycle Management

### Start the full infrastructure

```bash
cd helmcharts/
cp .env.example .env   # first time only — fill in credentials
./start_infra.sh
```

The script: validates `.env`, creates all namespaces and secrets, adds Helm repos, installs all Helm releases in dependency order (Traefik first), deploys the API service and MkDocs, applies `ServiceMonitors` and Ingress rules, and waits for each critical pod to be ready.

### Stop and uninstall

```bash
./stop_infra.sh
```

Uninstalls all five Helm releases and deletes the `ServiceMonitors`. PVCs are **not** deleted automatically — data is preserved unless explicitly removed.

---

## Stack Documentation Index

| Stack | File |
|---|---|
| Traefik | [traefik.md](traefik.md) |
| Apache Airflow | [airflow.md](airflow.md) |
| PostgreSQL + pgAdmin | [postgres.md](postgres.md) |
| Prometheus | [prometheus.md](prometheus.md) |
| Grafana | [grafana.md](grafana.md) |
