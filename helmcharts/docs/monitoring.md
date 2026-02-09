# Monitoring with Prometheus and Grafana

## Overview

This document explains how to configure and use Prometheus and Grafana to monitor the MD1 infrastructure.

**Architecture:** Prometheus and Grafana are deployed as **separate Helm releases** for better flexibility and independent lifecycle management.

### Installed Components

1. **Prometheus** (separate chart): Monitoring and alerting system that collects and stores metrics
2. **Grafana** (separate chart): Visualization platform for creating dashboards
3. **AlertManager**: Alert manager included with Prometheus
4. **Node Exporter**: Exports system metrics (CPU, memory, disk)
5. **Kube State Metrics**: Exports Kubernetes resource metrics

### Quick Start Guides

- **[Prometheus Quick Start](prometheus-quickstart.md)** - Get started with metrics collection
- **[Grafana Quick Start](grafana-quickstart.md)** - Create dashboards and visualizations
- **[Grafana PostgreSQL Setup](grafana-postgresql-setup.md)** - Connect to your database

## Installation

Prometheus and Grafana installation is automatic when running `start_infra.sh`.

To install manually:

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus (without bundled Grafana)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --values prometheus-values.yaml \
  --namespace monitoring

# Apply ServiceMonitors for applications
kubectl apply -f servicemonitors.yaml

# Install Grafana separately
helm install grafana grafana/grafana \
  --values grafana-values.yaml \
  --namespace monitoring
```

**Why separate deployments?**
- ✅ Independent lifecycle management
- ✅ Update/restart one without affecting the other
- ✅ Better resource management and scaling
- ✅ Cleaner architecture

## Accessing the Interfaces

### Grafana

Grafana provides dashboards to visualize metrics. It's deployed separately from Prometheus.

```bash
# Forward Grafana port
kubectl port-forward svc/grafana 3000:80 --namespace monitoring
```

Then access: http://localhost:3000

**Default credentials:**
- Username: `admin`
- Password: `Gr@f@n@Admin123`

**Pre-configured datasources:**
- Prometheus (metrics)
- PostgreSQL (application data)

See [grafana-quickstart.md](grafana-quickstart.md) for detailed usage.

### Prometheus

Prometheus exposes its PromQL query interface.

```bash
# Forward Prometheus port
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring
```

Then access: http://localhost:9090

### AlertManager

AlertManager manages Prometheus alerts.

```bash
# Forward AlertManager port
kubectl port-forward svc/prometheus-kube-prometheus-alertmanager 9093:9093 --namespace monitoring
```

Then access: http://localhost:9093

## Available Metrics

### Kubernetes Metrics

- **Pods**: State, restarts, CPU/memory usage
- **Nodes**: CPU, memory, disk, network usage
- **Deployments**: Replica status, availability
- **Services**: Endpoint status

### Application Metrics

#### PostgreSQL
- Active connections count
- Database sizes
- Queries per second
- Query duration

#### Redis
- Memory usage
- Key count
- Cache hit/miss ratio
- Client connections

#### Airflow
- DAG states
- Task duration
- Failed tasks
- Available workers

## Recommended Grafana Dashboards

### Pre-installed Dashboards

The `kube-prometheus` stack includes several default dashboards:

1. **Kubernetes / Compute Resources / Cluster**: Cluster overview
2. **Kubernetes / Compute Resources / Namespace (Pods)**: Metrics per namespace
3. **Node Exporter / Nodes**: Detailed node metrics

### Dashboards to Import

Grafana.com offers community dashboards. Here are useful IDs:

- **1860**: Node Exporter Full
- **7362**: Kubernetes Cluster Monitoring
- **9628**: PostgreSQL Database
- **11835**: Redis Dashboard
- **12058**: Apache Airflow

To import a dashboard:
1. Go to Grafana → Dashboards → Import
2. Enter the dashboard ID
3. Select Prometheus datasource
4. Click Import

## Useful PromQL Queries

### Pod CPU Usage
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="airflow"}[5m])) by (pod)
```

### Pod Memory Usage
```promql
sum(container_memory_working_set_bytes{namespace="airflow"}) by (pod)
```

### Pods in Error
```promql
kube_pod_status_phase{phase="Failed"} > 0
```

### PostgreSQL Connections
```promql
pg_stat_database_numbackends{datname="postgres"}
```

### Redis Hit Ratio
```promql
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
```

## Configuring Alerts

Alerts are configured in Prometheus. To add a custom alert:

1. Create a `custom-alerts.yaml` file:

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
        description: "Pod {{ $labels.pod }} is using {{ $value }} bytes of memory"
```

2. Apply the configuration:
```bash
kubectl apply -f custom-alerts.yaml
```

## Data Retention

By default, Prometheus retains metrics for **15 days** (configurable in `prometheus-values.yaml`).

To modify retention:

```yaml
prometheus:
  prometheusSpec:
    retention: 30d  # Change to 30 days
```

## Storage

Prometheus and Grafana data is persisted via PersistentVolumeClaims (PVC):

- **Prometheus**: 10Gi
- **Grafana**: 5Gi
- **AlertManager**: 2Gi

To check volumes:
```bash
kubectl get pvc -n monitoring
```

## Troubleshooting

### Prometheus Not Collecting Metrics

1. Check that pods are running:
```bash
kubectl get pods -n monitoring
```

2. Check Prometheus targets:
   - Go to Prometheus UI → Status → Targets
   - Verify that targets are "UP"

3. Check ServiceMonitors:
```bash
kubectl get servicemonitors -n datalake
kubectl get servicemonitors -n airflow
```

### Grafana Cannot Connect to Prometheus

1. Check datasource in Grafana:
   - Configuration → Data Sources → Prometheus
   - Test the connection

2. Verify Prometheus is accessible:
```bash
kubectl get svc -n monitoring | grep prometheus
```

### Alerts Not Being Sent

1. Check alert rules:
```bash
kubectl get prometheusrules -n monitoring
```

2. Check AlertManager:
   - Go to AlertManager UI → Status

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Kube-Prometheus-Stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
