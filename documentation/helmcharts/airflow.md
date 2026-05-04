# Apache Airflow Stack

**Helm chart:** `apache-airflow/airflow`
**Namespace:** `airflow`
**Values file:** `helmcharts/airflow-values.yaml`

---

## Overview

Airflow orchestrates the project's data pipelines (DAGs). It is deployed with the **CeleryExecutor**, which distributes task execution across a pool of worker pods backed by a Redis message broker. DAGs are continuously synced from the project's Git repository — no manual file copy is needed.

---

## Components

| Component | Replicas | Description |
|---|---|---|
| **Webserver / API Server** | 1 | Web UI (`svc/airflow-api-server`, NodePort) and REST API |
| **Scheduler** | 1 | Parses DAGs, schedules task instances, and triggers them |
| **Workers** | 2 | Celery workers that execute tasks; each can run 4 tasks concurrently |
| **Triggerer** | 1 | Handles deferrable operators (async sensors) |
| **Git-Sync sidecar** | per pod | Continuously pulls DAGs from GitHub every 30 s |
| **PostgreSQL** (subchart) | 1 | Metadata database (task state, connections, variables) |
| **Redis** (subchart) | 1 | Celery broker — queues tasks between the scheduler and workers |

### Subchart: PostgreSQL

The Airflow release embeds a **Bitnami PostgreSQL** subchart scoped to the `airflow` namespace. It is separate from the shared PostgreSQL instance in the `datalake` namespace.

| Parameter | Value |
|---|---|
| User | `airflow` |
| Database | `airflow` |
| Persistence | 3 Gi |
| CPU request / limit | 250 m / 500 m |
| Memory request / limit | 256 Mi / 512 Mi |

### Subchart: Redis

| Parameter | Value |
|---|---|
| Persistence | disabled (in-memory broker only) |
| CPU request / limit | 100 m / 500 m |
| Memory request / limit | 256 Mi / 512 Mi |

### Workers

| Parameter | Value |
|---|---|
| Replicas | 2 |
| Concurrency per worker | 4 tasks |
| CPU request / limit | 250 m / 1 |
| Memory request / limit | 512 Mi / 2 Gi |

---

## DAG Synchronisation (Git-Sync)

DAGs are not baked into the image. A `git-sync` sidecar container clones and continuously refreshes the repository at runtime.

| Parameter | Value |
|---|---|
| Repository | `https://github.com/Thr0nm41l/MD1_Fil-Rouge.git` |
| Branch | `feature/serviceAPI` |
| Revision | `HEAD` |
| Sub-path | `dags/` |
| Poll interval | 30 s |

To list currently loaded DAGs:

```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- ls /opt/airflow/dags
```

To use a **private repository**, create a credentials secret and reference it:

```bash
kubectl create secret generic git-credentials \
  --from-literal=username=git \
  --from-literal=password=<GITHUB_TOKEN> \
  -n airflow
```

Then add `credentialsSecret: git-credentials` to the `gitSync` block in `airflow-values.yaml`.

---

## Additional Python Packages

The following packages are installed at pod startup via `_PIP_ADDITIONAL_REQUIREMENTS`:

| Package | Purpose |
|---|---|
| `faker` | Generating synthetic seed data in DAGs |
| `bcrypt` | Password hashing in seed DAGs |

---

## Kubernetes Secrets

All sensitive values are injected through Kubernetes secrets created by `start_infra.sh`:

| Secret name | Namespace | Key(s) | Used by |
|---|---|---|---|
| `airflow-fernet-key` | airflow | `fernet-key` | Encrypts connection credentials stored in the metadata DB — **must never change** after first deploy |
| `airflow-metadata-credentials` | airflow | `connection` | SQLAlchemy connection string to the bundled PostgreSQL |
| `airflow-result-backend-credentials` | airflow | `connection` | Celery result backend connection string |
| `airflow-postgres-credentials` | airflow | `postgres-password`, `password` | Bitnami PostgreSQL subchart initialisation |

The API secret key is passed at install time via `--set apiSecretKey="${AIRFLOW_API_KEY}"`.

---

## Accessing the UI

```bash
kubectl port-forward svc/airflow-api-server 8080:8080 -n airflow
```

Then open: [http://localhost:8080](http://localhost:8080)

Default credentials: `admin` / `admin` (change after first login).

---

## Installation

```bash
# Ensure secrets exist (run start_infra.sh, or create them manually)
helm install airflow apache-airflow/airflow \
  --values helmcharts/airflow-values.yaml \
  --set apiSecretKey="${AIRFLOW_API_KEY}" \
  --timeout 15m \
  -n airflow
```

Wait for the API server pod to be ready:

```bash
kubectl wait --for=condition=ready pod -l component=api-server -n airflow --timeout=300s
```

---

## Monitoring

A `ServiceMonitor` in `helmcharts/servicemonitors.yaml` configures Prometheus to scrape the Airflow webserver's `/metrics` endpoint (port `airflow-ui`) every 30 s.

Useful Grafana dashboard IDs: **12058** (Apache Airflow).

---

## Useful Queries

```promql
# Active Airflow task instances by state
airflow_task_instance_state

# Scheduler heartbeat
airflow_scheduler_heartbeat
```

---

## Teardown

```bash
helm uninstall airflow -n airflow
# To also remove persisted data:
kubectl delete pvc --all -n airflow
```
