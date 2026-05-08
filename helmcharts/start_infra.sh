#!/bin/bash

# ============================================================
# Load Credentials from .env
# ============================================================

if [ ! -f .env ]; then
  echo "Error: .env file not found. Copy .env.example to .env and fill in your credentials." >&2
  exit 1
fi
source .env

required_vars=(
  POSTGRES_ADMIN_PASSWORD AIRFLOW_DB_USER AIRFLOW_DB_PASSWORD
  AIRFLOW_FERNET_KEY
  AIRFLOW_API_KEY
  PGADMIN_EMAIL PGADMIN_PASSWORD
  GRAFANA_ADMIN_USER GRAFANA_ADMIN_PASSWORD
)
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "Error: required variable '$var' is not set in .env" >&2
    exit 1
  fi
done

echo "Credentials loaded from .env." >&2

# ============================================================
# Utilitary Functions
# ============================================================

function init_namespace {
  namespace=$1
  kubectl get namespace $namespace
  if [ $? -ne 0 ]; then
    echo "Namespace '$namespace' does not exist. Creating it..." >&2
    kubectl create namespace $namespace
    if [ $? -ne 0 ]; then
      echo "Failed to create namespace '$namespace'" >&2
      exit 1
    else
      echo "Namespace '$namespace' created successfully." >&2
    fi
  else
    echo "Namespace '$namespace' already exists." >&2
  fi
}

# ============================================================
# Kubernetes Cluster Setup
# ============================================================

#minikube start

# Create a namespace for the datalake
init_namespace datalake

# Create namespace for airflow
init_namespace airflow

# Create namespace for monitoring
init_namespace monitoring

# Create namespace for documentation
init_namespace documentation

# API service runs in the datalake namespace — no separate namespace needed

echo "Namespaces are set up." >&2
echo "" >&2

# ============================================================
# Kubernetes Secrets
# ============================================================

# Using --dry-run=client | kubectl apply to make creation idempotent

# Used by the postgres superuser
kubectl create secret generic postgres-credentials \
  --from-literal=postgres-password="${POSTGRES_ADMIN_PASSWORD}" \
  --from-literal=airflow-db-user="${AIRFLOW_DB_USER}" \
  --from-literal=airflow-password="${AIRFLOW_DB_PASSWORD}" \
  -n datalake --dry-run=client -o yaml | kubectl apply -f -

# Used by pgAdmin to authenticate to pgAdmin UI
kubectl create secret generic pgadmin-credentials \
  --from-literal=password="${PGADMIN_PASSWORD}" \
  -n datalake --dry-run=client -o yaml | kubectl apply -f -

# Used by Grafana to authenticate to the Grafana UI
kubectl create secret generic grafana-admin-credentials \
  --from-literal=admin-user="${GRAFANA_ADMIN_USER}" \
  --from-literal=admin-password="${GRAFANA_ADMIN_PASSWORD}" \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

# Used by Grafana to connect to the PostgreSQL datasource
kubectl create secret generic grafana-datasource-credentials \
  --from-literal=POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD}" \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

# Used by the bundled Bitnami PostgreSQL subchart to initialize the airflow user password
# postgres-password: read by the PostgreSQL container
# password: read by the Airflow migration job
kubectl create secret generic airflow-postgres-credentials \
  --from-literal=postgres-password="${AIRFLOW_DB_PASSWORD}" \
  --from-literal=password="${AIRFLOW_DB_PASSWORD}" \
  -n airflow --dry-run=client -o yaml | kubectl apply -f -

# Used by Airflow to connect to its dedicated bundled PostgreSQL (airflow-postgresql.airflow)
kubectl create secret generic airflow-metadata-credentials \
  --from-literal=connection="postgresql+psycopg2://${AIRFLOW_DB_USER}:${AIRFLOW_DB_PASSWORD}@airflow-postgresql.airflow.svc.cluster.local:5432/airflow" \
  -n airflow --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic airflow-result-backend-credentials \
  --from-literal=connection="db+postgresql://${AIRFLOW_DB_USER}:${AIRFLOW_DB_PASSWORD}@airflow-postgresql.airflow.svc.cluster.local:5432/airflow" \
  -n airflow --dry-run=client -o yaml | kubectl apply -f -

# Used by Airflow to encrypt/decrypt connection credentials in the metadata DB — must stay stable across restarts
kubectl create secret generic airflow-fernet-key \
  --from-literal=fernet-key="${AIRFLOW_FERNET_KEY}" \
  -n airflow --dry-run=client -o yaml | kubectl apply -f -


echo "Kubernetes secrets created." >&2
echo "" >&2

# ============================================================
# Helm Repo And Charts Installation
# ============================================================

# Add Helm repos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add apache-airflow https://airflow.apache.org
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add runix https://helm.runix.net
helm repo update

# Install PostgreSQL
helm install postgres bitnami/postgresql --values postgres-values.yaml -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to install PostgreSQL" >&2
  exit 1
else 
  echo "PostgreSQL installed successfully." >&2
fi

echo "Waiting for PostgreSQL pod to be ready..." >&2
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n datalake --timeout=120s
echo "PostgreSQL pod is ready." >&2

# Install PgAdmin
helm install pgadmin runix/pgadmin4 --values pgadmin4-values.yaml -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to install PgAdmin" >&2
  exit 1
else 
  echo "PgAdmin installed successfully." >&2
fi

# Install Airflow (Redis and PostgreSQL are bundled as subcharts)
helm install airflow apache-airflow/airflow --values airflow-values.yaml --set apiSecretKey="${AIRFLOW_API_KEY}" --timeout 15m -n airflow
if [ $? -ne 0 ]; then
  echo "Failed to install Airflow" >&2
  exit 1
else 
  echo "Airflow installed successfully." >&2
fi

echo "Waiting for Airflow pods to be ready..." >&2
kubectl wait --for=condition=ready pod -l component=api-server -n airflow --timeout=300s
echo "Airflow pods are ready." >&2

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack --values prometheus-values.yaml -n monitoring
if [ $? -ne 0 ]; then
  echo "Failed to install Prometheus" >&2
  exit 1
else
  echo "Prometheus installed successfully." >&2
fi

echo "Waiting for Prometheus pods to be ready..." >&2
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s
echo "Prometheus pods are ready." >&2

# Apply ServiceMonitors for custom applications
echo "Applying ServiceMonitors..." >&2
kubectl apply -f servicemonitors.yaml
echo "ServiceMonitors applied." >&2

# Install Grafana
helm install grafana grafana/grafana --values grafana-values.yaml -n monitoring
if [ $? -ne 0 ]; then
  echo "Failed to install Grafana" >&2
  exit 1
else
  echo "Grafana installed successfully." >&2
fi

echo "Waiting for Grafana pod to be ready..." >&2
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s
echo "Grafana pod is ready." >&2

# Deploy Api Service (runs in datalake namespace alongside PostgreSQL)
kubectl apply -f apiservice-deployment.yaml
if [ $? -ne 0 ]; then
  echo "Failed to deploy API Service" >&2
  exit 1
else
  echo "API Service deployed successfully." >&2
fi

echo "Waiting for API Service pod to be ready..." >&2
kubectl wait --for=condition=ready pod -l app=apiservice -n datalake --timeout=120s
echo "API Service pod is ready." >&2

# Deploy MkDocs documentation site
kubectl apply -f mkdocs-deployment.yaml -n documentation
if [ $? -ne 0 ]; then
  echo "Failed to deploy MkDocs" >&2
  exit 1
else
  echo "MkDocs deployed successfully." >&2
fi

echo "Waiting for MkDocs pod to be ready..." >&2
kubectl wait --for=condition=ready pod -l app=mkdocs -n documentation --timeout=120s
echo "MkDocs pod is ready." >&2

# Port-forward commands (uncomment to auto-start)
# kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow &
# kubectl port-forward svc/pgadmin-pgadmin4 5050:80 --namespace datalake &
# kubectl port-forward svc/grafana 3000:80 --namespace monitoring &
# kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring &

echo "All Helm charts have been installed." >&2
echo "" >&2
echo "=== Access Your Services ===" >&2
echo "" >&2
echo "Airflow UI:" >&2
echo "  kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow" >&2
echo "  http://localhost:8080 (admin / admin)" >&2
echo "" >&2
echo "pgAdmin:" >&2
echo "  kubectl port-forward svc/pgadmin-pgadmin4 5050:80 --namespace datalake" >&2
echo "  http://localhost:5050 (admin@admin.com / admin)" >&2
echo "" >&2
echo "Grafana (Dashboards):" >&2
echo "  kubectl port-forward svc/grafana 3000:80 --namespace monitoring" >&2
echo "  http://localhost:3000 (admin / <your-password>)" >&2
echo "" >&2
echo "Prometheus (Metrics):" >&2
echo "  kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring" >&2
echo "  http://localhost:9090" >&2
echo "" >&2
echo "API Service:" >&2
echo "  kubectl port-forward svc/apiservice 8000:8000 --namespace datalake" >&2
echo "  http://localhost:8000" >&2
echo "" >&2
echo "MkDocs (Documentation):" >&2
echo "  kubectl port-forward svc/mkdocs 8081:8000 --namespace documentation" >&2
echo "  http://localhost:8081" >&2
echo "" >&2
exit 0