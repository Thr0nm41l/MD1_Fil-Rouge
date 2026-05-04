# Grafana Stack

**Helm chart:** `grafana/grafana`
**Namespace:** `monitoring`
**Values file:** `helmcharts/grafana-values.yaml`

---

## Overview

Grafana provides the visualization layer for the infrastructure. It is deployed as a **separate Helm release** from the Prometheus stack, enabling independent updates and restarts without affecting metrics collection.

It comes pre-configured with two datasources:
- **Prometheus** — for infrastructure and application metrics
- **PostgreSQL** — for SQL-based panels querying the datalake directly

---

## Configuration

| Parameter | Value |
|---|---|
| Helm chart | `grafana/grafana` |
| Release name | `grafana` |
| Persistence | 2 Gi |
| CPU request / limit | 100 m / 500 m |
| Memory request / limit | 128 Mi / 512 Mi |

### Minikube-specific Workarounds

The default Grafana chart runs an `initChownData` init-container that calls `chown` on the data volume. On Minikube's `hostPath` storage class this fails with "operation not permitted". Two workarounds are applied:

| Setting | Value | Reason |
|---|---|---|
| `initChownData.enabled` | `false` | Disables the failing init-container |
| `securityContext` (runAs/fsGroup) | `472` | Grafana's default UID/GID — ensures the main container can write without `chown` |

---

## Datasources

Both datasources are provisioned declaratively and are available immediately after startup.

### Prometheus

| Field | Value |
|---|---|
| UID | `prometheus` |
| URL | `http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090` |
| Access mode | proxy |
| Default datasource | Yes |
| Scrape interval | 30 s |

### PostgreSQL

| Field | Value |
|---|---|
| UID | `postgresql` |
| URL | `postgres-postgresql.datalake.svc.cluster.local:5432` |
| User | `postgres` (superuser) |
| Database | `airflow` |
| SSL mode | `disable` |
| Password injection | Via env var `${POSTGRES_ADMIN_PASSWORD}` (from secret `grafana-datasource-credentials`) |

The PostgreSQL password is **never hardcoded** in the values file. Grafana expands `${POSTGRES_ADMIN_PASSWORD}` at runtime using the environment variable injected from the `grafana-datasource-credentials` Kubernetes secret.

---

## Kubernetes Secrets

Two secrets in the `monitoring` namespace are required before installation:

| Secret | Key(s) | Purpose |
|---|---|---|
| `grafana-admin-credentials` | `admin-user`, `admin-password` | Grafana UI login credentials |
| `grafana-datasource-credentials` | `POSTGRES_ADMIN_PASSWORD` | Injected as env var for the PostgreSQL datasource password |

Both are created by `start_infra.sh` from the `.env` file.

To retrieve the admin password manually:

```bash
kubectl get secret grafana-admin-credentials -n monitoring \
  -o jsonpath='{.data.admin-password}' | base64 -d && echo
```

---

## Accessing the UI

```bash
kubectl port-forward svc/grafana 3000:80 -n monitoring
```

Then open: [http://localhost:3000](http://localhost:3000)

Credentials: `admin` / your `GRAFANA_ADMIN_PASSWORD` from `.env`.

---

## Installation

```bash
# Ensure secrets exist first (start_infra.sh handles this)
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install grafana grafana/grafana \
  --values helmcharts/grafana-values.yaml \
  -n monitoring
```

Wait for readiness:

```bash
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s
```

---

## Recommended Community Dashboards

Import these from Grafana → Dashboards → Import using the numeric ID:

| ID | Dashboard |
|---|---|
| 1860 | Node Exporter Full |
| 7362 | Kubernetes Cluster Monitoring |
| 9628 | PostgreSQL Database |
| 11835 | Redis Dashboard |
| 12058 | Apache Airflow |

The default `kube-prometheus-stack` dashboards (cluster overview, per-namespace compute resources, node exporter) are pre-installed by Prometheus and visible in Grafana automatically.

---

## Teardown

```bash
helm uninstall grafana -n monitoring
# To also remove persisted dashboards/config:
kubectl delete pvc --all -n monitoring
```
