# Prometheus Quick Start Guide

## What You Get

After running `./start_infra.sh`, you'll have:

✅ **Prometheus** - Collects and stores metrics from all your infrastructure
✅ **AlertManager** - Alerts you when things go wrong
✅ **Node Exporter** - System-level metrics (CPU, memory, disk)
✅ **Kube State Metrics** - Kubernetes cluster metrics
✅ **ServiceMonitors** - Automatic discovery of PostgreSQL, Redis, and Airflow

> **Note:** Grafana is deployed separately. See [grafana-quickstart.md](grafana-quickstart.md) for Grafana setup and usage.

## Quick Access

### 1. Start Your Infrastructure
```bash
cd helmcharts
./start_infra.sh
```

This will automatically install:
- PostgreSQL
- Redis
- pgAdmin
- Airflow
- **Prometheus** (metrics collection)
- **Grafana** (visualization - deployed separately)

### 2. Access Prometheus UI

Prometheus has a built-in web interface for querying metrics and viewing targets.

Open a new terminal and run:
```bash
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring
```

Then open: http://localhost:9090

### 3. Verify Metrics Collection

In Prometheus UI:

**Check Targets:**
1. Go to **Status** → **Targets**
2. All targets should show status **UP**
3. You should see:
   - Kubernetes API server
   - Node exporters
   - Kube state metrics
   - PostgreSQL (if metrics enabled)
   - Redis (if metrics enabled)
   - Airflow pods

**Check Service Discovery:**
1. Go to **Status** → **Service Discovery**
2. See all discovered Kubernetes services

### 4. Test a Query

In Prometheus UI, try these queries:

**Total pods in cluster:**
```promql
count(kube_pod_info)
```

**CPU usage by namespace:**
```promql
sum(rate(container_cpu_usage_seconds_total[5m])) by (namespace)
```

**Memory usage by pod:**
```promql
sum(container_memory_working_set_bytes) by (pod, namespace)
```

## What Metrics Are Available?

### Infrastructure Metrics
- **CPU Usage** - per pod, per node, per namespace
- **Memory Usage** - current usage, limits, requests
- **Disk I/O** - read/write operations
- **Network Traffic** - ingress/egress bandwidth

### Application Metrics
- **PostgreSQL** - connections, query performance, database size
- **Redis** - memory usage, cache hit ratio, operations per second
- **Airflow** - DAG runs, task duration, worker health

### Kubernetes Metrics
- **Pod Status** - running, pending, failed pods
- **Container Restarts** - track stability
- **Resource Requests vs Limits** - capacity planning
- **Node Health** - ready vs not-ready nodes

## Example: Monitor Your Airflow Tasks

In Prometheus UI (http://localhost:9090), go to **Graph** and try this query:

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="airflow"}[5m])) by (pod)
```

This shows CPU usage for all Airflow pods averaged over 5 minutes.

For better visualization with dashboards, see Grafana: [grafana-quickstart.md](grafana-quickstart.md)

## Setting Up Alerts

Create a file `custom-alerts.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: airflow-alerts
  namespace: monitoring
spec:
  groups:
  - name: airflow
    interval: 30s
    rules:
    - alert: AirflowHighCPU
      expr: rate(container_cpu_usage_seconds_total{namespace="airflow"}[5m]) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Airflow pod {{ $labels.pod }} high CPU"
        description: "CPU usage is above 80% for 5 minutes"
```

Apply it:
```bash
kubectl apply -f custom-alerts.yaml
```

## Common Tasks

### Check What Prometheus is Monitoring

**View all targets:**
```bash
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring
```
Go to: http://localhost:9090/targets

All targets should show status **UP**.

**View configuration:**
Go to: http://localhost:9090/config

**View service discovery:**
Go to: http://localhost:9090/service-discovery

### Check Prometheus Storage

**View storage usage:**
```bash
kubectl get pvc -n monitoring
```

**Check Prometheus disk usage:**
In Prometheus UI, run:
```promql
prometheus_tsdb_storage_blocks_bytes
```

### Manage Prometheus

**Restart Prometheus:**
```bash
kubectl rollout restart statefulset/prometheus-prometheus-kube-prometheus-prometheus -n monitoring
```

**View Prometheus logs:**
```bash
kubectl logs -f statefulset/prometheus-prometheus-kube-prometheus-prometheus -n monitoring
```

**Check Prometheus configuration is valid:**
```bash
kubectl exec -it statefulset/prometheus-prometheus-kube-prometheus-prometheus -n monitoring -- promtool check config /etc/prometheus/prometheus.yml
```

## Troubleshooting

### Prometheus Not Collecting Metrics

**Check Prometheus is running:**
```bash
kubectl get pods -n monitoring | grep prometheus
```

**Check targets status:**
```bash
# Port-forward and visit http://localhost:9090/targets
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring
```

Look for targets in **DOWN** state and check their error messages.

**Check ServiceMonitors:**
```bash
kubectl get servicemonitors --all-namespaces
```

### Prometheus Pod Not Starting

**Check logs:**
```bash
kubectl logs -n monitoring prometheus-prometheus-kube-prometheus-prometheus-0
```

**Check disk space:**
```bash
kubectl get pvc -n monitoring
kubectl describe pvc prometheus-prometheus-kube-prometheus-prometheus-db-prometheus-prometheus-kube-prometheus-prometheus-0 -n monitoring
```

**Common issues:**
- Insufficient disk space → Increase PVC size in `prometheus-values.yaml`
- Configuration errors → Check PrometheusRules and ServiceMonitors syntax

### Metrics Missing for Applications

**PostgreSQL/Redis metrics not showing:**

1. Check ServiceMonitors exist:
```bash
kubectl get servicemonitors -n datalake
kubectl get servicemonitors -n airflow
```

2. Verify services have metrics endpoints:
```bash
kubectl describe svc postgres-postgresql -n datalake
kubectl describe svc redis -n datalake
```

3. Check if metrics endpoints are accessible:
```bash
kubectl exec -it postgres-postgresql-0 -n datalake -- curl localhost:9187/metrics
```

### High Memory/CPU Usage

**Check Prometheus resource usage:**
```bash
kubectl top pod -n monitoring | grep prometheus
```

**Reduce retention period** in `prometheus-values.yaml`:
```yaml
prometheus:
  prometheusSpec:
    retention: 7d  # Instead of 15d
```

**Limit scrape frequency** for non-critical metrics in ServiceMonitors.

## Next Steps

1. **Set up Grafana dashboards**: See [grafana-quickstart.md](grafana-quickstart.md) for visualization
2. **Customize retention**: Edit `prometheus-values.yaml` to change data retention period
3. **Add custom alerts**: Create PrometheusRule resources for your specific needs
4. **Configure notifications**: Set up AlertManager to send alerts to Slack, email, etc.
5. **Learn PromQL**: Master Prometheus query language for complex queries

## Useful PromQL Queries

**Kubernetes Metrics:**
```promql
# Total pods per namespace
count(kube_pod_info) by (namespace)

# Pods not in Running state
kube_pod_status_phase{phase!="Running"} > 0

# Pods with high restart count
rate(kube_pod_container_status_restarts_total[15m]) > 0
```

**Resource Usage:**
```promql
# CPU usage by pod
sum(rate(container_cpu_usage_seconds_total[5m])) by (pod, namespace)

# Memory usage by pod
sum(container_memory_working_set_bytes) by (pod, namespace)

# Disk usage
node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100
```

**Application Metrics:**
```promql
# Airflow pods
sum(up{namespace="airflow"}) by (pod)

# PostgreSQL connections (if exporter enabled)
pg_stat_database_numbackends

# Redis memory usage (if exporter enabled)
redis_memory_used_bytes
```

## Related Documentation

- [Grafana Quick Start](grafana-quickstart.md) - Visualizing metrics with dashboards
- [Grafana PostgreSQL Setup](grafana-postgresql-setup.md) - Connecting to your database
- [Complete Monitoring Guide](monitoring.md) - Detailed monitoring documentation
- [Prometheus Official Documentation](https://prometheus.io/docs/)
