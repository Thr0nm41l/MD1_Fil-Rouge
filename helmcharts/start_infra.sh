#!/bin/bash

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

echo "Namespaces are set up." >&2
echo "" >&2

# Check kube secrets
# kubectl get secrets username-airflow -n airflow
# if [ $? -ne 0 ]; then
#   echo "Secret 'username-airflow' does not exist in 'airflow' namespace. You need to create it." >&2
# else
#   echo "Secret 'username-airflow' already exists in 'airflow' namespace."
# fi



# ============================================================
# Helm Repo And Charts Installation
# ============================================================

# Add Helm repos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add apache-airflow https://airflow.apache.org
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

# Port-forward Airflow and PgAdmin
# kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow &
# kubectl port-forward svc/pgadmin-pgadmin4 5050:80 --namespace datalake &

echo "All Helm charts have been installed." >&2
exit 0