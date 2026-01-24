#!/bin/bash

helm uninstall airflow
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Airflow"
fi

helm uninstall redis
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Redis"
fi

helm uninstall postgres
if [ $? -ne 0 ]; then
  echo "Failed to uninstall PostgreSQL"
fi

minikube stop

echo "All Helm releases have been uninstalled." >&2
exit 0