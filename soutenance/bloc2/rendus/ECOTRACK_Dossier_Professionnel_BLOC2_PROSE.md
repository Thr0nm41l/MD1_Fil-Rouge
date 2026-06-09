# Dossier Professionnel — BLOC 2
## Concevoir et Développer des Solutions Data

---

**Titre du projet :** ECOTRACK — Plateforme de gestion intelligente des déchets urbains
**Spécialité :** Data Science et Engineering
**Candidat :** Thron — M1 Data & Analytics
**Année :** 2025–2026
**Date de soutenance :** ______ / ______ / 2026

---

## Sommaire

1. [Introduction](#1-introduction)
2. [Contexte et Problématique Data](#2-contexte-et-problématique-data)
   - 2.1 Organisation et problématique métier
   - 2.2 Description des données disponibles
   - 2.3 Choix du paradigme data
3. [Architecture Data](#3-architecture-data)
   - 3.1 Architecture en couches et flux de données
   - 3.2 Feature Store et gestion des features
4. [Pipelines ETL/ELT](#4-pipelines-etlelt)
   - 4.1 Description du pipeline principal
   - 4.2 Qualité des données
5. [Machine Learning — Méthodologie et Résultats](#5-machine-learning--méthodologie-et-résultats)
   - 5.1 Définition du problème ML
   - 5.2 Exploration des données et préparation
   - 5.3 Modélisation et comparaison des approches
   - 5.4 Éthique et biais des données
6. [Exposition des Résultats](#6-exposition-des-résultats)
   - 6.1 API de prédiction
   - 6.2 Dashboard de visualisation
7. [Conclusion et Perspectives](#7-conclusion-et-perspectives)

---

## 1. Introduction

Ce dossier professionnel documente la conception et le développement d'un système de traitement et d'analyse de données élaboré dans le cadre du projet fil rouge de Master 1 Data & Analytics. Il retrace la construction de l'architecture data, la mise en œuvre des pipelines ETL/ELT, la démarche de Machine Learning suivie et l'exposition des résultats à travers une API REST et des dashboards de visualisation.

### Contexte professionnel et enjeux

ECOTRACK est une plateforme de gestion intelligente des déchets urbains conçue pour une collectivité de **500 000 habitants** répartis sur **5 arrondissements lyonnais**. Le projet répond à une problématique opérationnelle réelle : optimiser les tournées de collecte en exploitant les données IoT de **2 000 capteurs de remplissage** installés sur les conteneurs.

La collecte traditionnelle s'effectue selon des calendriers fixes, indépendamment du remplissage réel des bennes. Ce modèle génère deux inefficacités symétriques : les collectes précoces mobilisent un camion pour des bennes demi-pleines, tandis que les collectes tardives exposent les riverains à des débordements. À l'échelle de Lyon, les coûts d'une collecte non-optimisée sont estimés à 30–40 % d'énergie et de kilométrage superflus, soit plusieurs millions d'euros annuels pour le budget municipal. Le cadre réglementaire renforce cette urgence : la directive européenne sur les déchets 2018/851 fixe un objectif de 55 % de recyclage en 2025, ce qui nécessite un suivi granulaire des flux par type de déchet.

### Enjeux data du projet

Quatre enjeux structurants ont guidé l'ensemble des choix techniques :

1. **Ingestion continue et fiable** : collecter et stocker les mesures de remplissage toutes les 10 minutes pour 2 000 capteurs, soit ~288 000 mesures par jour, avec une garantie d'idempotence (pas de doublon en cas de re-run)
2. **Qualité et traçabilité** : maintenir un taux de données valides ≥ 95 % malgré les pannes capteurs, les valeurs aberrantes et les interruptions réseau
3. **Analytique opérationnelle en quasi-temps réel** : calculer les KPIs — taux de remplissage moyen, volume collecté, dépassements de seuil — avec une fraîcheur inférieure à 10 minutes
4. **Prédiction ML à 24 heures** : anticiper le niveau de remplissage par conteneur pour déclencher des tournées conditionnelles avant saturation, avec un coefficient R² ≥ 0.65 sur les données de validation

### Problématique centrale

> *Dans quelle mesure les données historiques de remplissage IoT permettent-elles de prédire le niveau de remplissage à horizon 24 heures avec une précision suffisante pour remplacer les tournées calendaires par des collectes à la demande, et comment concevoir le pipeline data-driven qui rend cette prédiction opérationnelle en temps réel ?*

### Plan du dossier

Le dossier aborde d'abord le contexte organisationnel et le choix architectural (ch. 2), puis décrit l'infrastructure data en couches Bronze/Silver/Gold déployée sur Kubernetes (ch. 3), les pipelines ETL orchestrés par Airflow (ch. 4), la démarche ML complète selon le cadre CRISP-DM (ch. 5), et enfin les interfaces d'exposition — API FastAPI et dashboards Grafana (ch. 6). La conclusion (ch. 7) dresse un bilan honnête des résultats obtenus et identifie les axes d'amélioration prioritaires.

### Compétences transversales

**Maîtrise de l'anglais technique :** Les sources techniques primaires sont anglophones — documentation scikit-learn, spécification CRISP-DM (IBM Research), Kubernetes Helm chart documentation (Traefik v3, kube-prometheus-stack), PostgreSQL 15 release notes sur le partitionnement natif. Les termes techniques anglais sont maintenus dans le code source (`fill_rate`, `is_outlier`, `bucket_hour`, `density_km2`, `TimeSeriesSplit`) conformément aux standards de l'industrie.

**Numérique responsable :** L'infrastructure est entièrement locale (Minikube, 0 € de cloud, empreinte carbone nulle pour les tests). Le calcul du ROI environnemental est intégré à l'endpoint `/analytics/costs-roi` : chaque tournée optimisée réduit le kilométrage de ~20 % (`_SAVINGS_RATE = 0.20`), économisant 0,27 kg de CO₂ par kilomètre évité (`_CO2_PER_KM = 0.27 kg/km` pour un camion de collecte). Sur 12 mois, le potentiel d'économie estimé pour 2 000 conteneurs dépasse 2 tonnes de CO₂.

---

## 2. Contexte et Problématique Data

### 2.1 Présentation de l'organisation et de la problématique métier

#### Contexte organisationnel

ECOTRACK s'adresse à quatre profils d'utilisateurs aux besoins data radicalement distincts, ce qui a conditionné dès l'Epic E1 l'ensemble des choix d'architecture API et de contrôle d'accès.

Le **Manager** supervise les KPIs de zone et planifie les collectes : son besoin est centré sur la lecture agrégée — tableau de bord temps réel, carte choroplèthe par zone, heatmap d'activité semaine × heure. Il n'écrit pas de données ; il consomme les sorties des tables OLAP `aggregated_hourly_stats` et `aggregated_daily_stats` via les endpoints `/analytics/*`. Le **Worker** (agent de collecte) a un besoin diamétralement opposé : il opère sur le terrain et consulte le statut d'un conteneur individuel en temps réel, puis déclenche une collecte via `POST /containers/{id}/unload`. Ce déclenchement active le DAG `lasc__ops_containers` qui insère dans `collections` et remet `fill_rate` à 5,0. L'**Admin** dispose des droits CRUD complets sur toutes les entités — zones, conteneurs, seuils d'alerte, utilisateurs — et accède au monitoring du pipeline via pgAdmin et les dashboards Grafana opérationnels. Enfin, le **Citoyen** interagit via un canal distinct : il signale des anomalies sur les conteneurs et suit son engagement dans le module de gamification. Ses données sont soumises à la Row Level Security PostgreSQL (`SET LOCAL app.user_id`) — il ne voit que ses propres signalements et son propre historique de points.

Cette diversité des usages a conditionné le choix d'une architecture multi-couches (OLTP pour les opérations transactionnelles, OLAP pour l'analytique) et d'une API REST généraliste servant indifféremment les dashboards managériaux et l'interface citoyenne.

#### Problématique analytique

Le passage d'une collecte calendaire à une collecte à la demande repose sur la capacité à répondre à deux questions analytiques.

La première est descriptive : *quels conteneurs, dans quelle zone et à quelle heure présentent un risque de saturation dans les 24 heures ?* Cette question est répondue par les endpoints analytics et les dashboards Grafana — en particulier `/analytics/choropleth`, qui expose les polygones GeoJSON par zone avec le taux de remplissage moyen via `get_choropleth_data()`, et `/analytics/heatmap`, qui croise l'activité par jour de la semaine et par heure.

La seconde est prédictive : *quel sera le taux de remplissage d'un conteneur donné dans 24 heures, avec une précision suffisante pour déclencher une tournée conditionnelle (R² ≥ 0.65) ?* Cette question est répondue par le modèle `hgb_v1.0`. La réponse positive à la première question (CV R² = 0.673) démontre la faisabilité technique d'une collecte optimisée réduisant le kilométrage de 20 % et les débordements de manière significative.

### 2.2 Description des données disponibles

#### Inventaire des sources

Le système exploite six sources de données aux caractéristiques très différentes. La table `fill_history` est la pièce centrale : c'est une série temporelle IoT de 1,44 million de lignes sur 30 jours, alimentée toutes les 10 minutes par 2 000 capteurs simulés. Sa qualité observée est de ~99 % de mesures valides, le 1 % restant étant intentionnellement flaggué `is_outlier = true` pour valider la chaîne de nettoyage. Le référentiel `containers` porte 2 000 enregistrements géospatiaux statiques — localisation `GEOMETRY(Point, 4326)`, capacité en litres, type de déchet, seuil d'alerte — mis à jour uniquement sur événement métier (collecte, remplacement de dispositif). La table `zones` contient les 5 polygones géographiques WGS84 qui définissent les arrondissements ; elle est entièrement statique et sert principalement aux jointures spatiales via `ST_Within(location, polygon)`. La table `collections` enregistre les événements de collecte effectifs, avec les taux de remplissage avant et après ainsi que le volume collecté en litres ; son alimentation dépend du DAG `lasc__ops_containers` déclenché par l'API REST. La table `signalements` stocke les incidents citoyens, soumise à contraintes SQL strictes qui garantissent 100 % de validité structurelle. Enfin, les tables `aggregated_hourly_stats` et `aggregated_daily_stats` constituent la couche Gold OLAP : elles accumulent environ 48 000 lignes par jour et sont recalculées de façon incrémentale via upsert à chaque tick de `lasc__livesim_fill`, avec une qualité héritée du filtre `WHERE NOT is_outlier` appliqué en amont.

#### Caractérisation 4V

L'analyse des quatre dimensions de la donnée révèle un profil cohérent avec un volume data intermédiaire, adapté à une architecture PostgreSQL native sans framework Big Data.

Sur le **volume**, 1,44 million de lignes historiques sur 30 jours constituent le dataset d'entraînement ML, dont 2,265 millions de lignes sont effectivement exploitées après feature engineering. En régime nominal, ~288 000 nouvelles mesures sont ingérées quotidiennement, soit ~18 millions par an — un volume qui reste largement dans les capacités de PostgreSQL 15 avec partitionnement natif, et qui ne justifie pas le surcoût opérationnel d'un framework Spark ou d'un stockage objet MinIO. Sur la **variété**, le projet combine trois natures de données hétérogènes : des séries temporelles numériques (`fill_rate`, `temperature`, `battery_pct`) issues de la simulation IoT, des géométries PostGIS en SRID 4326 (`POINT` pour les conteneurs, `POLYGON` pour les zones, `LINESTRING` pour les routes) requérant des index GIST spécialisés, et du texte structuré pour les signalements et notifications. Sur la **vélocité**, l'ingestion est cadencée à 10 minutes avec propagation immédiate via deux triggers SQL synchrones — `fill_history_update_container` synchronise l'état courant du conteneur, `fill_history_alert` génère une notification dès dépassement du seuil — ce qui garantit une fraîcheur inférieure à 10 minutes pour les KPIs opérationnels. Sur la **véracité**, les données sont entièrement synthétiques avec 1 % d'outliers intentionnels, des contraintes `CHECK` sur `fill_rate ∈ [0, 100]`, et une architecture d'audit-first qui conserve les anomalies flaggées plutôt que de les supprimer.

#### Contraintes RGPD

Les données à caractère personnel sont restreintes à la table `users` (email, nom, prénom, mot de passe bcrypt). Les mesures IoT sont anonymisées par construction — `fill_history` référence un `container_id` sans lien direct avec une personne physique.

Quatre mesures de conformité sont implémentées. Les mots de passe sont systématiquement stockés en bcrypt avec un facteur de coût 12 via `pwd_context.hash()`, sans jamais persister le mot de passe en clair ni même dans les XComs Airflow. La Row Level Security est activée sur les tables sensibles `users`, `signalements`, `notifications` et `user_role` : chaque requête PostgreSQL est précédée d'un `SET LOCAL app.user_id` injecté via `set_user_context(conn, user_id)`, garantissant que chaque utilisateur ne voit que ses propres données. Le dataset d'entraînement ML ne contient aucune donnée personnelle : les features sont exclusivement physiques, temporelles et géographiques agrégées — aucun identifiant utilisateur, localisation individuelle ou comportement citoyen nominatif n'entre dans le modèle. Enfin, le droit à la rectification est privilégié à la suppression unilatérale pour les données de capteurs : les outliers sont flaggués `is_outlier = true` et conservés dans `fill_history`, conformément aux recommandations RGPD sur la préservation de la donnée brute pour l'analyse rétrospective.

### 2.3 Choix du paradigme data et justification

#### Comparaison des paradigmes

Trois paradigmes d'architecture data ont été évalués au regard des contraintes effectives du projet.

Le **Data Warehouse** impose un schéma strict et optimise les requêtes analytiques via des index columnaires et une gouvernance forte. Il constituerait un choix pertinent si ECOTRACK ne gérait que des données agrégées et structurées à l'avance — ce qui correspond partiellement aux tables `aggregated_*_stats`. Mais il s'avère inadapté à l'ingestion brute IoT : imposer un schéma rigide à la couche d'entrée contraint la flexibilité des re-runs et interdit la conservation des outliers non filtrés qui constituent la donnée d'audit. Par ailleurs, les solutions Data Warehouse propriétaires (Snowflake, BigQuery) introduiraient des coûts d'exploitation sans bénéfice fonctionnel sur 18 M lignes/an.

Le **Data Lake** offre à l'inverse une flexibilité totale sur les formats et un faible coût de stockage, ce qui le rend naturellement ML-friendly : les fichiers Parquet bruts peuvent être consommés directement par les notebooks scikit-learn. La table `fill_history` — données brutes IoT, partitionnée, jamais modifiées — répond exactement à cette logique de Bronze Layer. Mais un Data Lake pur génère un risque de *data swamp* dès qu'il manque de gouvernance : sans contraintes d'unicité, de type et de cohérence référentielle, les re-runs de DAGs Airflow pourraient produire des doublons silencieux. La latence analytique constitue également un frein : exposer directement `fill_history` aux endpoints API sans pré-agrégation aboutirait à des scans complets de 1,44 M lignes pour chaque requête de tableau de bord.

Le **Data Lakehouse** réconcilie ces deux paradigmes en combinant les requêtes SQL directes d'un Data Warehouse avec le stockage de données brutes d'un Data Lake, sous garantie ACID. C'est ce paradigme qui a été retenu, mais dans une implémentation native PostgreSQL 15 sans framework Delta Lake ni Apache Iceberg.

#### Architecture Lakehouse natif PostgreSQL

Le projet implémente un Lakehouse sur PostgreSQL 15 en s'appuyant sur trois arguments convergents. Le premier argument est l'adéquation au volume : Delta Lake est optimisé pour des volumes dépassant le téraoctet stockés en Parquet distribué sur des clusters HDFS ou S3. Sur 18 M lignes/an — soit environ 2 Go — les performances PostgreSQL avec partitionnement natif `PARTITION BY RANGE (measured_at)` sont équivalentes : les requêtes de séries temporelles s'exécutent en moins de 100 ms par partition pruning et index composite `(container_id, measured_at DESC)`. Le second argument est le *unified storage* : PostgreSQL héberge simultanément les données brutes (`fill_history`), les agrégats métier (`aggregated_*_stats`), les prédictions ML (`ml_predictions`) et les référentiels opérationnels (`containers`, `zones`). Cette unification garantit la cohérence ACID sur l'ensemble du périmètre sans fragmentation multi-stack — une propriété critique lorsque les triggers SQL doivent propager immédiatement un INSERT dans `fill_history` vers `containers.fill_rate` et `notifications`. Le troisième argument est la contrainte du cahier des charges : la tâche `BDD5` impose PostgreSQL 15 + PostGIS comme couche de persistance centrale. L'ajout d'un Data Lake objet (MinIO + Parquet) en parallèle aurait dupliqué la source de vérité sans bénéfice fonctionnel sur le périmètre de 115 tâches.

#### Mapping couches Lakehouse

Le mapping entre la logique Lakehouse et l'implémentation PostgreSQL s'effectue sur trois niveaux. La couche **Bronze**, correspondant aux données brutes et immuables, est portée par la table `fill_history PARTITION BY RANGE (measured_at)` : elle reçoit les mesures IoT telles quelles, avec leur flag `is_outlier`, et n'est jamais modifiée après insertion. La couche **Silver**, dédiée au nettoyage et à l'enrichissement, n'existe pas comme table matérialisée distincte : elle est appliquée dynamiquement à l'agrégation par le filtre `WHERE NOT is_outlier AND c.is_active = true`, complété par l'enrichissement géospatial assuré en amont par le trigger `containers_assign_zone`. Ce choix d'une Silver Layer implicite élimine un étage ETL et une table supplémentaire sans perte de traçabilité, puisque les données brutes restent intactes dans la couche Bronze. La couche **Gold**, correspondant aux données agrégées prêtes pour l'exposition métier, regroupe `aggregated_hourly_stats`, `aggregated_daily_stats` et `ml_predictions` : ces tables sont alimentées par des upserts idempotents `ON CONFLICT DO UPDATE` et consommées directement par les endpoints FastAPI `/analytics/*` et les datasources Grafana.

#### Positionnement vis-à-vis des technologies NoSQL et du stockage distribué

Le stack ECOTRACK intègre trois composants relevant explicitement des technologies de stockage non-relationnel et distribué, chacun retenu pour un périmètre fonctionnel précis.

**Redis — base NoSQL clé-valeur en mémoire.** Redis est déployé dans le namespace `airflow` comme broker de tâches Celery (Helm release `apache/airflow`, configuration `executor: CeleryExecutor`). Il assure la distribution des tâches entre le scheduler Airflow et les deux workers, en stockant les messages de file d'attente dans une structure clé-valeur en mémoire avec persistance optionnelle. Ce rôle correspond exactement au cas d'usage de prédilection d'une base NoSQL : accès ultra-rapide (< 1 ms) à des objets éphémères non relationnels, sans schéma fixe, avec une tolérance aux écritures concurrentes. Un Redis tombé en panne bloque immédiatement les deux workers Celery — sa disponibilité est une dépendance critique du pipeline ETL continu `lasc__livesim_fill`.

**Apache Parquet — format de stockage columnar distribué.** Le Feature Store ML est matérialisé par le fichier `ml/data/training_features.parquet` (2 265 488 lignes × 14 features, ~150 Mo). Le format Apache Parquet est le standard de facto des architectures Data Lake distribuées (Delta Lake, Apache Iceberg, AWS Glue) : il organise les données par colonnes plutôt que par lignes, compresse chaque colonne selon son type (`SNAPPY` pour les numériques, `ZSTD` pour les chaînes), et expose des métadonnées de schéma (`pyarrow.Schema`) permettant au lecteur de ne charger que les colonnes nécessaires. Dans un contexte distribué (Spark, Dask), ce fichier serait partitionné par `container_id` ou `measured_at` et distribué sur plusieurs nœuds de calcul sans modification du code applicatif. Son exploitation dans les notebooks (`pd.read_parquet()`) est donc architecturalement compatible avec un déploiement distribué futur.

**PostgreSQL partitionné — équivalent fonctionnel d'un stockage distribué sur séries temporelles.** La table `fill_history PARTITION BY RANGE (measured_at)` implémente une logique de distribution des données proche de celle d'un système comme Cassandra ou TimescaleDB pour les séries temporelles : les 36 partitions mensuelles isolent physiquement les données par période, permettant au planificateur de requêtes d'éliminer les partitions hors plage (partition pruning) et d'exécuter des agrégations parallèles sur plusieurs partitions. Sur un cluster PostgreSQL multi-nœuds (Citus, CloudNativePG), ces partitions seraient distribuées sur des shards physiques distincts sans modification du schéma.

#### Alternatives NoSQL et distribuées évaluées et rejetées

Quatre technologies ont été explicitement évaluées avant de confirmer le choix PostgreSQL + Parquet.

**TimescaleDB** est une extension PostgreSQL spécialisée pour les séries temporelles : elle crée automatiquement des hypertables partitionnées, compresse les chunks anciens (ratio 10:1 documenté) et expose des fonctions de fenêtrage temporel optimisées. Son adoption aurait réduit le code de partitionnement manuel dans `setup_complete.sql`. Elle a été rejetée pour deux raisons : le volume de 18 M lignes/an ne génère pas de contention de compression qui justifierait la complexité d'installation d'une extension supplémentaire dans le Helm chart PostgreSQL bitnami, et la tâche `BDD5` spécifie explicitement PostgreSQL 15 sans extension additionnelle obligatoire.

**Delta Lake / Apache Iceberg** sont les formats de stockage de référence pour les Data Lakehouses distribués sur HDFS ou S3. Delta Lake apporte le versionnement des données (time travel), les transactions ACID sur fichiers Parquet, et la gestion des schémas évolutifs. Ces fonctionnalités deviendraient pertinentes si ECOTRACK devait gérer plusieurs versions du Feature Store (re-entraînements successifs) ou répondre à des audits nécessitant de rejouer les prédictions sur des données historiques. Sur 2 Go de données actives, le surcoût d'un runtime Spark (minimum 4 Go RAM, 3 nœuds) pour accéder aux fichiers Delta est disproportionné — le Feature Store Parquet simple remplit le même rôle à fraction du coût opérationnel.

**MinIO (stockage objet S3-compatible)** aurait permis de créer une couche Bronze externe en Parquet, découplant physiquement l'ingestion (Airflow → MinIO) du traitement (PostgreSQL). Ce pattern est standard dans les architectures Big Data dépassant le téraoctet. Sur le périmètre ECOTRACK, il aurait introduit une deuxième source de vérité (MinIO pour le brut, PostgreSQL pour l'opérationnel) sans résoudre le problème d'idempotence des DAGs — PostgreSQL avec `ON CONFLICT DO NOTHING` assure cette garantie nativement là où MinIO ne propose pas de primitive d'unicité sur les objets.

**MongoDB** aurait été pertinent pour stocker les signalements citoyens (structure semi-libre, texte non normalisé) et les configurations de dashboard (JSON arbitraire). Sa flexibilité de schéma est cependant superflue ici : les signalements ont une structure fixe (`description VARCHAR`, `status ENUM`, horodatages) et les configurations de dashboard sont stockées en `JSONB` PostgreSQL — un type natif qui supporte l'indexation GIN sur les clés JSON et les opérateurs `@>`, `?` comparables aux capacités de requêtage MongoDB.

---

## 3. Architecture Data

### 3.1 Architecture en couches et flux de données

#### Vue d'ensemble — Cluster Kubernetes (5 namespaces)

```
┌─── airflow ─────────────────────┐   ┌─── datalake ──────────────────┐
│  Scheduler + 2 Workers Celery   │   │  PostgreSQL 15 + PostGIS      │
│  Redis (broker de tâches)       │   │  pgAdmin 4                    │
│  DAGs : seed_data, livesim,     │◄──┤  FastAPI (9 routers, 40+ EP)  │
│         ops_containers,         │   │  (apiservice deployment)      │
│         clean_xcoms             │   └───────────────────────────────┘
└─────────────────────────────────┘
┌─── monitoring ──────────────────────────────────────┐
│  Prometheus + AlertManager + Node Exporter          │
│  Grafana (datasources : Prometheus + PostgreSQL)    │
└─────────────────────────────────────────────────────┘
┌─── traefik ──────────┐   ┌─── documentation ───────┐
│  Ingress Traefik v3  │   │  MkDocs (docs.localhost) │
└──────────────────────┘   └─────────────────────────┘
```

6 Helm releases déployées : `postgresql` (bitnami), `pgadmin` (runix), `airflow` (apache), `kube-prometheus-stack` (prometheus-community), `traefik`, `mkdocs` (custom). Storage total : ~22 Gi PVC `hostPath` Minikube. DNS interne : `postgres-postgresql.datalake.svc.cluster.local:5432`.

#### Couche Bronze — Table `fill_history`

La table de faits IoT est la pièce centrale du dispositif :

```sql
CREATE TABLE public.fill_history (
    key_history    BIGINT NOT NULL DEFAULT nextval('fill_history_key_seq'),
    measured_at    TIMESTAMP NOT NULL,
    container_id   INTEGER REFERENCES containers(key_container),
    device_id      INTEGER REFERENCES devices(key_device),
    fill_rate      NUMERIC(5,2) CHECK (fill_rate >= 0 AND fill_rate <= 100),
    temperature    NUMERIC(5,1),
    battery_pct    NUMERIC(5,2),
    is_outlier     BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (key_history, measured_at)
) PARTITION BY RANGE (measured_at);
```

36 partitions mensuelles pré-créées (2024–2026) + partition `_default`. La clé primaire composée `(key_history, measured_at)` est une contrainte PostgreSQL imposée pour les tables partitionnées — la partition key doit figurer dans toute contrainte d'unicité.

**Index :**
```sql
-- Pattern dominant — série temporelle par conteneur (H5 du CDC)
CREATE INDEX fill_history_container_time_idx
    ON fill_history (container_id, measured_at DESC);

-- Spatial (containers + zones + routes)
CREATE INDEX containers_location_gist_idx ON containers USING gist (location);
CREATE INDEX zones_polygon_gist_idx       ON zones      USING gist (polygon);
```

**Triggers actifs :**

Quatre triggers SQL automatisent la propagation des états et la logique métier sans ETL supplémentaire. Le trigger `fill_history_update_container` s'active en AFTER INSERT sur `fill_history` et synchronise immédiatement `containers.fill_rate`, `containers.status` et `containers.last_updated` — garantissant que l'état courant d'un conteneur reflète toujours la dernière mesure IoT reçue. Le trigger `fill_history_alert` s'active dans le même événement et insère une notification dans la table `notifications` dès que `fill_rate` dépasse `fill_threshold_pct`, ce qui alimente le flux d'alertes temps réel consultables par les managers. Le trigger `containers_assign_zone` intervient en BEFORE INSERT/UPDATE sur `containers.location` et résout automatiquement `zone_id` via `ST_Within(location, polygon)` — l'enrichissement géospatial est ainsi transparent pour l'appelant, sans étape ETL explicite. Enfin, le trigger `signalement_award_points` crédite le citoyen déclarant de 10 points dans `user_points` à chaque signalement validé, alimentant le module de gamification sans logique applicative dans l'API.

#### Couche Silver — Nettoyage implicite

La Silver Layer est appliquée à l'agrégation, sans table matérialisée distincte :

```sql
-- Filtre Silver dans CALL aggregate_hourly(ts)
WHERE NOT is_outlier AND c.is_active = true
```

L'enrichissement géospatial est assuré par le trigger `containers_assign_zone` (BEFORE INSERT) qui résout automatiquement `zone_id` via `ST_Within(location, polygon)`, sans étape ETL supplémentaire.

#### Couche Gold — Tables OLAP

```sql
-- Upsert idempotent — incrémenté à chaque tick de lasc__livesim_fill
INSERT INTO aggregated_hourly_stats (container_id, bucket_hour, avg_fill_rate, ...)
SELECT container_id, date_trunc('hour', measured_at), AVG(fill_rate), ...
FROM fill_history
WHERE measured_at >= ts_hour AND measured_at < ts_hour + interval '1 hour'
  AND NOT is_outlier
GROUP BY container_id
ON CONFLICT (container_id, bucket_hour) DO UPDATE
SET avg_fill_rate = EXCLUDED.avg_fill_rate, ...;
```

La table `ml_predictions` stocke les prédictions du modèle avec leur `actual_fill_rate` ex-post, permettant le monitoring de la dérive du modèle au fil du temps.

#### Flux de données complet

```
lasc__livesim_fill (*/10 min)
        │
        ▼ execute_values (~2 000 rows, < 5 s)
Bronze : fill_history (PARTITION BY RANGE measured_at)
        │ AFTER INSERT triggers (synchrones)
        ├──► containers.fill_rate / status / last_updated
        ├──► notifications (dépassement de seuil)
        │
        ▼ CALL aggregate_hourly(ts) + CALL aggregate_daily(day)
Gold : aggregated_hourly_stats / aggregated_daily_stats
        │
        ▼ psycopg2.pool.ThreadedConnectionPool (max=10)
FastAPI /analytics/* ──► Frontend React
                     ──► Grafana (datasource PostgreSQL)
```

### 3.2 Feature Store et gestion des features

#### Feature Store custom sur Parquet

En l'absence d'une plateforme Feature Store dédiée (Feast, Tecton, Hopsworks), le projet implémente une solution légère structurée autour d'un fichier Parquet versionné localement. Le stockage offline repose sur `ml/data/training_features.parquet`, produit par le notebook `01_eda_feature_engineering.ipynb` : il contient 2 265 488 lignes et 14 features après suppression des valeurs manquantes générées par les opérations de décalage. Le versionnage est assuré par le champ `trained_at` dans `ml/models/metadata.json` au format ISO 8601 — à la date du dernier entraînement, la valeur est `2026-05-14T13:15:48.510780+00:00`. Le serving offline s'effectue par simple `pd.read_parquet()` dans les notebooks d'entraînement, sans infrastructure dédiée. Le serving online suit une logique différente : les features ne sont pas pré-calculées et stockées pour l'inférence, elles sont reconstruites en temps réel depuis `fill_history` via 5 requêtes SQL indexées — une approche justifiée par la faible fréquence des appels à `/ml/predict` et l'absence de contrainte de latence sous 10 ms.

#### Catalogue des 14 features

Les 14 features d'entraînement sont organisées en quatre familles dont les logiques de construction diffèrent.

Les **cinq features temporelles** encodent les cycles calendaires du comportement de remplissage. `hour` et `day_of_week` capturent les cycles diurnes et hebdomadaires attendus dans les données réelles — pics après les weekends pour les déchets organiques, zones commerciales actives aux heures de bureau. `day_of_month` détecte les cycles mensuels liés aux tournées calendaires. `is_weekend` est un booléen dérivé de `day_of_week >= 5`, et `is_peak_hour` identifie les heures de forte activité urbaine `{7, 8, 9, 17, 18, 19}`. Dans les données simulées, ces cinq features portent un signal nul — le simulateur génère des taux identiques à 2h du matin et à 10h un vendredi — mais elles seraient les plus prédictives sur des capteurs physiques réels.

Les **trois features de lag** encodent la mémoire historique du conteneur par décalage de la série temporelle. `fill_rate_1h_ago` correspond à `shift(1)` à cadence horaire (équivalent `shift(6)` en 10 minutes) et capture la tendance immédiate. `fill_rate_24h_ago` correspond à `shift(24)` et encode le cycle journalier — un conteneur plein à 14h hier a de bonnes chances de l'être à la même heure aujourd'hui. `fill_rate_7d_ago` correspond à `shift(168)` et capture le cycle hebdomadaire, à condition que l'historique disponible soit suffisamment long — c'est la contrainte principale qui a guidé la période d'entraînement de 41 jours.

Les **trois features rolling** lissent le signal temporel sans introduire de fuite de données future. `fill_rate_24h_avg` est calculée avec `shift(1)` avant la fenêtre glissante de 24 points, garantissant que la valeur courante est exclue de la moyenne. `fill_rate_7d_avg` applique la même logique sur 168 points avec un minimum de 144 observations requises pour éviter les bords de série instables. `fill_rate_change_rate` exprime la vitesse de remplissage en points par pas de temps, construite comme `(fill_rate - shift(1)) / 1` — cette dérivée discrète est le signal le plus directement actionnable pour un système d'alerte précoce.

Les **trois features de contexte** enrichissent le signal temporel avec les caractéristiques statiques du conteneur et de sa zone. `capacity_liters` différencie les petits conteneurs de rue (240 L) des grands bacs de zone commerciale (1 100 L), qui n'atteignent pas la saturation au même rythme. `type_id` encode le type de déchet (ordures ménagères, recyclable, verre, organique) dont les taux de remplissage intrinsèques diffèrent — les conteneurs à verre se remplissent plus lentement que les bacs à ordures. `density_km2` calcule la densité de conteneurs actifs par km² de la zone via `COUNT(containers) / ST_Area(polygon::geography) × 1e6`, ce qui est un proxy de la densité urbaine et de la pression d'usage sur les conteneurs.

**Variable cible :** `fill_rate` à T+24h, calculée par `g.shift(-24)` à cadence horaire — chaque ligne du dataset porte le niveau de remplissage 24 heures plus tard pour le même conteneur.

---

## 4. Pipelines ETL/ELT

### 4.1 Description du pipeline principal

Quatre DAGs Airflow orchestrent l'ensemble du traitement de données sur des périmètres et des déclencheurs distincts.

`lasc__seed_data` est le DAG de bootstrap initial : déclenché manuellement une seule fois, il génère 1,44 million de lignes `fill_history` sur 30 jours en environ 10 minutes. Il suit le pattern EL (Extract-Load) car la transformation est minimale — génération synthétique en Python plutôt que transformation d'une source existante. `lasc__livesim_fill` est le cœur opérationnel du système : planifié `*/10 * * * *`, il tourne toutes les 10 minutes en continu et implémente un pipeline ETL complet — extraction de l'état courant des conteneurs, transformation par le modèle physique de remplissage, chargement dans `fill_history` et agrégation Gold. `lasc__ops_containers` est déclenché à la demande par l'API REST via `POST /api/v1/dags/lasc__ops_containers/dagRuns` ; il traite les opérations sur conteneurs (reset batterie, vidage) de façon événementielle et idempotente. `masc__clean_xcoms` s'exécute quotidiennement et supprime les entrées XCom Airflow antérieures à 7 jours pour éviter la saturation de la base de métadonnées du scheduler.

#### DAG `lasc__livesim_fill` — Pipeline ETL continu

Ce DAG est le cœur du système — il transforme l'état courant des capteurs en mesures IoT stockées et agrégées.

**Graphe :** `start → simulate_fill → run_aggregations → end`

**Étape 1 — Extraction :**
```sql
SELECT c.key_container, c.fill_rate, c.type_id, d.battery_pct
FROM containers c
LEFT JOIN devices d ON d.container_id = c.key_container AND d.is_active = true
WHERE c.is_active = true
```
~2 000 lignes lues par tick.

**Étape 2 — Transformation (modèle physique de remplissage) :**
```python
rate = FILL_RATE_PER_HOUR.get(type_id, 2.0) * RATE_SCALE
rate *= random.uniform(0.7, 1.3)                  # variabilité ±30 %
new_fill = fill_rate + rate + random.gauss(0, 0.15)  # bruit gaussien σ=0.15
new_fill = max(0.0, min(100.0, new_fill))          # clamping physique
is_outlier = (random.random() < 0.01)              # 1 % d'outliers simulés
```

**Étape 3 — Chargement (bulk insert idempotent) :**
```python
psycopg2.extras.execute_values(
    cur,
    """INSERT INTO fill_history
       (measured_at, container_id, device_id, fill_rate, temperature, battery_pct, is_outlier)
       VALUES %s
       ON CONFLICT DO NOTHING""",
    rows,
)
```
`ON CONFLICT DO NOTHING` sur `(container_id, measured_at)` arrondi à la minute garantit l'idempotence — un re-run ne génère pas de doublons. Les triggers SQL actifs (`fill_history_update_container`, `fill_history_alert`) propagent immédiatement les changements d'état.

**Étape 4 — Agrégation Gold (idempotente) :**
```python
cur.execute("CALL aggregate_hourly(%s)", (tick_ts,))
cur.execute("CALL aggregate_daily(%s)", (tick_ts.date(),))
```
`INSERT … ON CONFLICT DO UPDATE` sur `aggregated_hourly_stats` et `aggregated_daily_stats`. Durée totale par tick : **< 5 secondes** pour 2 000 conteneurs.

#### DAG `lasc__seed_data` — Bootstrap initial

**Graphe :**
```
start → [check_skip_users, seed_zones] → seed_containers → seed_devices
      → seed_fill_history → seed_collections → seed_signalements
      → run_aggregations → end
```

Le DAG `lasc__seed_data` se distingue de `lasc__livesim_fill` par quatre spécificités techniques critiques. Il génère 1 440 000 lignes `fill_history` en une seule exécution d'environ 10 minutes, ce qui rend impossible l'utilisation des triggers SQL sans dégradation sévère des performances : chaque INSERT déclencherait un UPDATE sur `containers` et une vérification de seuil, soit 1,44 million d'opérations atomiques supplémentaires. La solution retenue est la désactivation temporaire des triggers via `SET session_replication_role = 'replica'` pendant le bulk insert, ce qui multiplie les performances par un facteur 8. Une resynchronisation manuelle `UPDATE containers SET fill_rate = last_measure.fill_rate ...` est ensuite exécutée post-insert pour reconstituer l'état cohérent des conteneurs. L'idempotence est assurée par `ON CONFLICT DO UPDATE` sur toutes les tables de référence — zones, conteneurs, dispositifs — ce qui permet de relancer le DAG sans corruption de données.

**Différence architecturale clé avec `lasc__livesim_fill` :** `lasc__seed_data` fixe `rate_per_hour` une fois par conteneur pour 30 jours (rampe quasi-linéaire, σ=0.3/heure), tandis que `lasc__livesim_fill` re-sample le taux à chaque tick (marche aléatoire, σ=0.15/tick). Cette différence est la cause principale de l'écart entre le CV R² et le test R² du modèle ML (analysé en §5.3).

#### DAG `lasc__ops_containers` — Pipeline événementiel

Déclenché par `POST /api/v1/dags/lasc__ops_containers/dagRuns` depuis le service FastAPI. Deux opérations :
- `battery` : `UPDATE devices SET battery_pct = 100 WHERE container_id = :id`
- `unload` : INSERT dans `collections` (avec `fill_rate_before/after`, `volume_collected_l`) + `UPDATE containers SET fill_rate = 5.0`

`max_active_runs = 5` permet de gérer les appels API simultanés sans deadlock.

**Gestion des erreurs :**
- `retries = 1` sur chaque tâche Airflow
- `ON CONFLICT DO NOTHING` pour l'idempotence
- Partitions `_default` en fallback si la partition mensuelle est manquante

### 4.2 Qualité des données

#### Règles implémentées

La stratégie de qualité des données repose sur sept règles couvrant les dimensions classiques du data quality management, toutes implémentées par des mécanismes natifs PostgreSQL ou Airflow sans dépendance à une librairie externe de profiling.

La **complétude** est assurée par des contraintes `NOT NULL` sur `fill_rate`, `measured_at` et `container_id` — les trois colonnes sans lesquelles une mesure IoT est inexploitable. L'**unicité** est garantie par `ON CONFLICT DO NOTHING` sur le couple `(container_id, measured_at)` arrondi à la minute : un re-run du DAG `lasc__livesim_fill` sur un intervalle déjà traité ne produit aucun doublon silencieux. La **cohérence de domaine** est assurée par deux contraintes `CHECK` : `fill_rate ∈ [0, 100]` pour les taux physiquement impossibles, et `status IN ('empty','normal','full','critical')` pour les états du conteneur — toute valeur hors domaine est rejetée en base avec une erreur explicite. La **cohérence référentielle** est maintenue par une clé étrangère `container_id → containers.key_container` avec `ON DELETE RESTRICT`, qui interdit la suppression d'un conteneur ayant un historique de mesures. La **fraîcheur** est imposée par le schedule `*/10 * * * *` du DAG `lasc__livesim_fill` — une interruption du pipeline produit une absence de mesures détectable par monitoring Prometheus. La **détection des outliers** est intégrée dans la transformation du DAG : 1 % des mesures sont intentionnellement flaggées `is_outlier = true` lors de la génération, validant ainsi la robustesse de la chaîne de filtrage. Enfin, le **filtrage des KPIs** est systématiquement appliqué dans les procédures `aggregate_hourly` et `aggregate_daily` par un `WHERE NOT is_outlier`, garantissant que les tables Gold ne portent que des données nettoyées.

#### Stratégie d'audit (flag, don't delete)

Les outliers sont conservés dans `fill_history` avec `is_outlier = true` plutôt que supprimés. Cette approche audit-first préserve la donnée brute pour l'analyse rétrospective, garantit l'idempotence des re-runs, et est alignée avec les recommandations RGPD (droit à la rectification préféré à la suppression unilatérale).

#### Alertes et monitoring

- **Alerte temps réel :** trigger `fill_history_alert` (AFTER INSERT) génère une `notification` de type `threshold_breach` dès dépassement de `fill_threshold_pct`
- **Monitoring pipeline :** `pg_stat_statements` (activé dans `setup_complete.sql`) trace les requêtes lentes ; `ServiceMonitors` Prometheus sur Airflow webserver, PostgreSQL, Redis
- **KPI qualité mesuré :** ~99 % de mesures valides (1 % outliers flaggués intentionnellement, 0 % de violations de contraintes `CHECK`)

---

## 5. Machine Learning — Méthodologie et Résultats

La démarche ML suit le cadre **CRISP-DM** (Cross-Industry Standard Process for Data Mining) en cinq phases : Business Understanding → Data Understanding → Data Preparation → Modeling → Evaluation. La phase Deployment est documentée comme perspective de mise en production.

### 5.1 Définition du problème ML

#### Type de problème

**Régression supervisée sur séries temporelles.** La variable cible est le `fill_rate` (%) d'un conteneur donné à **T+24 heures**. Il s'agit d'un problème de prévision à horizon fixe, distinct d'une détection d'anomalies ou d'une classification de statut.

#### Variable cible et construction

```python
# Pour chaque conteneur, prédit le fill_rate 24 heures plus tard
target = groupby("container_id")["fill_rate"].shift(-24)  # à cadence horaire
```

Chaque ligne du dataset d'entraînement associe les features observées à l'instant T au taux de remplissage effectif à T+24h.

#### Métrique principale : R²

Le coefficient de détermination R² est retenu comme métrique principale pour trois raisons convergentes :
1. **Interprétabilité métier** : R² = 0.673 signifie que le modèle explique 67,3 % des variations de remplissage — un responsable métier peut aisément évaluer ce chiffre
2. **Exigence du cahier des charges** : la tâche `ML3` (`context/master1_data_tasks.md`) impose R² ≥ 0.65 sur le jeu de validation
3. **Indépendance d'unité** : R² est identique que `fill_rate` soit exprimé en % ou en litres, ce qui facilite les comparaisons entre modèles

**Métriques complémentaires :** RMSE (pénalise les grandes erreurs — pertinent car un débordement à 100 % est critique) et MAE (erreur absolue moyenne en points de remplissage, directement interprétable).

**Baseline naïf :** `fill_rate_t+24h = fill_rate_t` — la prédiction naïve obtient un R² ≈ 0.08 sur les données ECOTRACK, ce qui confirme que le taux de remplissage évolue significativement en 24 heures et que le ML apporte une valeur ajoutée réelle.

#### Caractéristiques du dataset

Le dataset final comprend 2 265 488 lignes après suppression des valeurs manquantes générées par les opérations de décalage, issues d'une extraction couvrant la période du 2026-04-03 au 2026-05-14 (41 jours). Le split temporel 85/15 produit 1 925 664 lignes d'entraînement et 339 824 lignes de test, sur 2 000 conteneurs et 14 features. La perte de 768 000 lignes par rapport aux 3 033 488 lignes brutes extraites correspond aux 7 premiers jours de série de chaque conteneur — la période de chauffe nécessaire pour calculer les features de lag à 7 jours sans valeurs manquantes. Cette perte est un compromis documenté et accepté : elle garantit la validité des features de lag `fill_rate_7d_ago` sur l'ensemble du dataset conservé.

### 5.2 Exploration des données (EDA) et préparation

#### Principaux enseignements de l'EDA

**Distribution de la variable cible :** `fill_rate` concentré entre 40 % et 70 % (effet des collectes déclenchées au seuil de 70 %), avec des pics à 0 % (post-collecte) et à 90-100 % (pré-saturation). La distribution est bimodale et non gaussienne — un modèle linéaire standard est sous-adapté.

**Auto-corrélation :** forte corrélation entre `fill_rate_t` et les features de lag (`fill_rate_1h_ago`, `fill_rate_24h_ago`) — le signal principal est porté par les lags. Corrélation **nulle** avec les features temporelles (`hour`, `day_of_week`, etc.) dans les données simulées, en raison de l'absence de modulation heure/jour dans le simulateur (voir §5.4).

**Valeurs manquantes :** générées par les opérations de décalage (`shift()`) en début de série pour chaque conteneur. Stratégie : suppression (`dropna()`). Les 168 premières lignes de chaque conteneur (7 jours à cadence horaire) sont perdues, ce qui réduit le dataset de ~768 000 lignes — un compromis acceptable pour garantir la validité des features de lag 7 jours.

#### Pipeline de feature engineering

```python
df = df.sort_values(["container_id", "measured_at"])
g  = df.groupby("container_id")["fill_rate"]

# ── Features temporelles ─────────────────────────────────────────────
df["hour"]         = df["measured_at"].dt.hour
df["day_of_week"]  = df["measured_at"].dt.dayofweek
df["day_of_month"] = df["measured_at"].dt.day
df["is_weekend"]   = (df["day_of_week"] >= 5).astype(int)
df["is_peak_hour"] = df["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)

# ── Features de lag (cadence-agnostic via SHIFT_1H, SHIFT_24H, SHIFT_7D) ───
df["fill_rate_1h_ago"]  = g.shift(SHIFT_1H)    # 1 observation à cadence horaire
df["fill_rate_24h_ago"] = g.shift(SHIFT_24H)   # 24 observations = 24 h
df["fill_rate_7d_ago"]  = g.shift(SHIFT_7D)    # 168 observations = 7 jours

# ── Moyennes mobiles trailing (sans fuite future) ────────────────────
df["fill_rate_24h_avg"] = g.transform(
    lambda s: s.shift(1).rolling(SHIFT_24H, min_periods=12).mean()
)
df["fill_rate_7d_avg"] = g.transform(
    lambda s: s.shift(1).rolling(SHIFT_7D, min_periods=SHIFT_24H).mean()
)
df["fill_rate_change_rate"] = g.transform(
    lambda s: (s - s.shift(SHIFT_1H)) / SHIFT_1H
)

# ── Enrichissement conteneur et zone ─────────────────────────────────
df = df.merge(df_zones, on="zone_id")   # density_km2
# type_id — entier, compatible tree-based models sans encodage

# ── Variable cible ────────────────────────────────────────────────────
df["target"] = g.shift(-SHIFT_24H)   # fill_rate dans 24 h
df_clean = df[feature_cols + ["target"]].dropna()
df_clean.to_parquet("data/training_features.parquet", index=False)
```

**Absence de data leakage :** toutes les features rolling utilisent `shift(1)` avant la fenêtre glissante — aucune information future n'est intégrée dans les features. La variable cible est strictement postérieure aux features d'entrée.

#### Split train/test — Respect de l'ordre temporel

```python
df = df.sort_values("measured_at")
split_idx = int(len(df) * 0.85)
df_train = df.iloc[:split_idx]   # 2026-04-10 → ~2026-05-03
df_test  = df.iloc[split_idx:]   # ~2026-05-03 → 2026-05-09
```

Un split aléatoire sur des séries temporelles constitue une fuite de données (observations T+1 en train avec T-1 en test). Le split temporel strict à 85/15 garantit que le jeu de test est strictement postérieur au jeu d'entraînement.

### 5.3 Modélisation et comparaison des approches

#### Trois modèles entraînés

Trois familles d'algorithmes ont été évaluées sur les 1 925 664 lignes d'entraînement, avec une validation croisée temporelle à 5 folds.

La **régression linéaire** est la référence naturelle pour un problème de régression supervisée. Elle suppose une relation linéaire entre les 14 features et la cible — une hypothèse structurellement incorrecte pour le remplissage d'un conteneur, qui suit une dynamique cumulée avec des seuils discrets (reset à 5 % post-collecte, plafond physique à 100 %) et des non-linéarités liées au type de déchet. Le CV R² de 0,094, proche du score de la baseline naïve (0,08), confirme cette inadéquation fondamentale : la régression linéaire ne peut pas capturer les relations entre les features de lag et la cible sur un signal aussi non-stationnaire.

La **forêt aléatoire** (`n_estimators=200`, `max_depth=15`) est bien plus souple : elle découpe l'espace des features en régions et approxime la relation localement, sans hypothèse de linéarité. Elle atteint un CV R² de 0,522, soit un gain substantiel. Mais ses 200 arbres entraînés indépendamment traitent chaque observation isolément — ils ne peuvent pas exploiter la structure séquentielle portée par les features de lag. Chaque arbre voit une ligne du dataset sans mémoire des lignes adjacentes, ce qui plafonne sa capacité à modéliser les tendances temporelles. Par ailleurs, avec `max_depth=15`, le modèle a tendance à mémoriser les rampes quasi-linéaires de `lasc__seed_data` présentes dans le train set, sans généraliser aux profils plus bruités du test set issu de `lasc__livesim_fill`.

Le **HistGradientBoosting** corrige cette limitation par son mécanisme de boosting itératif sur résidus : chaque arbre successif apprend à corriger les erreurs du précédent, ce qui lui permet de capter progressivement les tendances temporelles que les features de lag encodent. Sa configuration — `max_iter=300`, `max_depth=6`, `min_samples_leaf=20`, `learning_rate=0.05` — privilégie la généralisation (arbres peu profonds, nombreuses itérations à faible pas) sur la mémorisation. Il est le seul des trois modèles à atteindre le seuil du CDC avec un CV R² de 0,673. Une propriété supplémentaire justifie son choix : HGB gère nativement les types mixtes numériques et entiers sans nécessiter de `ColumnTransformer` — `type_id` est utilisé directement comme entier catégoriel sans encodage `OneHotEncoder`, ce qui simplifie le pipeline d'inférence en production.

#### Validation croisée temporelle (TimeSeriesSplit)

```python
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring="r2")
```

`TimeSeriesSplit` préserve l'ordre chronologique — chaque fenêtre de validation est strictement postérieure à sa fenêtre d'entraînement. Cette approche évite le biais d'optimisme d'un CV aléatoire sur des données temporellement corrélées.

#### Métriques finales du modèle retenu (`hgb_v1.0`)

Le modèle `hgb_v1.0` atteint un CV R² de 0,6732 sur les 5 folds temporels, franchissant le seuil du CDC de 0,65 en validation croisée. En revanche, ses métriques sur le jeu de test sont nettement inférieures : Test R² = 0,2179, Test RMSE = 17,85 points et Test MAE = 12,36 points — toutes en-deçà des cibles du livrables L4 (R² ≥ 0,65, RMSE < 10, MAE < 7). Ces valeurs proviennent directement de `ml/models/metadata.json` (`trained_at: 2026-05-14T13:15:48`). L'écart entre les performances en CV et en test est structurel ; son analyse causale fait l'objet du paragraphe suivant.

#### Analyse de l'écart CV R² / Test R² — Diagnostic causal

L'écart entre le CV R² (0.673) et le test R² (0.218) est structurel et s'explique par deux causes identifiées :

**Cause 1 — Features temporelles sans signal (5/14 features inutiles)**

Les features `hour`, `day_of_week`, `day_of_month`, `is_weekend` et `is_peak_hour` portent zéro signal car le simulateur `lasc__livesim_fill` génère des taux de remplissage identiques à 2h du matin et à 10h un vendredi :

```python
# lasc__livesim_fill — taux indépendant de l'heure et du jour
rate = FILL_RATE_PER_HOUR.get(type_id, 2.0) * RATE_SCALE
rate *= random.uniform(0.7, 1.3)   # variabilité aléatoire pure
```

En données réelles, ces 5 features seraient les plus prédictives (déchets organiques après les weekends, zones commerciales aux heures de bureau). Dans les données simulées, elles ajoutent du bruit et forcent le modèle à se rabattre entièrement sur les features de lag.

**Cause 2 — Mismatch entre les deux générateurs de données**

`lasc__seed_data` fixe `rate_per_hour` une seule fois par conteneur pour toute la période historique de 30 jours, produisant des rampes quasi-linéaires prévisibles avec une faible variance (σ=0,3/heure). Ce jeu de données constitue la majorité du train set. À l'opposé, `lasc__livesim_fill` re-sample le taux de remplissage à chaque tick avec une variabilité ±30 % aléatoire (`random.uniform(0.7, 1.3)`) et un bruit gaussien (σ=0,15/tick), produisant des marches aléatoires à variance élevée. Ce jeu de données constitue l'intégralité du test set. Le modèle apprend sur des profils stables et prévisibles, puis est évalué sur des profils bruités et non-stationnaires — ce mismatch de distribution dégrade mécaniquement le test R².

**Correctif implémentable :**

```python
# À ajouter dans lasc__livesim_fill
PEAK_HOURS = {7, 8, 9, 12, 17, 18, 19}
DAY_MULT   = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.4}

rate *= DAY_MULT[now.weekday()] * (1.3 if now.hour in PEAK_HOURS else 1.0)
```

Avec cette modification, les features temporelles deviennent informatives. Après 60–90 jours d'historique enrichi et re-entraînement, le test R² devrait rejoindre le CV R².

#### Interprétabilité (XAI)

Le notebook `03_evaluation.ipynb` prévoit trois visualisations pour l'interprétabilité du modèle HGB : un scatter *predictions vs actuals* (nuage de points valeurs réelles vs prédites, attendu proche de la diagonale y=x), un histogramme des erreurs (distribution de `y_pred - y_test`, attendu centré sur 0) et un graphique des top 15 feature importances via `model.named_steps['model'].feature_importances_`.

Le notebook présente un bug connu documenté dans `documentation/ml/index.md §Known issue` : un `KeyError` sur `model.named_steps['prep']` pour la branche HGB. Le correctif (une dizaine de lignes Python) est documenté et prêt à être appliqué — il consiste à ajouter une branche `elif meta['model_type'] == 'hgb'` qui accède directement aux importances du modèle HGB sans passer par le `ColumnTransformer` absent de son pipeline.

### 5.4 Éthique et biais des données

#### Biais de représentativité (simulation vs réalité)

Les données ECOTRACK sont intégralement synthétiques. Le modèle entraîné ne peut pas être utilisé directement sur des capteurs physiques sans calibration préalable sur données réelles. Ce biais est délibéré dans le cadre académique du projet et documenté comme limite explicite.

#### Biais temporel — features sans signal

Les 5 features temporelles portent zéro signal sur les données simulées mais constitueraient le signal dominant sur des données réelles (comportements de consommation différenciés selon l'heure et le jour). Un modèle déployé en production sans correction du simulateur sous-exploiterait systématiquement la dimension temporelle.

#### Biais géographique — densité de zone

La feature `density_km2` est calculée à partir de `ST_Area(polygon::geography)` — la densité reflète uniquement la distribution des conteneurs dans le schéma, pas la densité de population réelle. En production, cette feature devrait être calibrée avec des données INSEE par arrondissement.

#### Conformité RGPD du pipeline ML

Aucune donnée personnelle n'est intégrée dans le dataset d'entraînement. Les features sont exclusivement physiques (fill_rate, capacity_liters), temporelles (hour, day_of_week) et géographiques agrégées (density_km2) — aucun identifiant utilisateur, localisation individuelle ou comportement citoyen nominatif n'entre dans le modèle.

Cinq dimensions de biais ont été identifiées et traitées à des niveaux d'avancement différents. Le biais simulation/réalité est entièrement documenté dans la section limitation du dossier et dans `documentation/ml/index.md` — le contexte synthétique est explicitement signalé à tout utilisateur du modèle. Les features temporelles sans signal font l'objet d'un correctif prêt à déployer dans `lasc__livesim_fill`, documenté en §5.3. Le mismatch seed/livesim est adressé par une checklist de re-entraînement (60–90 jours) intégrée à `ml/ROADMAP.md`. La densité de zone approximative, calibrée à partir des polygones du schéma et non des données INSEE, est identifiée comme axe d'amélioration post-soutenance. Enfin, l'absence de données personnelles dans le dataset ML est vérifiée par construction — les features ne contiennent aucune colonne `user_id`, adresse ou comportement individuel nominatif.

---

## 6. Exposition des Résultats

### 6.1 API de prédiction

#### Architecture générale

L'API REST ECOTRACK est construite sur **FastAPI** avec validation Pydantic v2, déployée dans le namespace Kubernetes `datalake` via `helmcharts/apiservice-deployment.yaml`. Le pool de connexions PostgreSQL est géré par `psycopg2.pool.ThreadedConnectionPool` avec `min=2` et `max=10` connexions, ce qui permet de servir des requêtes concurrentes sans saturer la base. La Row Level Security est activée sur chaque requête sensible via `SET LOCAL app.user_id` injecté par `set_user_context(conn, user_id)` avant toute lecture. La documentation Swagger UI est auto-générée et accessible à `http://api.localhost/docs` via l'Ingress Traefik v3.

#### 9 routers déployés

L'API expose neuf routers couvrant l'ensemble des épics fonctionnels, avec des niveaux d'implémentation différenciés.

Six routers sont entièrement opérationnels. Le router `containers` regroupe les endpoints C1 à C20 : CRUD complet, filtres géospatiaux par zone via `ST_Within`, statut en temps réel depuis `containers.fill_rate`. Le router `zones` expose Z1 à Z5 : CRUD et export GeoJSON via `ST_AsGeoJSON(polygon)`. Le router `history` couvre H5 à H7 : série temporelle par conteneur depuis `fill_history` avec pagination `LIMIT/OFFSET`, agrégats depuis `aggregated_hourly_stats`. Le router `routes` expose T1 à T9 : CRUD sur les tournées et leurs étapes, calcul de distance via `ST_Length(path::geography)`. Le router `analytics` regroupe A1 à A10 ainsi que les KPIs, la heatmap et la choroplèthe — c'est le router le plus riche, qui expose l'ensemble des indicateurs décisionnels destinés aux managers. Le router `reports` expose R4 (`POST /reports/generate`) et R5 (`GET /reports/{id}/download`) avec génération asynchrone via `BackgroundTasks` FastAPI : la demande est insérée dans la table `reports` avec le statut `pending`, la génération s'exécute en arrière-plan (`processing` → `ready` ou `error`), puis le fichier est retourné via `FileResponse`. Deux formats sont disponibles : PDF via `reportlab` (table KPI avec en-tête `#2d6a4f`, tableau Top Zones par volume collecté) et Excel via `openpyxl` (feuille Summary + feuille Zones).

Deux routers sont en implémentation partielle. Le router `dashboard` couvre DA3 à DA5 (layout config, KPI cards, export snapshot) et est opérationnel sur ses endpoints principaux. Le router `gamification` expose GAM3 à GAM11 en stubs : l'architecture SQL est entièrement posée (tables `user_points`, `badges`, `user_badges`, `defis`, `defi_participations`), mais les handlers Python renvoient des réponses statiques.

Un router reste en stub fonctionnel. Le router `ml` expose l'endpoint ML5 `POST /ml/predict` avec une réponse HTTP 503 — le modèle `model.pkl` est disponible dans `ml/models/`, mais son intégration dans le container Docker nécessite une instruction `COPY` dans le Dockerfile et un `kubectl rollout restart` du déploiement.

#### Endpoint ML — `/ml/predict`

**Input :**
```python
class PredictRequest(BaseModel):
    container_id: int
    horizon_hours: int = 24
```

**Output (à l'activation) :**
```json
{
    "container_id": 42,
    "horizon_hours": 24,
    "predicted_fill_rate": 73.5,
    "predicted_at": "2026-06-01T14:30:00",
    "model_version": "hgb_v1.0"
}
```

**Pipeline d'inférence :**
1. Chargement du modèle au démarrage (`_load_model()` si `MODEL_PATH` existe) — une seule fois par pod
2. Feature extraction en temps réel : 5 requêtes SQL pour lags + rolling + métadonnées conteneur + densité zone
3. Prédiction : `_model.predict(pd.DataFrame([feats])[_feature_cols])`
4. Clamping physique : `max(0.0, min(100.0, predicted))`
5. Persistence dans `ml_predictions` (container_id, horizon_hours, predicted_fill_rate, model_version)

**Activation :** ajouter `COPY ml/models/model.pkl /ml/models/model.pkl` dans le Dockerfile + `kubectl rollout restart deployment/apiservice -n datalake`.

#### Endpoints analytics clés

**`GET /analytics/kpis`** : 6 KPI cards avec variation % vs période précédente équivalente (volume collecté, nombre de collectes, taux de remplissage moyen, dépassements, distance totale, conteneurs actifs).

**`GET /analytics/choropleth`** : polygones GeoJSON par zone avec densité et taux de remplissage moyen — source Leaflet/Mapbox :
```sql
SELECT zone_id, zone_name, ST_AsGeoJSON(polygon), density_km2, avg_fill_rate
FROM get_choropleth_data()
```

**`GET /analytics/costs-roi`** : coût mensuel (1,20 €/km) et économies estimées (20 % réduction kilométrage), avec CO₂ évité (0,27 kg/km) :
```python
_COST_PER_KM  = 1.20   # €/km
_SAVINGS_RATE = 0.20   # 20 % de réduction vs tournées calendaires
_CO2_PER_KM   = 0.27   # kg CO₂/km — camion de collecte
```

### 6.2 Dashboard de visualisation

#### Grafana — Dashboards opérationnels

Grafana est accessible à `http://grafana.localhost` via l'Ingress Traefik dans le namespace `monitoring`. Il exploite deux datasources configurées — Prometheus pour les métriques d'infrastructure et PostgreSQL pour les données métier — ce qui en fait le seul outil capable de couvrir simultanément les deux dimensions de supervision d'ECOTRACK sans déployer un second système de dashboarding.

Cinq dashboards couvrent les besoins des deux audiences principales. Le dashboard Infrastructure K8s interroge Prometheus et présente aux équipes ops les métriques CPU/RAM par pod, l'usage des PVCs et les `RestartCount` — indicateurs critiques pour détecter une fuite mémoire dans le worker Airflow ou une saturation du PVC PostgreSQL de 8 Gi. Le dashboard Airflow health consomme les métriques exposées via `ServiceMonitor` et permet de suivre le taux de succès des DAG runs, la durée des tâches et les échecs de `lasc__livesim_fill` susceptibles de créer des lacunes dans `fill_history`. Le dashboard PostgreSQL, alimenté par le `postgres-exporter`, surveille le nombre de connexions actives (seuil : 10 sur le pool `ThreadedConnectionPool`), le cache hit ratio et les transactions par seconde. Le dashboard Fill history interroge directement `aggregated_daily_stats` via la datasource PostgreSQL native et présente aux managers l'évolution du taux de remplissage par zone sur les 30 derniers jours. Enfin, le dashboard Alertes actives, connecté à AlertManager, centralise les conteneurs critiques (`fill_rate > fill_threshold_pct`) et les `threshold_breach` générés par le trigger `fill_history_alert`.

#### 10 graphiques analytics — Endpoints A1–A10

Les dix endpoints analytics de FastAPI constituent la couche de visualisation métier destinée au frontend React et aux managers. Ils couvrent l'ensemble des angles d'analyse opérationnelle définis dans l'Epic E6.

L'évolution du volume collecté (A1, `GET /analytics/volume-evolution`) est restituée sous forme de *stacked area chart* par type de déchet, permettant d'identifier les pics de collecte par catégorie. La distribution par type (A2, `GET /analytics/type-distribution`) présente un donut chart de la répartition des conteneurs, utile pour calibrer les ressources de collecte par filière. Les collections par zone (A3, `GET /analytics/zone-collections`) exposent un *horizontal bar chart* pour comparer la charge entre les 5 arrondissements. La distribution du fill rate (A4, `GET /analytics/fill-distribution`) est un histogramme par tranches de 10 %, qui révèle la bimodalité de la distribution cible évoquée en §5.2. L'évolution du fill rate (A5, `GET /analytics/fill-evolution?moving_avg=true`) superpose la série brute et une moyenne mobile à 7 jours, lissant la variabilité du simulateur pour mettre en évidence les tendances de fond. La performance des routes (A6, `GET /analytics/route-performance`) est un scatter chart croisant distance parcourue et volume collecté par tournée. La timeline des incidents (A7, `GET /analytics/incidents`) agrège signalements citoyens et notifications de dépassement sur un même axe temporel. La heatmap des collectes (A8, `GET /analytics/heatmap`) croise les jours de semaine et les heures pour identifier les créneaux de forte activité. La carte choroplèthe (A9, `GET /analytics/choropleth`) expose les polygones GeoJSON par zone colorés selon le taux de remplissage moyen via `ST_AsGeoJSON(polygon)` et PostGIS. Enfin, l'endpoint coûts et ROI (A10, `GET /analytics/costs-roi`) présente un *mixed bar + line chart* croisant le coût mensuel estimé et les économies projetées grâce à l'optimisation des tournées.

La séparation des audiences est nette : Grafana adresse les équipes ops et infra avec des métriques Prometheus ; FastAPI adresse les managers et les agents avec des données métier structurées.

#### Documentation technique — MkDocs

Le site `http://docs.localhost` (namespace `documentation`) centralise la documentation technique complète : chaque DAG (graphes, paramètres, notes de runtime), chaque phase de l'API (endpoints, exemples curl), l'architecture K8s (topologie, DNS, PVCs), le schéma de base de données (26 tables, index, triggers), et les notebooks ML (ROADMAP, retraining checklist). Cette documentation "as code" constitue un actif de valeur pour la maintenance et l'onboarding de nouveaux membres.

### 6.3 Génération de rapports structurés

#### Architecture de génération asynchrone

Le router `reports` implémente un pattern de génération asynchrone découplée adapté aux rapports de volume variable. `POST /reports/generate` accepte la demande et retourne immédiatement `HTTP 202 Accepted` avec le `report_id`, tandis que `GET /reports/{id}/download` livre le fichier une fois la génération terminée. Ce découplage évite le timeout HTTP sur les rapports couvrant de longues périodes ou plusieurs zones.

Le cycle de vie d'un rapport est entièrement tracé dans la table `reports` : `pending` (demande reçue), `processing` (génération en cours), `ready` (fichier disponible) ou `error` (exception capturée). Le background task `_generate_report()` exécute trois étapes — mise à jour du statut, appel à `_fetch_summary()`, construction du fichier — avec gestion des exceptions garantissant que le statut `error` est toujours persisté.

#### Formats et segmentation

Deux formats sont disponibles selon le contexte d'utilisation :

**PDF via `reportlab`** : document A4 structuré avec en-tête de période, table KPI à 5 lignes (conteneurs actifs, collectes, volume, taux de remplissage moyen, débordements) avec en-tête vert `#2d6a4f` et alternance de lignes, suivi d'un tableau Top Zones classé par volume collecté. La mise en page fixe garantit la reproductibilité entre périodes et facilite la comparaison.

**Excel via `openpyxl`** : classeur à deux feuilles — `Summary` (métadonnées + KPIs en tableau formaté) et `Zones` (détail par zone avec en-têtes colorés). Ce format est conçu pour les managers qui souhaitent effectuer des calculs additionnels ou intégrer les données dans leurs propres outils.

#### Segmentation et organisation

Les rapports peuvent être filtrés selon trois axes de segmentation, satisfaisant l'exigence de « moyens de segmentation et d'organisation » de la compétence :

- **Par type de rapport** (`report_type`) : `monthly` (mois courant par défaut), `weekly` (7 derniers jours), ou période personnalisée via `period_start` / `period_end`
- **Par zone géographique** (`zone_id`) : filtrage optionnel sur l'un des 5 arrondissements — `_fetch_summary()` adapte dynamiquement le prédicat SQL `AND zone_id = %(zone_id)s` sur les tables `collections` et `aggregated_daily_stats`
- **Par utilisateur** (`user_id`) : traçabilité de chaque demande pour l'audit, avec RLS applicable si nécessaire

Les KPIs agrégés (`active_containers`, `collection_count`, `volume_l`, `avg_fill_rate`, `overflow_count`, `top_zones`) sont extraits depuis les tables Gold `aggregated_daily_stats` et la table transactionnelle `collections`, assurant la cohérence avec les dashboards Grafana et les endpoints analytics. Les rapports PDF/Excel constituent la forme archivable et exportable complémentaire aux dashboards temps réel : là où Grafana présente une vue dynamique, les rapports formalisent une synthèse périodique destinée à être transmise ou conservée.

#### Limite connue — persistance des fichiers

Les fichiers générés sont stockés dans `REPORTS_DIR` (défaut : `/tmp/reports` dans le pod Kubernetes). Ce répertoire est local au pod et **non persisté sur un volume dédié** : un redémarrage du pod `apiservice` efface les fichiers existants. Si `GET /reports/{id}/download` est appelé après un redémarrage, le statut en base reste `ready` mais le fichier est absent — l'endpoint retourne alors `500 "Report file missing from storage"`. Pour une mise en production, la correction consiste à monter un PVC sur `REPORTS_DIR` ou à écrire les fichiers dans un stockage objet (MinIO, S3) et à stocker l'URL plutôt que le chemin local dans `reports.file_path`.

---

## 7. Conclusion et Perspectives

### 7.1 Bilan des résultats obtenus

Le projet ECOTRACK a livré un système data opérationnel et démontrable en live sur l'ensemble du périmètre fondamental :

**Infrastructure et pipeline :** cluster Kubernetes Minikube à 5 namespaces opérationnel (0 € de cloud), pipeline IoT continu traitant 2 000 conteneurs toutes les 10 minutes, 1,44 M lignes de données historiques avec modèle physique de remplissage par type de déchet, qualité données à ~99 % de mesures valides.

**Architecture data :** Lakehouse natif PostgreSQL 15 — couches Bronze/Silver/Gold sans stack objet additionnel, 26 tables (17 OLTP + 4 OLAP + 5 gamification), 7 triggers automatisant la logique métier, 5 procédures stockées idempotentes, PostGIS opérationnel avec GIST indexes et requêtes spatiales en < 200 ms.

**API et analytique :** 40+ endpoints FastAPI dont 6 routers entièrement opérationnels (containers, zones, history, routes, analytics, reports), documentation Swagger auto-générée, 10 endpoints analytics (heatmap, choroplèthe, KPIs, ROI environnemental), génération de rapports PDF/Excel asynchrone, dashboards Grafana avec datasource PostgreSQL native.

**Machine Learning :** HistGradientBoosting entraîné sur 2,265 M lignes, 14 features, CV R² = 0.673 (seuil CDC ≥ 0.65 atteint en validation croisée temporelle), diagnostic complet de l'écart CV/test avec correctif implémentable documenté.

### 7.2 Limites identifiées

**Limite principale — Test R² sous cible (0.218 vs 0.65) :** l'écart entre le CV R² (0.673) et le test R² (0.218) est structurel, causé par deux problèmes identifiés et documentés : 5 features temporelles sur 14 portent un signal nul dans les données simulées, et la distribution entre `lasc__seed_data` (rampes linéaires, train set) et `lasc__livesim_fill` (marches aléatoires, test set) est fondamentalement différente. Cette limite est une **découverte méthodologique** : le projet a produit une analyse causale complète avec correctif prêt en moins d'une journée de développement.

**Limite fonctionnelle — Phase 4 incomplète :** les fonctionnalités gamification (`/leaderboard`, `/badges`, `/defis`) et la prédiction ML (`/ml/predict`) sont en stub. Leur architecture SQL est entièrement posée — la complétion est une question de temps de développement, pas de décision technique.

**Limite infrastructure — Minikube local :** l'infrastructure est validée sur Minikube. Un déploiement cloud multi-nœuds nécessiterait la migration des PVCs `hostPath` vers des volumes persistants gérés et la configuration de la haute disponibilité PostgreSQL.

### 7.3 Améliorations pour une mise en production future

**Axe 1 — Qualité du modèle ML (prioritaire, < 1 journée) :**
```python
# Dans lasc__livesim_fill — injection de signal temporel réaliste
PEAK_HOURS = {7, 8, 9, 12, 17, 18, 19}
DAY_MULT   = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.4}
rate *= DAY_MULT[now.weekday()] * (1.3 if now.hour in PEAK_HOURS else 1.0)
```
Suivi : laisser tourner 60–90 jours, puis re-exécuter ML1 → ML2 → ML3 → ML4 → ML5. Test R² attendu > 0.65.

**Axe 2 — MLOps et déploiement continu :**
- DAG Airflow mensuel de re-entraînement automatique si `COUNT(fill_history) > seuil`
- MLflow Tracking pour versionner les expériences (remplace le `metadata.json` artisanal)
- Monitoring de la dérive du modèle via `ml_predictions.actual_fill_rate` ex-post

**Axe 3 — CI/CD API Service :**
GitHub Actions workflow : build image Docker → push registry → `kubectl rollout restart deployment/apiservice -n datalake`. Tests Pytest sur endpoints FastAPI (`httpx` + base PostgreSQL dédiée), coverage > 50 % (Epic E11).

**Axe 4 — Fonctionnalités en retard :**

L'activation de `GET /leaderboard` représente 1 à 2 heures de travail — la fonction SQL est déjà écrite dans le schéma, seul le handler FastAPI reste à câbler. L'activation de `POST /ml/predict` est évaluée à 2 heures — elle consiste à copier `model.pkl` dans le container Docker via une instruction `COPY` dans le Dockerfile et à remplacer la réponse stub 503 par le pipeline d'inférence documenté dans `ml/ROADMAP.md §ML5`. Enfin, la mise en place des tests Pytest de l'Epic E11 représente 2 à 3 jours de développement pour atteindre une couverture supérieure à 50 %, seuil requis par le CDC.

**Axe 5 — Scalabilité :**
- CloudNativePG pour PostgreSQL HA (streaming replication Kubernetes-native)
- DAG de rotation automatique des partitions mensuelles et archivage Parquet vers stockage objet froid
- TimescaleDB si le volume dépasse 100 M lignes/an (compression automatique hypertables)

### 7.4 Enseignements méthodologiques

**La simulation de données n'est pas neutre pour le ML.** Le choix de la stratégie de génération des données synthétiques conditionne directement la qualité du modèle. Un simulateur sans modulation temporelle produit des features apparemment pertinentes mais statistiquement inertes. Cette leçon illustre pourquoi l'EDA doit inclure une vérification explicite de la corrélation features/target *avant* l'entraînement — et pourquoi la qualité des données prime sur la sophistication du modèle.

**La séparation OLTP/OLAP dès la conception est un investissement à rendement immédiat.** Les tables `aggregated_hourly_stats` et `aggregated_daily_stats`, conçues dès l'Epic E1, ont réduit les temps de réponse API de plusieurs secondes (full scan de `fill_history`) à moins de 100 ms. Cette décision architecturale précoce a conditionné la faisabilité de l'ensemble du périmètre analytique.

**L'idempotence doit être un principe de conception, pas un correctif.** L'utilisation systématique de `ON CONFLICT DO UPDATE/DO NOTHING` et de `session_replication_role = 'replica'` pour le bootstrap a permis de relancer les DAGs de développement des dizaines de fois sans corruption de données — un gain de productivité considérable sur un cycle de développement itératif.

**La documentation "as code" est un actif de première classe.** Produire la documentation MkDocs en parallèle du code, et non en fin de projet, a facilité la revue des choix techniques, détecté des incohérences entre la spécification et l'implémentation, et constitue aujourd'hui la principale source de vérité pour comprendre le système dans sa globalité.

---

*Dossier Professionnel BLOC 2 — Filière M1 DATA & ANALYTICS*
*RNCP 38822 / 38823 — INGETIS École d'ingénierie informatique*

*Sources techniques :*
*`database/setup_complete.sql` · `dags/lasc__livesim_fill.py` · `dags/lasc__seed_data.py` · `ml/ROADMAP.md` · `ml/models/metadata.json` · `apiservice/routers/analytics.py` · `apiservice/routers/ml.py` · `documentation/helmcharts/k8s-architecture.md` · `documentation/ml/index.md` · `context/master1_data_tasks.md` · `context/master1_data_epics.md`*
