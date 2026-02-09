#!/bin/bash

# Kill any running port-forward processes
echo "Stopping port-forwards..." >&2
#pkill -f "kubectl port-forward.*airflow"
#pkill -f "kubectl port-forward.*pgadmin"
echo "Port-forwards stopped." >&2

helm uninstall airflow -n airflow
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Airflow"
fi

helm uninstall redis -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Redis"
fi

helm uninstall pgadmin -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to uninstall PgAdmin"
fi

helm uninstall postgres -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to uninstall PostgreSQL"
fi

#minikube stop

echo "All Helm releases have been uninstalled." >&2
exit 0