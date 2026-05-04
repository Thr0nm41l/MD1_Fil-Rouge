# Prometheus Stack

**Helm chart:** `prometheus-community/kube-prometheus-stack`
**Namespace:** `monitoring`
**Values file:** `helmcharts/prometheus-values.yaml`
**ServiceMonitors:** `helmcharts/servicemonitors.yaml`

---

## Overview

Prometheus is the metrics collection and alerting backbone of the infrastructure. It is deployed via the `kube-prometheus-stack` chart, which bundles Prometheus, AlertManager, Node Exporter, and Kube State Metrics into a single release.

Grafana is **not** included in this release — it is deployed as a separate Helm chart to allow independent lifecycle management. See [grafana.md](grafana.md).

---

## Components

| Component | Enabled | Description |
|---|---|---|
| **Prometheus** | Yes | Time-series metrics store and PromQL query engine |
| **AlertManager** | Yes | Receives alerts from Prometheus and routes/deduplicates them |
| **Node Exporter** | Yes | Exports host-level metrics: CPU, memory, disk, network |
| **Kube State Metrics** | Yes | Exports Kubernetes object metrics: pod states, deployments, etc. |
| **Kube API Server** | Yes | Monitors the Kubernetes API server |
| **Kubelet** | Yes | Monitors kubelet metrics (including cAdvisor container metrics) |
| **CoreDNS** | Yes | Monitors DNS resolution health |
| **Controller Manager** | No | Not accessible in Minikube |
| **Scheduler** | No | Not accessible in Minikube |
| **Etcd** | No | Not accessible in Minikube |
| **Grafana** | No | Deployed separately (`grafana/grafana` chart) |

---

## Storage

| Resource | Size |
|---|---|
| Prometheus PVC | 5 Gi (`ReadWriteOnce`) |
| AlertManager PVC | 2 Gi |
| Metrics retention | 7 days |

---

## Service Discovery

The following flags are set to allow Prometheus to discover **all** `ServiceMonitor` and `PodMonitor` resources in the cluster, regardless of which Helm release created them:

```yaml
serviceMonitorSelectorNilUsesHelmValues: false
podMonitorSelectorNilUsesHelmValues: false
```

Without this, Prometheus would only scrape targets from monitors carrying the chart's own labels.

---

## ServiceMonitors

Custom `ServiceMonitor` resources in `helmcharts/servicemonitors.yaml` extend Prometheus scraping to the application namespaces:

| Monitor | Namespace | Selector | Port | Path | Interval |
|---|---|---|---|---|---|
| `postgres-servicemonitor` | `datalake` | `app.kubernetes.io/name: postgresql` | `metrics` | (default) | 30 s |
| `redis-servicemonitor` | `datalake` | `app.kubernetes.io/name: redis` | `metrics` | (default) | 30 s |
| `airflow-servicemonitor` | `airflow` | `component: webserver` | `airflow-ui` | `/metrics` | 30 s |

Apply or re-apply them with:

```bash
kubectl apply -f helmcharts/servicemonitors.yaml
```

---

## Accessing the UI

```bash
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring
```

Open: [http://localhost:9090](http://localhost:9090)

### AlertManager

```bash
kubectl port-forward svc/prometheus-kube-prometheus-alertmanager 9093:9093 -n monitoring
```

Open: [http://localhost:9093](http://localhost:9093)

---

## Installation

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --values helmcharts/prometheus-values.yaml \
  -n monitoring

kubectl apply -f helmcharts/servicemonitors.yaml
```

Wait for readiness:

```bash
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s
```

---

## Useful PromQL Queries

### Cluster resources

```promql
# CPU usage by pod (airflow namespace)
sum(rate(container_cpu_usage_seconds_total{namespace="airflow"}[5m])) by (pod)

# Memory usage by pod (airflow namespace)
sum(container_memory_working_set_bytes{namespace="airflow"}) by (pod)

# Pods not running
kube_pod_status_phase{phase=~"Failed|Unknown"} > 0
```

### PostgreSQL

```promql
# Active connections per database
pg_stat_database_numbackends

# Transactions per second
rate(pg_stat_database_xact_commit[5m]) + rate(pg_stat_database_xact_rollback[5m])
```

### Redis

```promql
# Cache hit ratio
rate(redis_keyspace_hits_total[5m]) /
  (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

# Memory usage
redis_memory_used_bytes
```

---

## Adding Custom Alerts

Create a `PrometheusRule` resource:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: custom-alerts
  namespace: monitoring
spec:
  groups:
  - name: custom
    interval: 30s
    rules:
    - alert: HighMemoryUsage
      expr: container_memory_usage_bytes{namespace="airflow"} > 1e9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.pod }} using high memory"
```

```bash
kubectl apply -f custom-alerts.yaml
```

---

## Teardown

```bash
helm uninstall prometheus -n monitoring
kubectl delete -f helmcharts/servicemonitors.yaml
# To also remove persisted data:
kubectl delete pvc --all -n monitoring
```
