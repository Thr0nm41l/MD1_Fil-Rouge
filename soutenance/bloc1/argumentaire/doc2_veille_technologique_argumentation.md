# Document 2 — Veille Technologique : Argumentation des Choix Technologiques

> Ce document confronte les comparatifs technologiques préconisés par le template M1 DATA avec les choix effectivement retenus dans ECOTRACK, en justifiant chaque décision par des données mesurées ou des contraintes projet.

---

## II-A. Traitement Batch : Spark vs Dask vs Ray — Choix retenu : aucun des trois

### Proposition du template

Comparer Apache Spark, Dask et Ray sur 5 critères (performance, API Python, écosystème, déploiement, coût), avec un volume cible de 180M mesures/an.

### Solution implémentée

Le traitement batch repose sur des **procédures stockées PostgreSQL** orchestrées par Airflow, sans framework distribué dédié.

**Argument — Volume réel vs volume théorique :**

| Paramètre | Template (ville entière) | Implémentation ECOTRACK |
|---|---|---|
| Volume annuel | 180M mesures | ~1,44M lignes / 30 jours (~18M/an à 2 000 conteneurs) |
| Source | 2 000 capteurs réels | Simulation par `lasc__livesim_fill` (*/10 * * * *) |
| Traitement batch | Apache Spark cluster | `CALL aggregate_hourly(ts)` + `CALL aggregate_daily(day)` |

Spark requiert un cluster dédié (minimum 3 workers, 4 Go RAM chacun) pour un gain de performance visible au-delà de ~50M lignes. Sur 18M lignes/an sur PostgreSQL partitionné, les procédures idempotentes `aggregate_hourly` et `aggregate_daily` (upsert `INSERT … ON CONFLICT DO UPDATE`) s'exécutent en quelques secondes par tranche horaire. L'objectif de requêtes < 100ms (tâche H1 du CDC) est atteint par l'indexation composite `(container_id, measured_at DESC)` et le partition pruning.

**Argument — Opérationnalisation :**
Spark aurait nécessité un Helm chart supplémentaire dans le cluster Minikube, un PVC de staging pour les fichiers Parquet, et une couche de lecture S3/MinIO. Le namespace `datalake` (PostgreSQL + API + pgAdmin) couvre 100 % des besoins sans surcoût opérationnel.

---

## II-B. Streaming : Kafka vs Pulsar vs RabbitMQ — Choix retenu : Airflow + psycopg2

### Proposition du template

Comparer Kafka, Pulsar et RabbitMQ sur débit, latence, durabilité, complexité, communauté pour un cas ECOTRACK à 180M mesures/an, latence < 2s.

### Solution implémentée

L'ingestion temps réel est assurée par le DAG `lasc__livesim_fill` (schedule `*/10 * * * *`) qui insère directement dans `fill_history` via `psycopg2.extras.execute_values`.

**Argument — Source unique simulée vs multi-producteurs :**

Kafka est conçu pour des architectures multi-producteurs (des milliers de capteurs physiques envoyant des messages MQTT de manière concurrente). Dans ECOTRACK, la source de données est un unique processus Python. Un broker de messages aurait ajouté :
- ZooKeeper ou KRaft pour le consensus de cluster
- Topics + consumer groups à provisionner
- Au moins 3 brokers pour la réplication (replication factor 2, port 9092)

Le DAG `lasc__livesim_fill` atteint la latence cible sans broker :
- Chaque tick : 2 000 lignes insérées en < 5 secondes
- Triggers SQL actifs : `fill_history_update_container` et `fill_history_alert` propagent immédiatement les états vers `containers` et `notifications`
- Idempotence : `ON CONFLICT DO NOTHING` sur `(container_id, measured_at)` arrondi à la minute

**Argument — Veille sur Kafka confirmée mais non retenue :**

L'analyse de la veille confirme que Kafka reste le choix optimal pour > 10 000 producteurs ou une latence < 500ms contrainte (cas MQTT pur). Pour le périmètre fil rouge, la cadence de 10 minutes est cohérente avec les cycles de collecte réels (aucune décision métier ne requiert une latence sub-seconde sur des données de remplissage qui évoluent en heures).

---

## II-C. Visualisation : Superset vs Metabase vs Grafana — Choix retenu : Grafana + FastAPI

### Proposition du template

Comparer Apache Superset, Metabase et Grafana sur facilité de création de dashboards, connecteurs BDD, performance, coût, communauté — pour des dashboards analytics temps réel.

### Solution implémentée

| Besoin | Outil retenu | Namespace K8s |
|---|---|---|
| Dashboards opérationnels infra | **Grafana** (datasource PostgreSQL + Prometheus) | `monitoring` |
| API analytics pour frontend | **FastAPI** (`/analytics/*`, 10 endpoints A1–A10) | `datalake` |
| Rapports PDF/Excel | **reportlab** + **openpyxl** (via `POST /reports/generate`) | `datalake` |

**Argument — Grafana déjà déployé, double datasource :**

Grafana est installé via `prometheus-community/kube-prometheus-stack` dans le namespace `monitoring` (voir `documentation/helmcharts/grafana.md`). Sa datasource PostgreSQL est configurée nativement et interroge directement `aggregated_daily_stats` et `fill_history` en SQL. Superset ou Metabase auraient requis un pod supplémentaire (~1 Gi RAM), un PVC pour la config, et un Ingress dédié — pour des dashboards fonctionnellement identiques.

**Résultat de la comparaison (veille conduite) :**

| Critère | Superset | Metabase | Grafana ✓ |
|---|---|---|---|
| Connexion PostgreSQL native | Oui | Oui | **Oui (actif en prod)** |
| Déjà dans le cluster | Non | Non | **Oui** |
| Coût opérationnel supplémentaire | +1 pod, +PVC | +1 pod, +PVC | **0** |
| Dashboards alertes (Prometheus) | Non | Non | **Oui** |
| API consommable par frontend React | Non | Non | Via FastAPI |

**Argument — FastAPI comme couche serving :**

La veille sur les outils BI conclut que Superset et Metabase sont orientés exploration autonome (self-service BI), alors que le frontend ECOTRACK consomme des données via des endpoints REST. Les 10 endpoints analytics (`/analytics/kpis`, `/heatmap`, `/choropleth`, etc.) définis dans `apiservice/routers/analytics.py` constituent la couche serving — entièrement découplée de l'outil de dashboarding.

---

## III-B. Tendances 2025 — Application concrète dans ECOTRACK

### Data Lakehouses (Delta Lake, Apache Iceberg)

**Application effective :** La logique Lakehouse (requêtes SQL directes sur données brutes + agrégats) est réalisée nativement par la coexistence de `fill_history` (table raw partitionnée) et `aggregated_*_stats` dans le même PostgreSQL. L'absence de fichiers Parquet ou Delta est un compromis conscient face à la contrainte de périmètre M1.

### DataOps et MLOps

**Application effective :** Le modèle ML est entraîné dans des notebooks Jupyter versionnés (`ml/01_eda_feature_engineering.ipynb`, `ml/02_training.ipynb`) avec export `model.pkl` + `metadata.json`. Le fichier `documentation/ml/index.md` documente un **retraining checklist** (4 étapes ML1 → ML5) conforme aux pratiques MLOps. Le déploiement préconisé est un PVC Kubernetes monté dans le pod `apiservice` (Option B dans le doc ML).

### Real-time Analytics

**Application effective :** Le DAG `lasc__livesim_fill` pousse des données toutes les 10 minutes. Les agrégats horaires sont recalculés immédiatement après chaque tick (`run_aggregations` task). L'endpoint `GET /analytics/kpis` interroge `aggregated_daily_stats` avec un temps de réponse cible < 100ms — sans Flink ni Materialize.

### Data Quality Observability

**Application effective :** Le flag `is_outlier BOOLEAN` sur `fill_history` (1 % des mesures simulées flaggées) remplace Monte Carlo. Les procédures `aggregate_hourly` et `aggregate_daily` filtrent `WHERE NOT is_outlier` pour garantir la qualité des KPIs. Un système d'alertes via le trigger `fill_history_alert` (notifications en base) couvre la détection proactive en < 1 tick (10 min).

---

## IV. Choix Technologiques Finaux — Récapitulatif

| Composant | Évalué | Retenu | Score comparatif | Justification principale |
|---|---|---|---|---|
| Batch processing | Spark / Dask / Ray | PostgreSQL stored procedures | N/A — hors périmètre volume | 18M lignes/an ne justifie pas un cluster distribué |
| Streaming IoT | Kafka / Pulsar / RabbitMQ | Airflow DAG (*/10 * * * *) | N/A — source unique simulée | Un unique processus Python n'est pas un cas d'usage broker |
| BI / Dashboards | Superset / Metabase / Grafana | Grafana + FastAPI | Grafana : déjà déployé, 0 coût additionnel | Datasource PostgreSQL native, alertes Prometheus intégrées |
| ML framework | LinearRegression / RandomForest | HistGradientBoosting | CV R²=0.673 (vs RF=0.522, LR=0.094) | Seul modèle atteignant R² > 0.65 sur les données réelles |
| Ingress | Nginx | Traefik | Helm chart officiel Traefik v3 | Routing hostname-based natif, TLS automation, dashboard intégré |
| Orchestration | Airflow (local) | Airflow + Celery (K8s) | 2 workers Celery + Redis | Scalabilité horizontale, isolation par namespace |

---

*Fichier d'argumentation — Document 2 Veille Technologique / filière M1 DATA & ANALYTICS*
*Sources : `documentation/ml/index.md`, `documentation/helmcharts/k8s-architecture.md`, `dags/lasc__livesim_fill.py`, `context/master1_data_tasks.md`*
