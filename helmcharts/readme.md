### Lancement de l'infra

Documentation 'How To' pour lancer l'infra.
Suivre les instructions block par block.

## Pré-requis
Docker 
Kubectl v1.15 ou plus
Minikube v1.48 ou plus
Helm v4.1.0 ou plus

Il faut aussi activer l'addon metric-server pour faire de l'autoscaling des workers Airflow
```bash
minikube addons enable metrics-server
```

## Créer les namespaces
```bash
kubectl create namespace airflow;
kubectl create namespace datalake;
kubectl create namespace monitoring
```

## Lancer les instances Postegres
```bash
helm install postgres bitnami/postgresql --values postgres-values.yaml --namespace datalake
```

Pour vérifier si tout est bien monté (tous les pods devraient être en 'running'):
```bash
kubectl get pods --namespace datalake
```

## lancer l'instance pgAdmin
Pour acceder à l'interface de PostgresQL, il faut déployer pgAdmin avec la commande:
```bash
helm install pgadmin runix/pgadmin4 --values pgadmin4-values.yaml -n datalake
```

## Lancer les instances Redis
```bash
helm install redis bitnami/redis --values redis-values.yaml --namespace datalake
```

## Lancer les instances Airflow
```bash
helm install airflow apache-airflow/airflow --values airflow-values.yaml --namespace airflow
```

Pour vérifier si tout est bien monté (tous les pods devraient être en 'running'):
```bash
kubectl get pods --all-namespaces
```

## Accéder à l'UI Airflow
Comme nous utilisons minikube il faut d'abord forward le port avec la commande :
```bash
kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow
```
On peut ensuite accéder à l'interface web via l'url : http://localhost:8080

## Accéder à l'UI pgAdmin
Comme nous utilisons minikube il faut d'abord forward le port avec la commande :
```bash
kubectl port-forward svc/pgadmin-pgadmin4 5050:80 --namespace datalake
```

On peut ensuite accéder à l'interface web via l'url : http://localhost:5050


## Les DAGs Airflow
Les dags sont récupérés depuis le répo du projet, dans le dossiers dags.
On peut les lister depuis un shell avec la commande :
```bash
kubectl exec -it deploy/airflow-scheduler -- ls /opt/airflow/dags
```

## Eteindre l'infra
```bash
helm uninstall airflow --namespace airflow;
helm uninstall redis --namespace datalake;
helm uninstall pgadmin --namespace datalake;
helm uninstall postgres --namespace datalake
```

## Notes pour améliorations futures
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

### Récupérer le mot de passe admin de PostgresQL

Login : postgres
On peut récupérer le mot de passe en exécutant la commande suivante :
```bash
kubectl get secret postgres-postgresql -n datalake -o jsonpath='{.data.postgres-password}' | base64 -d && echo
```

Le mot de passe est défini dans la chart, mais au cas où il soit désynchronisé, utiliser la commande suivante :
```bash
kubectl exec -it postgres-postgresql-0 -n datalake -- psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'P0stgr3s@dmin';" 2>&1 || echo "Password change failed, trying with current password..."
```