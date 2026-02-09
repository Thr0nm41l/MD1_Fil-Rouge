#!/bin/bash

stacknumber=6
stopedstacknumber=0

# Kill any running port-forward processes
echo "Stopping port-forwards..." >&2
#pkill -f "kubectl port-forward.*airflow"
#pkill -f "kubectl port-forward.*pgadmin"
echo "Port-forwards stopped." >&2

helm uninstall airflow -n airflow
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Airflow"
  else
    stopedstacknumber=$((stopedstacknumber + 1))
fi

helm uninstall redis -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Redis"
  else
    stopedstacknumber=$((stopedstacknumber + 1))
fi

helm uninstall pgadmin -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to uninstall PgAdmin"
  else
    stopedstacknumber=$((stopedstacknumber + 1))
fi

helm uninstall postgres -n datalake
if [ $? -ne 0 ]; then
  echo "Failed to uninstall PostgreSQL"
else
  stopedstacknumber=$((stopedstacknumber + 1))
fi

helm uninstall prometheus -n monitoring
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Prometheus"
else
  stopedstacknumber=$((stopedstacknumber + 1))
fi

helm uninstall grafana -n monitoring
if [ $? -ne 0 ]; then
  echo "Failed to uninstall Grafana"
else
  stopedstacknumber=$((stopedstacknumber + 1))
fi

# Remove ServiceMonitors
kubectl delete -f servicemonitors.yaml 2>/dev/null
if [ $? -ne 0 ]; then
  echo "Failed to delete ServiceMonitors"
else
  if [ $stopedstacknumber -eq $stacknumber ]; then
    echo "All Helm releases and ServiceMonitors have been uninstalled successfully." >&2
    minikube stop
  else
    echo "Some Helm releases or ServiceMonitors may not have been uninstalled successfully." >&2
  fi
fi

exit 0