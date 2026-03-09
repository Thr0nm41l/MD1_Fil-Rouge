#!/bin/bash

# Alternative infrastructure setup using Grafana Operator
# This script uses the modern, non-deprecated Grafana Operator instead of the deprecated Helm chart

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

# Create namespaces
init_namespace datalake
init_namespace airflow
init_namespace monitoring

echo "Namespaces are set up." >&2
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

# Install Redis
helm install redis bitnami/redis --values redis-values.yaml -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to install Redis" >&2
  exit 1
else
  echo "Redis installed successfully." >&2
fi

echo "Waiting for Redis pod to be ready..." >&2
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n datalake --timeout=120s
echo "Redis pod is ready." >&2

# Install Airflow
helm install airflow apache-airflow/airflow --values airflow-values.yaml --timeout 15m -n airflow
if [ $? -ne 0 ]; then
  echo "Failed to install Airflow" >&2
  exit 1
else
  echo "Airflow installed successfully." >&2
fi

echo "Waiting for Airflow pods to be ready..." >&2
kubectl wait --for=condition=ready pod -l component=webserver -n airflow --timeout=300s
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

# Install Grafana Operator
echo "Installing Grafana Operator..." >&2
helm install grafana-operator grafana/grafana-operator \
  --values grafana-operator-values.yaml \
  -n monitoring
if [ $? -ne 0 ]; then
  echo "Failed to install Grafana Operator" >&2
  exit 1
else
  echo "Grafana Operator installed successfully." >&2
fi

echo "Waiting for Grafana Operator to be ready..." >&2
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana-operator -n monitoring --timeout=300s
echo "Grafana Operator is ready." >&2

# Create Grafana instance
echo "Creating Grafana instance..." >&2
kubectl apply -f grafana-instance.yaml
if [ $? -ne 0 ]; then
  echo "Failed to create Grafana instance" >&2
  exit 1
else
  echo "Grafana instance created successfully." >&2
fi

# Wait a bit for Grafana to be created
sleep 10

echo "Waiting for Grafana pod to be ready..." >&2
kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=300s 2>/dev/null || echo "Grafana pod may still be starting..."
echo "Grafana pod is ready." >&2

# Create Grafana datasources
echo "Creating Grafana datasources..." >&2
kubectl apply -f grafana-datasources.yaml
if [ $? -ne 0 ]; then
  echo "Failed to create Grafana datasources" >&2
else
  echo "Grafana datasources created successfully." >&2
fi

# Port-forward commands (uncomment to auto-start)
# kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow &
# kubectl port-forward svc/pgadmin-pgadmin4 5050:80 --namespace datalake &
# kubectl port-forward svc/grafana-service 3000:3000 --namespace monitoring &
# kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring &

echo "All components have been installed." >&2
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
echo "Grafana (Monitoring Dashboards - via Operator):" >&2
echo "  kubectl port-forward svc/grafana-service 3000:3000 --namespace monitoring" >&2
echo "  http://localhost:3000 (admin / Gr@f@n@Admin123)" >&2
echo "" >&2
echo "Prometheus (Metrics):" >&2
echo "  kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 --namespace monitoring" >&2
echo "  http://localhost:9090" >&2
echo "" >&2
exit 0
