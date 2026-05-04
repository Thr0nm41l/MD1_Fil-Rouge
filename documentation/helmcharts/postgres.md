# PostgreSQL + pgAdmin Stack

**Helm charts:**
- PostgreSQL: `bitnami/postgresql`
- pgAdmin: `runix/pgadmin4`

**Namespace:** `datalake`
**Values files:** `helmcharts/postgres-values.yaml`, `helmcharts/pgadmin4-values.yaml`

---

## Overview

The `datalake` namespace hosts a shared **PostgreSQL** instance and a web-based **pgAdmin 4** management UI. This PostgreSQL instance is distinct from the internal one bundled inside the Airflow Helm release — it is the project's primary persistent data store.

Grafana connects to this instance as a data source to enable SQL-based dashboard panels.

---

## PostgreSQL

### Configuration

| Parameter | Value |
|---|---|
| Helm chart | `bitnami/postgresql` |
| Release name | `postgres` |
| Persistence | 5 Gi |
| CPU request / limit | 250 m / 1 |
| Memory request / limit | 512 Mi / 2 Gi |

### Users & Databases

| User | Database | Role |
|---|---|---|
| `postgres` | `postgres` | Superuser — full cluster admin |
| `airflow` | `airflow` | Application user — used by DAGs and Grafana |

### In-cluster DNS

```
postgres-postgresql.datalake.svc.cluster.local:5432
```

This hostname is used by all other services (pgAdmin server definitions, Grafana datasource, Airflow connection objects) to reach PostgreSQL.

### Kubernetes Secret

The secret `postgres-credentials` in the `datalake` namespace is created by `start_infra.sh` and referenced by the Helm chart:

| Key | Purpose |
|---|---|
| `postgres-password` | Superuser (`postgres`) password |
| `airflow-db-user` | Airflow DB username (informational) |
| `airflow-password` | Airflow user password |

To retrieve the superuser password at any time:

```bash
kubectl get secret postgres-credentials -n datalake \
  -o jsonpath='{.data.postgres-password}' | base64 -d && echo
```

### Resetting the Superuser Password

If the live password gets out of sync with the secret (e.g. after re-creating the secret without restarting the pod):

```bash
kubectl exec -it postgres-postgresql-0 -n datalake -- \
  psql -U postgres -c "ALTER USER postgres WITH PASSWORD '${POSTGRES_ADMIN_PASSWORD}';"
```

### Installation

```bash
helm install postgres bitnami/postgresql \
  --values helmcharts/postgres-values.yaml \
  -n datalake
```

Wait for readiness:

```bash
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=postgresql -n datalake --timeout=120s
```

### Monitoring

A `ServiceMonitor` (`postgres-servicemonitor`, in `helmcharts/servicemonitors.yaml`) scrapes the PostgreSQL metrics exporter every 30 s.

Useful Grafana dashboard ID: **9628** (PostgreSQL Database).

---

## pgAdmin 4

### Configuration

| Parameter | Value |
|---|---|
| Helm chart | `runix/pgadmin4` |
| Release name | `pgadmin` |
| Listen address / port | `0.0.0.0:80` |
| Persistence | 5 Gi |

### Login

| Field | Value |
|---|---|
| Email | `admin@localhost.io` |
| Password | `PGADMIN_PASSWORD` from `.env` |

### Pre-loaded Server Definitions

pgAdmin ships with two server entries pre-configured so no manual registration is needed:

| Entry | Host | Port | User | Database |
|---|---|---|---|---|
| Airflow PostgreSQL (airflow user) | `postgres-postgresql.datalake.svc.cluster.local` | 5432 | `airflow` | `airflow` |
| PostgreSQL Admin (superuser) | `postgres-postgresql.datalake.svc.cluster.local` | 5432 | `postgres` | `postgres` |

Passwords are **not** stored in the pre-loaded definitions and must be entered on first connection for security reasons.

### Kubernetes Secret

The secret `pgadmin-credentials` in the `datalake` namespace holds the pgAdmin UI password under the key `password`.

### Accessing the UI

```bash
kubectl port-forward svc/pgadmin-pgadmin4 5050:80 -n datalake
```

Then open: [http://localhost:5050](http://localhost:5050)

### Installation

```bash
helm install pgadmin runix/pgadmin4 \
  --values helmcharts/pgadmin4-values.yaml \
  -n datalake
```

---

## Teardown

```bash
helm uninstall pgadmin -n datalake
helm uninstall postgres -n datalake
# To also remove persisted data:
kubectl delete pvc --all -n datalake
```
