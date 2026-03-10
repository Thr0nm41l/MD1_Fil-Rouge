# Infrastructure Setup

Documentation on how to launch the MD1 infrastructure.
Follow the instructions block by block.

## Prerequisites

- Docker Engine v29.1.3 or higher
- Kubectl v1.15 or higher
- Minikube v1.48 or higher
- Helm v4.1.0 or higher

You also need to enable the metrics-server addon for Airflow worker autoscaling:
```bash
minikube addons enable metrics-server
```

## Quick Start (Automated)

The easiest way to launch the entire infrastructure:

First, copy the example env file and fill in your credentials:
```bash
cp .env.example .env
# Edit .env with your passwords and settings
```

Then run:
```bash
./start_infra.sh
```

This script will automatically:
- Load credentials from `.env` and create Kubernetes secrets
- Create necessary namespaces (airflow, datalake, monitoring)
- Add required Helm repositories
- Install PostgreSQL
- Install pgAdmin
- Install Redis
- Install Airflow
- Install Prometheus (monitoring & alerting)
- Install Grafana (visualization dashboards)
- Apply ServiceMonitors for monitoring

To stop the infrastructure:
```bash
./stop_infra.sh
```

## Manual Setup (Step by Step)

If you prefer to install components manually, follow these steps:

### 0. Set Up Credentials

Copy the example env file and fill in your credentials:
```bash
cp .env.example .env
# Edit .env with your passwords and settings
source .env
```

Create the Kubernetes secrets that the Helm charts depend on:
```bash
kubectl create secret generic postgres-credentials \
  --from-literal=postgres-password="${POSTGRES_ADMIN_PASSWORD}" \
  --from-literal=airflow-db-user="${AIRFLOW_DB_USER}" \
  --from-literal=airflow-password="${AIRFLOW_DB_PASSWORD}" \
  -n datalake

kubectl create secret generic pgadmin-credentials \
  --from-literal=password="${PGADMIN_PASSWORD}" \
  -n datalake

kubectl create secret generic grafana-admin-credentials \
  --from-literal=admin-user="${GRAFANA_ADMIN_USER}" \
  --from-literal=admin-password="${GRAFANA_ADMIN_PASSWORD}" \
  -n monitoring

kubectl create secret generic grafana-datasource-credentials \
  --from-literal=POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD}" \
  -n monitoring

kubectl create secret generic airflow-metadata-credentials \
  --from-literal=connection="postgresql+psycopg2://${AIRFLOW_DB_USER}:${AIRFLOW_DB_PASSWORD}@postgres-postgresql.datalake.svc.cluster.local:5432/airflow" \
  -n airflow

kubectl create secret generic airflow-result-backend-credentials \
  --from-literal=connection="db+postgresql://${AIRFLOW_DB_USER}:${AIRFLOW_DB_PASSWORD}@postgres-postgresql.datalake.svc.cluster.local:5432/airflow" \
  -n airflow
```

### 1. Create Namespaces

```bash
kubectl create namespace airflow
kubectl create namespace datalake
kubectl create namespace monitoring
```

### 2. Add Helm Repositories

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add apache-airflow https://airflow.apache.org
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add runix https://helm.runix.net
helm repo update
```

### 3. Install PostgreSQL

```bash
helm install postgres bitnami/postgresql --values postgres-values.yaml --namespace datalake
```

To verify everything is running properly (all pods should be in 'running' state):
```bash
kubectl get pods --namespace datalake
```

### 4. Install pgAdmin

To access the PostgreSQL interface, deploy pgAdmin with the command:
```bash
helm install pgadmin runix/pgadmin4 --values pgadmin4-values.yaml -n datalake
```

### 5. Install Redis

```bash
helm install redis bitnami/redis --values redis-values.yaml --namespace datalake
```

### 6. Install Airflow

```bash
helm install airflow apache-airflow/airflow --values airflow-values.yaml --namespace airflow
```

To verify everything is running properly (all pods should be in 'running' state):
```bash
kubectl get pods --all-namespaces
```

### 7. Install Prometheus

```bash
helm install prometheus prometheus-community/kube-prometheus-stack \
  --values prometheus-values.yaml \
  --namespace monitoring
```

Apply ServiceMonitors for application monitoring:
```bash
kubectl apply -f servicemonitors.yaml
```

### 8. Install Grafana

```bash
helm install grafana grafana/grafana \
  --values grafana-values.yaml \
  --namespace monitoring
```

Grafana is installed separately from Prometheus for better separation of concerns and independent lifecycle management.

**Note:** All credentials are sourced from your `.env` file and stored in Kubernetes secrets (created in step 0) — no passwords are hardcoded in config files or Git.

## Accessing the Web Interfaces

### Airflow UI

Since we're using Minikube, we need to forward the port first:
```bash
kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow
```

Then access the web interface at: http://localhost:8080

**Default credentials:**
- Username: `admin`
- Password: `admin`

### pgAdmin UI

Forward the port:
```bash
kubectl port-forward svc/pgadmin-pgadmin4 5050:80 --namespace datalake
```

Then access the web interface at: http://localhost:5050

**Credentials:**
- Email: `admin@localhost.io`
- Password: the `PGADMIN_PASSWORD` you set in `.env`

### Grafana (Monitoring Dashboards)

Forward the port:
```bash
kubectl port-forward svc/grafana 3000:80 --namespace monitoring
```

Then access at: http://localhost:3000

**Credentials:**
- Username: `admin`
- Password: retrieve it with:
```bash
kubectl get secret grafana-admin-credentials -n monitoring \
  -o jsonpath='{.data.admin-password}' | base64 -d && echo
```

Grafana comes pre-configured with:
- **Prometheus** datasource for metrics
- **PostgreSQL** datasource for application data

### Prometheus (Metrics & Queries)

Forward the port:
```bash
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring
```

Then access at: http://localhost:9090

For detailed monitoring documentation, see [docs/monitoring.md](docs/monitoring.md)

## Working with Airflow DAGs

DAGs are retrieved from the project repository, in the `dags` folder.
You can list them from a shell with the command:
```bash
kubectl exec -it deploy/airflow-scheduler -- ls /opt/airflow/dags
```

To add or modify DAGs, simply edit files in the `dags/` directory. Airflow will automatically detect changes.

## Shutting Down the Infrastructure

To uninstall all components:

```bash
./stop_infra.sh
```

Or manually:
```bash
helm uninstall grafana --namespace monitoring
helm uninstall prometheus --namespace monitoring
helm uninstall airflow --namespace airflow
helm uninstall redis --namespace datalake
helm uninstall pgadmin --namespace datalake
helm uninstall postgres --namespace datalake
```

To completely stop Minikube:
```bash
minikube stop
```

## PostgreSQL Access

### Retrieve PostgreSQL Admin Password

**Login:** `postgres`

You can retrieve the password from the Kubernetes secret:
```bash
kubectl get secret postgres-credentials -n datalake -o jsonpath='{.data.postgres-password}' | base64 -d && echo
```

If the password in the running PostgreSQL instance gets out of sync with the secret, reset it to match your `.env`:
```bash
kubectl exec -it postgres-postgresql-0 -n datalake -- psql -U postgres -c "ALTER USER postgres WITH PASSWORD '${POSTGRES_ADMIN_PASSWORD}';"
```

### Connect to PostgreSQL from pgAdmin

Two servers are pre-loaded in pgAdmin. To connect:

1. Access pgAdmin at http://localhost:5050
2. Login with credentials from your `.env`
3. Click on a pre-loaded server (e.g. "PostgreSQL Admin (superuser)")
4. Enter the password when prompted (your `POSTGRES_ADMIN_PASSWORD` from `.env`)

Or register a server manually:
1. Right-click "Servers" → "Register" → "Server"
2. General tab: Name = `MD1 PostgreSQL`
3. Connection tab:
   - Host: `postgres-postgresql.datalake.svc.cluster.local`
   - Port: `5432`
   - Username: `postgres`
   - Password: your `POSTGRES_ADMIN_PASSWORD` from `.env`

## Advanced Configuration

### Using a Separate Private Repository for DAGs

If you want to use a separate private repository for DAGs (instead of storing them in the project repo), you can create a Kubernetes secret to store the repository credentials:

```bash
kubectl create secret generic git-credentials --from-literal=username=git --from-literal=password=GITHUB_TOKEN --namespace airflow
```

Then add this to the end of the `airflow-values.yaml` file (after creating the Kubernetes secret):

```yaml
dags:
  gitSync:
    enabled: true
    repo: https://github.com/YOUR_ORG/YOUR_DAGS_REPO.git
    branch: main # Or any branch
    subPath: dags # Folder containing the dags 
    credentialsSecret: git-credentials # If the repo is private
```

## Troubleshooting

### Pods Not Starting

Check pod status:
```bash
kubectl get pods --all-namespaces
```

View pod logs:
```bash
kubectl logs <pod-name> -n <namespace>
```

Describe pod for events:
```bash
kubectl describe pod <pod-name> -n <namespace>
```

### Port Forward Not Working

Make sure the service exists:
```bash
kubectl get svc -n <namespace>
```

Kill any existing port-forward processes:
```bash
pkill -f "kubectl port-forward"
```

### Persistent Volume Issues

Check PVC status:
```bash
kubectl get pvc --all-namespaces
```

For Minikube, ensure you have enough disk space:
```bash
minikube ssh
df -h
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Minikube Cluster                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────┐  ┌────────────────┐                 │
│  │   Namespace:   │  │   Namespace:   │                 │
│  │    airflow     │  │   datalake     │                 │
│  ├────────────────┤  ├────────────────┤                 │
│  │                │  │                │                 │
│  │  • Webserver   │  │  • PostgreSQL  │                 │
│  │  • Scheduler   │  │  • pgAdmin     │                 │
│  │  • Workers     │  │  • Redis       │                 │
│  │  • Triggerer   │  │                │                 │
│  └────────────────┘  └────────────────┘                 │
│                                                         │
│  ┌────────────────────────────────────┐                 │
│  │        Namespace: monitoring       │                 │
│  ├────────────────────────────────────┤                 │
│  │                                    │                 │
│  │  • Prometheus                      │                 │
│  │  • Grafana                         │                 │
│  │  • AlertManager                    │                 │
│  │  • Node Exporter                   │                 │
│  └────────────────────────────────────┘                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Additional Resources

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [Minikube Documentation](https://minikube.sigs.k8s.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Monitoring Documentation](docs/monitoring.md)
- [Prometheus Quick Start](docs/prometheus-quickstart.md)
