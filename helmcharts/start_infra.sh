#!/bin/bash

minikube start

helm install postgres bitnami/postgresql --values postgres-values.yaml
if [ $? -ne 0 ]; then
  echo "Failed to install PostgreSQL"
  exit 1
fi

helm install redis bitnami/redis --values redis-values.yaml
if [ $? -ne 0 ]; then
  echo "Failed to install Redis"
  exit 1
fi

#helm install airflow apache-airflow/airflow --values airflow-values.yaml
helm install airflow apache-airflow/airflow -f airflow-values.yaml --timeout 15m
if [ $? -ne 0 ]; then
  echo "Failed to install Airflow"
  exit 1
fi

