# Using Grafana with PostgreSQL

Grafana can connect to your PostgreSQL database to visualize application data alongside infrastructure metrics.

## Adding PostgreSQL as a Data Source

### Via Grafana UI

1. Access Grafana: http://localhost:3000
2. Login with `admin` / `Gr@f@n@Admin123`
3. Go to **Configuration** → **Data Sources**
4. Click **Add data source**
5. Select **PostgreSQL**
6. Configure:
   - **Name**: `MD1 PostgreSQL`
   - **Host**: `postgres-postgresql.datalake.svc.cluster.local:5432`
   - **Database**: `postgres` (or your database name)
   - **User**: `postgres`
   - **Password**: `postgresadmin`
   - **SSL Mode**: `disable`
   - **Version**: Select your PostgreSQL version
7. Click **Save & Test**

### Via Configuration (Advanced)

You can also pre-configure PostgreSQL datasource in `prometheus-values.yaml`:

```yaml
grafana:
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus-kube-prometheus-prometheus:9090
        access: proxy
        isDefault: true
      - name: PostgreSQL
        type: postgres
        url: postgres-postgresql.datalake.svc.cluster.local:5432
        database: postgres
        user: postgres
        secureJsonData:
          password: postgresadmin
        jsonData:
          sslmode: disable
          postgresVersion: 1300  # 13.0
```

## Example Queries

### Time Series Data

Query records over time:

```sql
SELECT
  $__time(created_at),
  count(*) as "Records Created"
FROM your_table
WHERE $__timeFilter(created_at)
GROUP BY 1
ORDER BY 1
```

### Aggregate Statistics

Display current counts:

```sql
SELECT
  NOW() as time,
  count(*) as total_records,
  count(DISTINCT user_id) as unique_users
FROM your_table
WHERE created_at >= NOW() - INTERVAL '24 hours'
```

### Table Visualization

Show recent records:

```sql
SELECT
  id,
  name,
  created_at,
  status
FROM your_table
ORDER BY created_at DESC
LIMIT 100
```

## Grafana Variables for PostgreSQL

Use Grafana variables to make dashboards interactive:

### Variable: Database Tables

Query:
```sql
SELECT tablename as __text, tablename as __value
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
```

Usage: `$table_name` in your queries

### Variable: Date Range

Built-in Grafana time range picker automatically works with:
- `$__timeFilter(column_name)`
- `$__timeFrom()` and `$__timeTo()`

## Example Dashboard Panels

### Panel 1: Records Per Hour

**Query:**
```sql
SELECT
  date_trunc('hour', created_at) as time,
  count(*) as count
FROM your_table
WHERE $__timeFilter(created_at)
GROUP BY 1
ORDER BY 1
```

**Visualization**: Time series (Line chart)

### Panel 2: Database Size

**Query:**
```sql
SELECT
  NOW() as time,
  pg_database_size(current_database()) / (1024*1024) as "Size (MB)"
```

**Visualization**: Stat panel

### Panel 3: Table Row Counts

**Query:**
```sql
SELECT
  NOW() as time,
  relname as "Table",
  n_live_tup as "Row Count"
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 10
```

**Visualization**: Table

### Panel 4: Active Queries

**Query:**
```sql
SELECT
  NOW() as time,
  pid,
  usename,
  application_name,
  state,
  query,
  query_start
FROM pg_stat_activity
WHERE state != 'idle'
  AND pid != pg_backend_pid()
ORDER BY query_start DESC
```

**Visualization**: Table

## Best Practices

### 1. Use Time Filters

Always use `$__timeFilter()` for time-based queries:
```sql
WHERE $__timeFilter(created_at)
```

This respects the Grafana time range picker.

### 2. Limit Result Sets

Add `LIMIT` clauses to prevent loading too much data:
```sql
LIMIT 1000
```

### 3. Use Indexes

Ensure your PostgreSQL tables have indexes on:
- Time columns used for filtering
- Columns used in `GROUP BY` and `ORDER BY`

```sql
CREATE INDEX idx_table_created_at ON your_table(created_at);
```

### 4. Cache Settings

For static/slow queries, enable query caching in panel settings:
- Go to panel → Edit → Query options
- Set cache timeout (e.g., 300 seconds)

### 5. Use Prepared Statements

Grafana variables automatically use prepared statements for safety.

## Combining Prometheus and PostgreSQL

### Example: Airflow Pipeline Monitoring

**Row 1: Infrastructure (Prometheus)**
- Panel: CPU usage per pod
- Panel: Memory usage
- Panel: Pod restart count

**Row 2: Application Data (PostgreSQL)**
- Panel: Records processed per hour
- Panel: Processing success rate
- Panel: Error count by type

**Row 3: Business Metrics (PostgreSQL)**
- Panel: Daily active users
- Panel: Transaction volume
- Panel: Revenue metrics

## Troubleshooting

### Connection Failed

Check that PostgreSQL is accessible:
```bash
kubectl exec -it postgres-postgresql-0 -n datalake -- psql -U postgres -c "SELECT version();"
```

### Query Timeout

Increase timeout in datasource settings:
- Configuration → Data Sources → PostgreSQL
- HTTP Settings → Timeout: 60 seconds

### Slow Queries

Check PostgreSQL query performance:
```sql
EXPLAIN ANALYZE
SELECT ...
```

Add indexes where needed.

### SSL Certificate Errors

For local development, use:
- SSL Mode: `disable`

For production, use proper SSL certificates.

## Security Considerations

### Read-Only User (Recommended)

Create a dedicated Grafana user with read-only access:

```sql
-- Create read-only user
CREATE USER grafana_reader WITH PASSWORD 'secure_password';

-- Grant connection
GRANT CONNECT ON DATABASE postgres TO grafana_reader;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO grafana_reader;

-- Grant SELECT on all tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_reader;

-- Grant SELECT on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO grafana_reader;
```

Then use this user in Grafana datasource configuration.

### Network Policies

In production, restrict network access:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-grafana-to-postgres
  namespace: datalake
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: postgresql
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
      podSelector:
        matchLabels:
          app.kubernetes.io/name: grafana
    ports:
    - protocol: TCP
      port: 5432
```

## Additional Resources

- [Grafana PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Grafana Query Basics](https://grafana.com/docs/grafana/latest/panels-visualizations/query-transform-data/)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
