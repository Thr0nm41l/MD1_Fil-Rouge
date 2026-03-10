# Airflow

## Overview

Apache Airflow is the workflow orchestration platform of the MD1 infrastructure. It schedules and monitors DAGs (Directed Acyclic Graphs), which are Python scripts that define data pipelines.

### Architecture

Airflow runs in the `airflow` namespace and uses **CeleryExecutor**, distributing task execution across a pool of worker pods. It relies on two external services deployed in the `datalake` namespace:

- **PostgreSQL** — metadata database (DAG runs, task states, logs)
- **Redis** — message broker between the scheduler and workers

```
┌──────────────────────────────────────────────────────────┐
│                   Namespace: airflow                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  Webserver  │    │  Scheduler  │    │  Triggerer  │   │
│  │  (UI + API) │    │ (DAG parse, │    │  (deferred  │   │
│  │  port 8080  │    │  scheduling)│    │   tasks)    │   │
│  └─────────────┘    └─────────────┘    └─────────────┘   │ 
│                                                          │
│  ┌─────────────┐  ┌─────────────┐                        │
│  │  Worker 1   │  │  Worker 2   │  (CeleryExecutor)      │
│  └─────────────┘  └─────────────┘                        │
│                                                          │
└───────────────────┬──────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │   Namespace: datalake │
        │  • PostgreSQL (meta)  │
        │  • Redis (broker)     │
        └───────────────────────┘
```

### Components

| Component   | Replicas | Role                                 |
|-------------|----------|--------------------------------------|
| Webserver   | 1        | Web UI and REST API                  |
| Scheduler   | 1        | Parses DAGs, triggers task instances |
| Workers     | 2        | Execute tasks (CeleryExecutor)       |
| Triggerer   | 1        | Handles deferred tasks (sensors)     |

## Accessing the UI

Forward the port:
```bash
kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow
```

Then access: http://localhost:8080

**Default credentials:**
- Username: `admin`
- Password: `admin`

## DAGs

### How DAGs Are Loaded

DAGs are loaded via **git-sync**: Airflow continuously polls the project repository and syncs the `dags/` directory into each pod. No manual file copying is needed.

**Configuration (from `airflow-values.yaml`):**
- Repository: `https://github.com/Thr0nm41l/MD1_Fil-Rouge.git`
- Branch: `main`
- Subfolder: `dags/`
- Sync interval: every 30 seconds

### Adding or Modifying DAGs

1. Create or edit a Python file in the `dags/` directory at the root of the repository
2. Commit and push to `main`
3. Airflow will pick up the change within ~30 seconds

### Listing Loaded DAGs

```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow dags list
```

Or check the file system directly:
```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- ls /opt/airflow/dags
```

### Triggering a DAG Manually

Via the UI: click the play button next to the DAG on the home screen.

Via CLI:
```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow dags trigger <dag_id>
```

### DAG Conventions

DAGs in this project follow these conventions:

- **File naming**: `<category>__<name>.py` (e.g. `test__print_hello.py`)
- **Tags**: use tags to categorize DAGs (e.g. `test`, `etl`, `reporting`)
- **Default args**: define `start_date`, `retries`, `retry_delay`, `owner`
- **Structure**: `start` (EmptyOperator) → tasks → `end` (EmptyOperator with `ALL_DONE` trigger rule)
- **Documentation**: use the module docstring as `doc_md` for the DAG

Example skeleton:
```python
"""
### DAG: category__name.py

## Tasks:
- task_name: Description of what the task does

## Schedule:
None / cron expression
"""
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

default_args = {
    "start_date": datetime(2025, 1, 1, tzinfo=ZoneInfo("Europe/Paris")),
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "owner": "airflow",
}

with DAG(
    dag_id="category__name",
    default_args=default_args,
    schedule=None,
    catchup=False,
    doc_md=__doc__,
    tags=["category"],
) as dag:

    start = EmptyOperator(task_id="start")
    # ... your tasks ...
    end = EmptyOperator(task_id="end", trigger_rule=TriggerRule.ALL_DONE)

    start >> end
```

## Secrets and Credentials

All credentials are sourced from `.env` and stored in Kubernetes secrets — nothing is hardcoded in the values file.

| Secret name                          | Namespace | Contents                                               |
|--------------------------------------|-----------|--------------------------------------------------------|
| `airflow-metadata-credentials`       | airflow   | PostgreSQL connection string for Airflow metadata DB   |
| `airflow-result-backend-credentials` | airflow   | PostgreSQL connection string for Celery result backend |

These are created automatically by `start_infra.sh`. To create them manually:

```bash
source .env

kubectl create secret generic airflow-metadata-credentials \
  --from-literal=connection="postgresql+psycopg2://${AIRFLOW_DB_USER}:${AIRFLOW_DB_PASSWORD}@postgres-postgresql.datalake.svc.cluster.local:5432/airflow" \
  -n airflow

kubectl create secret generic airflow-result-backend-credentials \
  --from-literal=connection="db+postgresql://${AIRFLOW_DB_USER}:${AIRFLOW_DB_PASSWORD}@postgres-postgresql.datalake.svc.cluster.local:5432/airflow" \
  -n airflow
```

### Passing Secrets to DAGs

To inject secrets as environment variables into DAG tasks, create a Kubernetes secret and reference it in `airflow-values.yaml`:

```bash
kubectl create secret generic airflow-variables \
  --from-literal=MY_API_KEY="your-key" \
  -n airflow
```

Then uncomment and update the `extraEnvFrom` block in `airflow-values.yaml`:
```yaml
extraEnvFrom:
  - secretRef:
      name: airflow-variables
```

## Configuration Reference

Key settings in `airflow-values.yaml`:

| Setting                            | Value             | Description                              |
|------------------------------------|-------------------|------------------------------------------|
| `executor`                         | `CeleryExecutor`  | Distributes tasks across worker pods     |
| `workers.replicas`                 | `2`               | Number of Celery worker pods             |
| `config.celery.worker_concurrency` | `4`               | Tasks per worker pod (total capacity: 8) |
| `workers.resources.limits`         | `1 CPU / 2Gi RAM` | Per-worker resource ceiling              |
| `dags.gitSync.wait`                | `30`              | Seconds between git-sync polls           |
| `postgresql.enabled`               | `false`           | Uses the shared PostgreSQL in `datalake` |
| `redis.enabled`                    | `false`           | Uses the shared Redis in `datalake`      |

## Common Operations

### View Logs

Task logs are available in the UI under **DAGs → <dag_id> → <run> → <task> → Logs**.

Via CLI:
```bash
# Scheduler logs
kubectl logs -f deploy/airflow-scheduler -n airflow

# Worker logs
kubectl logs -f -l component=worker -n airflow

# Webserver logs
kubectl logs -f deploy/airflow-webserver -n airflow
```

### Scale Workers

```bash
kubectl scale deployment airflow-worker -n airflow --replicas=3
```

Or update `workers.replicas` in `airflow-values.yaml` and run:
```bash
helm upgrade airflow apache-airflow/airflow --values airflow-values.yaml -n airflow
```

### Restart a Component

```bash
kubectl rollout restart deployment/airflow-webserver -n airflow
kubectl rollout restart deployment/airflow-scheduler -n airflow
kubectl rollout restart deployment/airflow-worker -n airflow
```

### Run an Airflow CLI Command

```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow <command>

# Examples:
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow dags list
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow tasks list <dag_id>
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow dags trigger <dag_id>
```

## Troubleshooting

### DAG Not Appearing in the UI

1. Check git-sync is running and has pulled the latest commit:
```bash
kubectl logs -l component=scheduler -n airflow | grep "git-sync"
```

2. Check for Python syntax errors in your DAG file:
```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- python /opt/airflow/dags/<your_dag>.py
```

3. Check the scheduler parsed the DAG without errors:
```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- airflow dags list-import-errors
```

### Tasks Stuck in "Queued" State

Workers may not be picking up tasks. Check:
```bash
# Are workers running?
kubectl get pods -n airflow -l component=worker

# Can workers reach Redis?
kubectl logs -l component=worker -n airflow | tail -20

# Is Redis up?
kubectl get pods -n datalake -l app.kubernetes.io/name=redis
```

### Tasks Failing

View task logs in the Airflow UI, or via CLI:
```bash
kubectl exec -it deploy/airflow-scheduler -n airflow -- \
  airflow tasks logs <dag_id> <task_id> <execution_date>
```

### Webserver Not Starting

Check for database connectivity issues:
```bash
kubectl logs deploy/airflow-webserver -n airflow | tail -30
kubectl get secret airflow-metadata-credentials -n airflow
```

### Workers Running Out of Memory

Adjust resource limits in `airflow-values.yaml`:
```yaml
workers:
  resources:
    requests:
      memory: "512Mi"
    limits:
      memory: "4Gi"
```

## Additional Resources

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [CeleryExecutor Guide](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/executor/celery.html)
- [DAG Writing Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Airflow Helm Chart](https://airflow.apache.org/docs/helm-chart/stable/index.html)
