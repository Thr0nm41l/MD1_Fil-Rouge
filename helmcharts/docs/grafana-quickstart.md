# Grafana Quick Start Guide

## What is Grafana?

Grafana is a visualization and analytics platform that allows you to create beautiful dashboards for your metrics and data. In this setup, Grafana is deployed **separately** from Prometheus for better flexibility and independent lifecycle management.

## What You Get

After running `./start_infra.sh`, Grafana is automatically configured with:

✅ **Pre-configured Datasources:**
- **Prometheus** - Infrastructure and application metrics
- **PostgreSQL** - Your application database for business metrics

✅ **Ready to Use:**
- Admin account set up
- Persistent storage (5Gi)
- Additional plugins installed

## Quick Access

### 1. Start Port Forward

Open a terminal and run:
```bash
kubectl port-forward svc/grafana 3000:80 --namespace monitoring
```

### 2. Login to Grafana

Open your browser and go to: http://localhost:3000

**Login credentials:**
- Username: `admin`
- Password: `Gr@f@n@Admin123`

### 3. Verify Datasources

1. Click the **gear icon** (⚙️) → **Data Sources**
2. You should see two datasources already configured:
   - **Prometheus** (default)
   - **PostgreSQL**
3. Click **Test** on each to verify connectivity

## Your First Dashboard

### Option 1: Import a Pre-built Dashboard

Grafana has thousands of community dashboards. Here are the best ones for this stack:

1. Click **Dashboards** (four squares icon) → **Import**
2. Enter one of these dashboard IDs:
   - **1860** - Node Exporter Full (detailed system metrics)
   - **7249** - Kubernetes Cluster (overview)
   - **9628** - PostgreSQL Database
   - **11835** - Redis Dashboard
   - **12058** - Apache Airflow
3. Click **Load**
4. Select **Prometheus** as the datasource
5. Click **Import**

### Option 2: Create Your Own Dashboard

**Create a simple CPU usage panel:**

1. Click **Dashboards** → **New Dashboard** → **Add visualization**
2. Select **Prometheus** as the datasource
3. In the query editor, enter:
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="airflow"}[5m])) by (pod)
```
4. In the right panel:
   - **Title**: Airflow Pod CPU Usage
   - **Visualization**: Time series
5. Click **Apply**
6. Click **Save dashboard** (disk icon at top)

## Pre-configured Datasources

### Prometheus Datasource

**What it provides:**
- Infrastructure metrics (CPU, memory, disk, network)
- Kubernetes cluster metrics
- Pod and container metrics
- ServiceMonitor metrics (PostgreSQL, Redis, Airflow)

**Example queries:**
```promql
# Memory usage by namespace
sum(container_memory_working_set_bytes) by (namespace)

# Pods in error state
kube_pod_status_phase{phase="Failed"} > 0

# Database connections
pg_stat_database_numbackends
```

### PostgreSQL Datasource

**What it provides:**
- Direct access to your application database
- Business metrics and application data
- Custom analytics

**Example queries:**
```sql
-- Records created per hour
SELECT
  date_trunc('hour', created_at) as time,
  count(*) as count
FROM your_table
WHERE $__timeFilter(created_at)
GROUP BY 1
ORDER BY 1

-- Current statistics
SELECT
  NOW() as time,
  count(*) as total_records
FROM your_table
```

See [grafana-postgresql-setup.md](grafana-postgresql-setup.md) for detailed PostgreSQL usage.

## Essential Grafana Features

### Time Range Picker

Top right corner - select the time range for your data:
- Last 5 minutes / 15 minutes / 1 hour / 6 hours / 24 hours / 7 days
- Custom range
- **Refresh**: Auto-refresh every 5s, 10s, 30s, 1m, etc.

### Variables

Create dynamic dashboards with dropdown filters:

1. Go to **Dashboard settings** (gear icon)
2. **Variables** → **Add variable**
3. Example variable - **Namespace**:
   - Name: `namespace`
   - Type: Query
   - Data source: Prometheus
   - Query: `label_values(kube_pod_info, namespace)`
4. Use in queries: `{namespace="$namespace"}`

### Explore Mode

Test queries before adding them to dashboards:

1. Click **Explore** (compass icon)
2. Select **Prometheus** or **PostgreSQL**
3. Write and test your query
4. Click **Add to dashboard** when ready

## Common Dashboard Panels

### Panel 1: System Overview

**Title:** Cluster CPU Usage
**Query (Prometheus):**
```promql
sum(rate(container_cpu_usage_seconds_total[5m]))
```
**Visualization:** Stat (single number)

### Panel 2: Pod Memory Usage

**Title:** Memory by Namespace
**Query (Prometheus):**
```promql
sum(container_memory_working_set_bytes) by (namespace)
```
**Visualization:** Time series (line chart)

### Panel 3: Database Activity

**Title:** PostgreSQL Active Connections
**Query (Prometheus):**
```promql
pg_stat_database_numbackends
```
**Visualization:** Time series

### Panel 4: Application Data

**Title:** Records Processed (Last 24h)
**Query (PostgreSQL):**
```sql
SELECT
  date_trunc('hour', created_at) as time,
  count(*) as "Records"
FROM your_table
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1
```
**Visualization:** Bar chart

### Panel 5: Airflow Task Status

**Title:** Airflow Pods
**Query (Prometheus):**
```promql
count(kube_pod_info{namespace="airflow"}) by (pod)
```
**Visualization:** Table

## Example Dashboard Layout

Here's a recommended dashboard structure:

```
┌─────────────────────────────────────────────────────┐
│ Cluster Overview Dashboard                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Row 1: High-Level Stats                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│ │Total Pods│ │ CPU %    │ │Memory %  │ │Disk %   ││
│ └──────────┘ └──────────┘ └──────────┘ └─────────┘│
│                                                      │
│ Row 2: Resource Usage Over Time                     │
│ ┌────────────────────────────────────────────────┐ │
│ │  CPU Usage by Namespace (Time Series)          │ │
│ └────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────┐ │
│ │  Memory Usage by Namespace (Time Series)       │ │
│ └────────────────────────────────────────────────┘ │
│                                                      │
│ Row 3: Application Metrics                          │
│ ┌────────────────┐ ┌──────────────────────────────┐│
│ │ Airflow Tasks  │ │  Database Connections        ││
│ │ (Stat)         │ │  (Time Series)               ││
│ └────────────────┘ └──────────────────────────────┘│
│                                                      │
│ Row 4: Business Metrics (PostgreSQL)                │
│ ┌────────────────────────────────────────────────┐ │
│ │  Records Processed (Bar Chart)                 │ │
│ └────────────────────────────────────────────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Alerting in Grafana

Grafana can send alerts based on your data:

### Create an Alert

1. Edit a panel
2. Go to **Alert** tab
3. Click **Create alert rule from this panel**
4. Set conditions:
   - **WHEN**: `avg()` of query `A`
   - **IS ABOVE**: `80` (for example, 80% CPU)
   - **FOR**: `5m` (alert after 5 minutes)
5. Add notification channel (email, Slack, etc.)

### Configure Notification Channels

1. **Alerting** (bell icon) → **Notification channels**
2. Click **Add channel**
3. Choose type (Email, Slack, Webhook, etc.)
4. Configure and test

## Organizing Dashboards

### Folders

1. **Dashboards** → **New folder**
2. Create folders like:
   - Infrastructure
   - Applications
   - Business Metrics
3. Move dashboards into folders

### Tags

Add tags to dashboards for easy filtering:
- `kubernetes`
- `postgresql`
- `airflow`
- `production`

## Performance Tips

### 1. Use Time Filters

Always use `$__timeFilter()` in PostgreSQL queries:
```sql
WHERE $__timeFilter(created_at)
```

### 2. Limit Data Points

For large datasets, use aggregation:
```promql
# Instead of all pods:
sum(rate(container_cpu_usage_seconds_total[5m])) by (namespace)
# Group by namespace only
```

### 3. Cache Settings

For slow queries:
1. Edit panel
2. **Query options** → **Cache timeout**: `300` (5 minutes)

### 4. Use Variables

Instead of creating multiple similar dashboards, use variables to make one dynamic dashboard.

## Common Tasks

### Export a Dashboard

1. Open dashboard
2. **Share** (export icon) → **Export** → **Save to file**
3. Save JSON file

### Import a Dashboard

1. **Dashboards** → **Import**
2. **Upload JSON file** or paste JSON
3. Select datasources
4. Click **Import**

### Reset Admin Password

If you forget the password:
```bash
kubectl exec -it deployment/grafana -n monitoring -- grafana-cli admin reset-admin-password newpassword
```

### Check Grafana Logs

```bash
kubectl logs -f deployment/grafana -n monitoring
```

### Restart Grafana

```bash
kubectl rollout restart deployment/grafana -n monitoring
```

## Troubleshooting

### Cannot Connect to Grafana

**Check pod is running:**
```bash
kubectl get pods -n monitoring | grep grafana
```

**Check logs:**
```bash
kubectl logs deployment/grafana -n monitoring
```

**Verify service:**
```bash
kubectl get svc grafana -n monitoring
```

### Datasource Connection Failed

**Prometheus datasource:**
- Check Prometheus is running: `kubectl get pods -n monitoring | grep prometheus`
- Verify service name: `prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local`

**PostgreSQL datasource:**
- Check PostgreSQL is running: `kubectl get pods -n datalake | grep postgres`
- Verify credentials in datasource settings

### Dashboards Show "No Data"

1. Check time range (top right) - make sure it covers when data exists
2. Verify datasource is selected correctly
3. Test the query in **Explore** mode
4. Check Prometheus has data: http://localhost:9090

### Slow Dashboard Loading

1. Reduce time range
2. Add caching to slow panels
3. Optimize queries (use aggregation)
4. Increase Grafana resources in `grafana-values.yaml`

## Best Practices

### Dashboard Design

✅ **Do:**
- Group related metrics in rows
- Use consistent colors and naming
- Add descriptions to panels
- Use variables for dynamic filtering
- Keep dashboards focused (one per topic)

❌ **Don't:**
- Overcrowd with too many panels
- Use too many colors without meaning
- Create huge time ranges for high-cardinality metrics
- Forget to add units to your metrics

### Query Optimization

✅ **Do:**
- Use aggregation for large datasets
- Apply filters early in queries
- Use recording rules for complex queries
- Cache slow queries

❌ **Don't:**
- Query all pods individually (group by namespace)
- Use `SELECT *` without limits
- Create queries with millions of data points

## Next Steps

1. **Import recommended dashboards** (IDs: 1860, 7249, 9628, 11835)
2. **Create your first custom dashboard** for your application
3. **Set up alerts** for critical metrics
4. **Configure notification channels** (Slack, email)
5. **Learn advanced features** (templating, annotations, playlists)

## Related Documentation

- [Prometheus Quick Start](prometheus-quickstart.md) - Understanding metrics collection
- [Grafana PostgreSQL Setup](grafana-postgresql-setup.md) - Using PostgreSQL datasource
- [Complete Monitoring Guide](monitoring.md) - Detailed monitoring documentation
- [Grafana Official Documentation](https://grafana.com/docs/grafana/latest/)

## Useful Resources

- [Grafana Dashboard Gallery](https://grafana.com/grafana/dashboards/) - Browse community dashboards
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/) - Quick reference
- [Grafana Tutorials](https://grafana.com/tutorials/) - Official learning resources
