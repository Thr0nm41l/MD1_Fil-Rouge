### Lancement de l'infra

Documentation 'How To' pour lancer l'infra.
Suivre les instructions block par block.

## Pré-requis
Docker
Kubectl
Minikube
Helm

Il faut aussi activer l'addon metric-server pour faire de l'autoscaling des workers Airflow
```bash
minikube addons enable metrics-server
```

## Crééer les namespaces
```bash
kubectl create namespace airflow;
kubectl create namespace datalake;
kubectl create namespace monitoring
```

## Créer les secrets kube (pas encore mis en place)
```bash
kubectl create secret generic airflow-variables \
  --from-literal=AIRFLOW_VAR_ENV=local \
  --from-literal=AIRFLOW_VAR_DATA_BUCKET=my-bucket \
  --from-literal=AIRFLOW_VAR_MAX_RETRIES=3


kubectl create secret generic username-airflow --from-literal=username=airflow --from-literal=password=airflow -n airflow
```
```bash
kubectl create secret generic airflow-connections \
  --from-literal=AIRFLOW_CONN_MY_POSTGRES=postgresql://user:pass@host:5432/db
```

## Lancer les instances Postegres
```bash
helm install postgres bitnami/postgresql --values postgres-values.yaml
```

Pour vérifier si tout est bien monté (tous les pods devraient être en 'running'):
```bash
kubectl get pods
```

## Lancer les instances Redis
```bash
helm install redis bitnami/redis --values redis-values.yaml
```

## Lancer les instances Airflow
```bash
helm install airflow apache-airflow/airflow --values airflow-values.yaml
```

Pour vérifier si tout est bien monté (tous les pods devraient être en 'running'):
```bash
kubectl get pods
```

## Activer l'Autoscaling des workers
```bash
kubectl autoscale deployment airflow-worker \
  --cpu-percent=60 \
  --min=2 \
  --max=6
```

Vérifier que tout fonctionne bien :
```bash
kubectl get hpa;
kubectl describe hpa airflow-worker
```

## Accéder à l'UI Airflow
```bash
kubectl port-forward svc/airflow-api-server 8080:8080 --namespace default
```

Les dags sont récupérés depuis le répo du projet, dans le dossiers dags.
On peut les lister depuis un shell avec la commande :
```bash
kubectl exec -it deploy/airflow-scheduler -- ls /opt/airflow/dags
```

## Eteindre l'infra
```bash
helm uninstall airflow;
helm uninstall redis;
helm uninstall postgres
```


## Pour aller plus loin

Si on veut utiliser un répo privé séparé du repo projet (si ça devient un peu fourre-tout), on peut utiliser cette commande pour crééer un secret kube qui stockera les infos du repo :
```bash
kubectl create secret generic git-credentials \
  --from-literal=username=git \
  --from-literal=password=TOKEN_GITHUB
```

Et ajouter ça à la fin du fichier airflow-values.yaml (une fois le secret kube créé)
```yaml
dags:
  gitSync:
    enabled: true
    repo: https://github.com/TON_ORG/TON_REPO_DAGS.git
    branch: main
    subPath: dags
    credentialsSecret: git-credentials
```