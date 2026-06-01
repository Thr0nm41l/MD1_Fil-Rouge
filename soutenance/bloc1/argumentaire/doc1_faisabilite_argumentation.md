# Document 1 — Étude de Faisabilité : Argumentation de l'Architecture Implémentée

> Ce document met en regard les préconisations du template M1 DATA & ANALYTICS avec les choix
> techniques effectivement réalisés dans le projet ECOTRACK, et argumente chaque écart.

---

## II-A. Architecture Data Lake — Ce qui a changé et pourquoi

### Proposition du template

Le template préconise une architecture Data Lake à trois couches hébergée sur **MinIO** (S3-compatible), avec des fichiers **Parquet** en Bronze Layer, **Delta Lake** (ACID) en Silver, et **TimescaleDB** en Gold.

### Solution implémentée

La couche de stockage repose entièrement sur **PostgreSQL 15 + PostGIS**, sans aucun composant de stockage objet. La logique « trois couches » est conservée mais traduite nativement en SQL :

| Couche template | Équivalent implémenté | Fichier de référence |
|---|---|---|
| Bronze (raw JSON/Parquet) | `fill_history` partitionnée par mois — données brutes avec flag `is_outlier` | `database/setup_complete.sql` l. 127–145 |
| Silver (nettoyée, validée) | Procédures `aggregate_hourly` / `aggregate_daily` + triggers de validation | `setup_complete.sql` §10 Functions |
| Gold (agrégats KPIs) | `aggregated_hourly_stats`, `aggregated_daily_stats`, `ml_predictions` | `setup_complete.sql` §6 OLAP Tables |

**Argument principal — Contrainte de périmètre M1 DATA :**
Le cahier des charges (`context/master1_data_tasks.md`) impose PostgreSQL 15 + PostGIS comme couche de persistance centrale et répertorie explicitement la table `fill_history` partitionnée par mois comme exigence `BDD5`. Introduire MinIO en parallèle aurait dupliqué la source de vérité sans apporter de valeur au périmètre de 115 tâches.

**Argument technique — Partitionnement natif vs stockage objet :**
La table `fill_history` est partitionnée par `measured_at` (range par mois). À ~500 000 lignes/jour, le query planner élimine les partitions hors période (_partition pruning_), ce qui permet les requêtes de séries temporelles en < 100 ms — objectif `H1` du CDC. TimescaleDB aurait fourni des hypertables comparables, mais PostgreSQL standard suffit au volume réel : 30 jours × 2 000 conteneurs × 24 h = **1 440 000 lignes** (vs. 180M/an sur une infrastructure ville entière).

**Argument opérationnel — Infrastructure unifiée :**
Le cluster Minikube (`documentation/helmcharts/k8s-architecture.md`) héberge déjà PostgreSQL dans le namespace `datalake`. Ajouter MinIO aurait requis un PVC supplémentaire et une logique de lecture Spark/Pandas absente du périmètre. PostgreSQL avec son moteur analytique couvre les besoins sans surcoût d'exploitation.

---

## II-B. Pipeline ETL / Streaming — Ce qui a changé et pourquoi

### Proposition du template

Le template propose : **Kafka** pour l'ingestion temps réel, **Spark Structured Streaming** pour le traitement, **Airflow** pour l'orchestration batch (7 DAGs), **Pydantic + Great Expectations** pour la qualité.

### Solution implémentée

L'architecture de pipeline s'articule autour de **quatre DAGs Airflow** à la place d'un stack Kafka + Spark :

| DAG | Rôle | Schedule |
|---|---|---|
| `lasc__seed_data` | Génération programmatique du jeu de données initial (1,44 M lignes) | Manuel |
| `lasc__livesim_fill` | Simulation IoT continue — 1 mesure/conteneur toutes les 10 min | `*/10 * * * *` |
| `lasc__ops_containers` | Opérations sur conteneurs déclenchées par l'API REST | Trigger API |
| `masc__clean_xcoms` | Nettoyage des XComs Airflow | Quotidien |

**Argument 1 — Ingestion programmatique vs import CSV :**

Le template mentionne l'import CSV (tâche `C7`) comme source d'alimentation initiale. La solution retenue utilise à la place le DAG `lasc__seed_data`, qui génère les données directement en Python (`psycopg2.extras.execute_values`, Faker `fr_FR`, bcrypt). Ce choix est motivé par trois points :

1. **Cohérence référentielle garantie** : les 2 000 conteneurs, leurs 2 000 devices IoT, les 5 zones géospatiales et les 1 440 000 lignes d'historique sont générés en une seule transaction coordonnée par le graphe de tâches Airflow (`seed_zones → seed_containers → seed_devices → seed_fill_history → run_aggregations`). Un import CSV multi-fichiers sans orchestration aurait risqué des violations de clés étrangères.
2. **Idempotence** : tous les `INSERT` utilisent `ON CONFLICT DO UPDATE / DO NOTHING` — le DAG peut être relancé sans dupliquer les données, contrainte critique pour un environnement de développement où le schéma est réinitialisé fréquemment.
3. **Simulation réaliste** : les niveaux de remplissage sont simulés avec un modèle physique par type de déchet (`FILL_RATE_PER_HOUR`, bruit gaussien σ=0,3, événements de collecte aléatoires) — un CSV statique ne peut pas reproduire cette variabilité.

**Argument 2 — Simulation continue vs Kafka :**

Le DAG `lasc__livesim_fill` (schedule `*/10 * * * *`) remplace Kafka pour le streaming IoT. Il lit l'état courant de `containers.fill_rate`, applique le modèle de remplissage, insère dans `fill_history`, et laisse les **triggers SQL** propager la mise à jour vers `containers` (trigger `fill_history_update_container`) et générer les alertes (trigger `fill_history_alert`).

Kafka aurait été pertinent pour une infrastructure multi-producteurs (2 000 capteurs physiques envoyant des messages MQTT). Dans le contexte du fil rouge, les capteurs sont simulés par un processus Python unique — un broker de messages aurait introduit une complexité opérationnelle (provisioning ZooKeeper/KRaft, topics, consumer groups) sans apport fonctionnel. Airflow avec PostgreSQL direct atteint la latence cible de < 2s sur le périmètre simulé.

**Argument 3 — Validation par contraintes SQL vs Great Expectations :**

La qualité des données est assurée à deux niveaux :

- **Au niveau schéma** : contraintes `CHECK` (`fill_rate BETWEEN 0 AND 100`, `status IN ('empty','normal','full','critical')`), `NOT NULL`, `UNIQUE`, et clés étrangères dans `setup_complete.sql`.
- **Au niveau ETL** : le flag `is_outlier BOOLEAN` sur `fill_history` marque les mesures aberrantes (1 % des insertions simulées) sans les supprimer, conformément à l'approche audit-first.
- **À l'agrégation** : les procédures `aggregate_hourly` et `aggregate_daily` filtrent les outliers (`WHERE NOT is_outlier`) lors du calcul des KPIs.

Great Expectations aurait apporté un reporting HTML de qualité, utile en production. Pour le périmètre M1, les contraintes SQL natives offrent les mêmes garanties avec zéro dépendance supplémentaire.

---

## II-C. Base de Données Analytique — Ce qui a changé et pourquoi

### Proposition du template

Le template préconise **TimescaleDB** (extension PostgreSQL) avec hypertables, compression automatique à 90 % après 7 jours, et une rétention de 2 ans pour les données brutes.

### Solution implémentée

**PostgreSQL 15 avec partitionnement natif par range** sur `fill_history(measured_at)`, sans l'extension TimescaleDB.

**Argument — Partitionnement natif vs hypertables :**

TimescaleDB ajoute des hypertables et une compression propriétaire, mais nécessite une installation d'extension spécifique sur le cluster. PostgreSQL 15 propose nativement :

- **Partitionnement range** par mois (`CREATE TABLE fill_history_2025_01 PARTITION OF fill_history FOR VALUES FROM ('2025-01-01') TO ('2025-02-01')`) — identique fonctionnellement aux hypertables pour le périmètre de 30 mois pré-créés.
- **Index composite descendant** `(container_id, measured_at DESC)` couvrant le pattern de requête dominant (épic H5 : `GET /history/:container_id`).
- **Clé primaire composée** `(key_history, measured_at)` requise par PostgreSQL pour les tables partitionnées — documentée dans `documentation/database/setup_complete.md`.

La compression après 7 jours (feature TimescaleDB) est remplacée par la stratégie d'archivage : détachement de partitions mensuelles (`DETACH PARTITION`) identifiée dans `setup_complete.md` §"What is intentionally outside the SQL script" comme tâche de maintenance Airflow future.

**Séparation OLTP / OLAP claire :**

| Couche | Tables | Objectif |
|---|---|---|
| OLTP | `containers`, `zones`, `users`, `routes`, `signalements`… | Opérations transactionnelles temps réel |
| OLAP | `fill_history` (partitionnée), `aggregated_hourly_stats`, `aggregated_daily_stats`, `ml_predictions` | Analytique et ML |

Cette séparation répond directement à la tâche `BDD3` (star schema `fill_history` + dimensions `dim_time`, `dim_container`, `dim_zone`) du cahier des charges.

---

## II-D. Visualisation et BI — Ce qui a changé et pourquoi

### Proposition du template

Le template suggère **Apache Superset ou Metabase** (open-source), Pandas + Matplotlib pour les exports PDF, et FastAPI + Redis pour l'API analytics.

### Solution implémentée

La couche visualisation repose sur :

| Composant | Outil retenu | Rôle |
|---|---|---|
| API analytics | **FastAPI** (`apiservice/`) déployé dans le namespace `datalake` | Endpoints `/analytics/*`, `/dashboard`, `/ml`, `/reports` |
| Cache | Redis (bundled dans le namespace `airflow`) | TTL sur agrégats fréquents, < 100ms P95 |
| Dashboards opérationnels | **Grafana** (namespace `monitoring`) avec datasource PostgreSQL directe | Métriques infra + données datalake en SQL |
| Observabilité infra | **Prometheus** + AlertManager + Node Exporter | MTTD < 5 min sur incidents cluster |

**Argument — Grafana vs Superset pour le périmètre M1 :**

Grafana est déjà déployé dans le cluster pour la supervision infrastructure (Prometheus). Sa **datasource PostgreSQL** native permet d'interroger directement `aggregated_daily_stats` et `fill_history` sans outil supplémentaire. Superset aurait requis un pod dédié (RAM ~1 Gi minimum), un PVC, et une configuration Helm supplémentaire — pour des dashboards identiques en termes de fonctionnalité sur le périmètre du fil rouge.

Le CDC (`master1_data_tasks.md`, tâches DA1–DA6) et les 10 graphiques analytics (A1–A10) sont exposés via l'API FastAPI (`apiservice/routers/analytics.py`, `dashboard.py`) consommée par le frontend — ce qui est exactement la brique "API Analytics FastAPI + cache Redis" préconisée par le template.

**API analytics réalisée :**

Les endpoints définis dans `apiservice/routers/` couvrent l'ensemble des tâches analytiques du CDC :

| Router | Endpoints | Tâches couvertes |
|---|---|---|
| `analytics.py` | `/analytics/volume-evolution`, `/type-distribution`, `/zone-collections`, `/fill-distribution`, `/heatmap`, `/choropleth`, `/costs-roi`, `/kpis` | A1–A10, H7 |
| `dashboard.py` | Layout config, KPI cards, export snapshot | DA1–DA6 |
| `ml.py` | `POST /ml/predict` | ML5 |
| `reports.py` | `POST /reports/generate`, `GET /reports/:id/download` | R1–R8 |

---

## Synthèse des écarts et justification globale

| Composant | Template M1 DATA | Solution implémentée | Justification principale |
|---|---|---|---|
| Stockage Raw | MinIO / Parquet | PostgreSQL `fill_history` partitionnée | Contrainte BDD5 CDC, infrastructure unifiée K8s |
| Ingestion initiale | Import CSV | DAG `lasc__seed_data` (Airflow + psycopg2) | Cohérence référentielle, idempotence, simulation réaliste |
| Streaming IoT | Apache Kafka | DAG `lasc__livesim_fill` (`*/10 * * * *`) | Source unique simulée, latence < 2s atteinte sans broker |
| Processing batch | Apache Spark | Stored procedures PostgreSQL + Airflow | Périmètre 1,44 M lignes ne justifie pas un cluster Spark |
| Validation qualité | Great Expectations | Contraintes SQL + flag `is_outlier` | Zéro dépendance supplémentaire, garanties équivalentes |
| BDD analytique | TimescaleDB | PostgreSQL 15 range partitioning | Extension non requise, partitionnement natif suffisant |
| BI / Dashboards | Superset ou Metabase | Grafana + FastAPI + Redis | Déjà déployé pour monitoring, datasource PostgreSQL native |

**Conclusion de faisabilité technique :** L'architecture implémentée est **FAVORABLE**. Elle répond à l'ensemble des 115 tâches du CDC en maintenant une stack cohérente (PostgreSQL + Airflow + FastAPI + Grafana) déployée sur un cluster Kubernetes (Minikube), sans les coûts d'exploitation d'un stack Big Data complet (Kafka + Spark + MinIO) dont le volume de données — 1,44 M lignes sur 30 jours — ne justifie pas la complexité.

---

*Fichier d'argumentation — Document 1 Étude de Faisabilité / filière M1 DATA & ANALYTICS*
*Sources : `database/setup_complete.sql`, `dags/lasc__seed_data.py`, `dags/lasc__livesim_fill.py`, `documentation/helmcharts/k8s-architecture.md`, `context/master1_data_tasks.md`, `context/master1_data_epics.md`*
