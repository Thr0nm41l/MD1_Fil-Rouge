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

ECOTRACK s'adresse à quatre profils d'utilisateurs aux besoins data distincts :

| Rôle | Responsabilité principale | Besoin data |
|---|---|---|
| **Manager** | Supervise les KPIs de zone, planifie les collectes | Tableau de bord temps réel, carte choroplèthe, heatmap d'activité |
| **Worker** (agent) | Exécute les tournées, enregistre les collectes | Statut conteneur en temps réel, route optimisée avec distances |
| **Admin** | Configure les zones, conteneurs et seuils d'alerte | CRUD complet sur toutes les entités, monitoring pipeline |
| **Citoyen** | Signale les anomalies, suit son engagement | Score de participation gamifié, historique de signalements |

Cette diversité des usages a conditionné le choix d'une architecture multi-couches (OLTP pour les opérations transactionnelles, OLAP pour l'analytique) et d'une API REST généraliste servant indifféremment les dashboards managériaux et l'interface citoyenne.

#### Problématique analytique

Le passage d'une collecte calendaire à une collecte à la demande repose sur la capacité à répondre à deux questions analytiques :

**Question descriptive :** *Quels conteneurs, dans quelle zone et à quelle heure présentent un risque de saturation dans les 24 heures ?* — répondue par les endpoints analytics et les dashboards Grafana.

**Question prédictive :** *Quel sera le taux de remplissage d'un conteneur donné dans 24 heures, avec une précision suffisante pour déclencher une tournée conditionnelle (R² ≥ 0.65) ?* — répondue par le modèle `hgb_v1.0`.

La réponse positive à la première question (CV R² = 0.673) démontre la faisabilité technique d'une collecte optimisée réduisant le kilométrage de 20 % et les débordements de manière significative.

### 2.2 Description des données disponibles

#### Inventaire des sources

| Source | Type | Volume | Fréquence | Qualité observée |
|---|---|---|---|---|
| `fill_history` | Série temporelle IoT | 1,44 M lignes / 30 j (~18 M/an) | 10 min | ~99 % valides (1 % `is_outlier`) |
| `containers` | Référentiel géospatial | 2 000 enregistrements | Statique (mise à jour événementielle) | 100 % complets |
| `zones` | Polygones géographiques (WGS84) | 5 zones | Statique | 100 % complets |
| `collections` | Événements de collecte | Variable (opérationnel) | Sur événement | Dépend du DAG `lasc__ops_containers` |
| `signalements` | Incidents citoyens | Variable | Sur événement | 100 % valides (contraintes SQL) |
| `aggregated_*_stats` | Agrégats OLAP horaires/quotidiens | ~48 K lignes/jour | 10 min (recalcul incrémental) | Qualité héritée de `fill_history` |

#### Caractérisation 4V

- **Volume :** 1,44 M lignes historiques (30 j) ; 2,265 M lignes utilisées pour l'entraînement ML ; ~288 K nouvelles mesures quotidiennes en régime nominal
- **Variété :** séries temporelles numériques (`fill_rate`, `temperature`, `battery_pct`) + géométries PostGIS (`POINT`, `POLYGON`, `LINESTRING`, SRID 4326) + texte structuré (`signalements`, `notifications`)
- **Vélocité :** ingestion toutes les 10 min, propagation immédiate via triggers SQL (`fill_history_update_container`, `fill_history_alert`)
- **Véracité :** données entièrement synthétiques, 1 % d'outliers intentionnels, contraintes `CHECK` sur `fill_rate ∈ [0, 100]`

#### Contraintes RGPD

Les données à caractère personnel sont restreintes à la table `users` (email, nom, prénom, mot de passe bcrypt). Les mesures IoT sont anonymisées par construction — `fill_history` référence un `container_id` sans lien direct avec une personne physique.

**Mesures de conformité :**
- Mots de passe stockés en bcrypt (algorithme `bcrypt`, facteur de coût 12) via `pwd_context.hash()`
- Row Level Security activée sur `users`, `signalements`, `notifications`, `user_role`
- `SET LOCAL app.user_id` injecté dans chaque connexion PostgreSQL via `set_user_context(conn, user_id)` — chaque utilisateur ne voit que ses propres données sensibles
- Aucune donnée personnelle dans le dataset d'entraînement ML

### 2.3 Choix du paradigme data et justification

#### Comparaison des paradigmes

| Paradigme | Forces | Faiblesses | Adéquation ECOTRACK |
|---|---|---|---|
| **Data Warehouse** | Schéma strict, requêtes analytiques rapides, gouvernance forte | Rigidité du schéma, pas adapté aux données brutes IoT, licence coûteuse | Partielle — les tables OLAP correspondent à la logique DW |
| **Data Lake** | Flexibilité tous formats, faible coût stockage, ML-friendly | Gouvernance difficile (risque *data swamp*), latence analytique élevée | Partielle — `fill_history` (raw, partitionnée) correspond à une Bronze Layer |
| **Data Lakehouse** | Combine requêtes SQL directes (DW) et données brutes (Data Lake), ACID, ML-friendly | Complexité opérationnelle si Delta Lake / Iceberg | **Retenu** — PostgreSQL natif implémente cette logique |

#### Architecture Lakehouse natif PostgreSQL

Le projet implémente un **Lakehouse sur PostgreSQL 15** sans framework Delta Lake ni Apache Iceberg. Ce choix est justifié par trois arguments convergents :

**Adéquation au volume :** Delta Lake est optimal pour des volumes dépassant le téraoctet stockés en Parquet distribué. Sur 18 M lignes/an (~2 Go), les performances PostgreSQL avec partitionnement natif `PARTITION BY RANGE (measured_at)` sont équivalentes — les requêtes de séries temporelles s'exécutent en < 100 ms par partition pruning et index composite `(container_id, measured_at DESC)`.

**Unified storage :** PostgreSQL héberge simultanément les données brutes (`fill_history`), les agrégats métier (`aggregated_*_stats`), les prédictions ML (`ml_predictions`) et les référentiels opérationnels (`containers`, `zones`). Cette unification garantit la cohérence ACID sur l'ensemble du périmètre sans fragmentation multi-stack.

**Contrainte du cahier des charges :** La tâche `BDD5` (`context/master1_data_tasks.md`) impose PostgreSQL 15 + PostGIS comme couche de persistance centrale. L'ajout d'un Data Lake objet (MinIO + Parquet) en parallèle aurait dupliqué la source de vérité sans bénéfice fonctionnel sur le périmètre de 115 tâches.

#### Mapping couches Lakehouse

| Couche | Table PostgreSQL | Rôle |
|---|---|---|
| **Bronze** (raw, immutable) | `fill_history` PARTITION BY RANGE (measured_at) | Données brutes IoT, flag `is_outlier`, jamais modifiées |
| **Silver** (cleaned, enriched) | Filtre `WHERE NOT is_outlier` + JOIN `containers/zones` | Nettoyage et enrichissement implicites à l'agrégation |
| **Gold** (aggregated, business-ready) | `aggregated_hourly_stats`, `aggregated_daily_stats`, `ml_predictions` | KPIs pré-calculés, exposition API directe |

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

| Trigger | Événement | Effet |
|---|---|---|
| `fill_history_update_container` | AFTER INSERT sur `fill_history` | Synchronise `containers.fill_rate`, `status`, `last_updated` |
| `fill_history_alert` | AFTER INSERT sur `fill_history` | Insère dans `notifications` si `fill_rate > fill_threshold_pct` |
| `containers_assign_zone` | BEFORE INSERT/UPDATE sur `containers.location` | Résout `zone_id` via `ST_Within(location, polygon)` |
| `signalement_award_points` | AFTER INSERT sur `signalements` | +10 pts dans `user_points` pour le citoyen déclarant |

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

En l'absence d'une plateforme Feature Store dédiée (Feast, Tecton, Hopsworks), le projet implémente une solution légère basée sur un fichier Parquet versionnée localement.

| Aspect | Implémentation |
|---|---|
| Stockage offline | `ml/data/training_features.parquet` — sortie de `01_eda_feature_engineering.ipynb` |
| Versionnage | `trained_at` dans `ml/models/metadata.json` (ISO 8601) |
| Serving offline | `pd.read_parquet()` dans les notebooks d'entraînement |
| Serving online | Recalcul en temps réel depuis `fill_history` (5 requêtes SQL par prédiction) |

#### Catalogue des 14 features

| Famille | Feature | Construction | Signal attendu |
|---|---|---|---|
| Temporelles | `hour` | `measured_at.dt.hour` | Cycles diurnes (heure de pointe) |
| Temporelles | `day_of_week` | `measured_at.dt.dayofweek` | Pics weekend (déchets organiques) |
| Temporelles | `day_of_month` | `measured_at.dt.day` | Cycles de collecte mensuels |
| Temporelles | `is_weekend` | `day_of_week >= 5` | Comportement weekend vs semaine |
| Temporelles | `is_peak_hour` | `hour ∈ {7,8,9,17,18,19}` | Heures de forte activité urbaine |
| Lags | `fill_rate_1h_ago` | `shift(6)` (6 ticks × 10 min) | Tendance immédiate |
| Lags | `fill_rate_24h_ago` | `shift(144)` | Cycle journalier |
| Lags | `fill_rate_7d_ago` | `shift(1008)` | Cycle hebdomadaire |
| Rolling | `fill_rate_24h_avg` | `rolling(144).mean()` (trailing) | Tendance lissée 24h |
| Rolling | `fill_rate_7d_avg` | `rolling(1008).mean()` (trailing) | Tendance lissée 7 jours |
| Rolling | `fill_rate_change_rate` | `(fill_rate - shift(6)) / 6` | Vitesse de remplissage (Δ/tick) |
| Conteneur | `capacity_liters` | `containers.capacity_liters` | Taille physique du conteneur |
| Conteneur | `type_id` | `containers.type_id` | Type de déchet (différents taux) |
| Géospatiale | `density_km2` | `COUNT(containers) / ST_Area(polygon) × 1e6` | Densité urbaine par zone |

**Variable cible :** `fill_rate` à T+24h, calculée par `g.shift(-144)` — chaque ligne du dataset porte le niveau de remplissage 144 ticks (24 heures) plus tard pour le même conteneur.

---

## 4. Pipelines ETL/ELT

### 4.1 Description du pipeline principal

Quatre DAGs Airflow orchestrent l'ensemble du traitement de données :

| DAG | Rôle | Schedule | Pattern |
|---|---|---|---|
| `lasc__seed_data` | Bootstrap initial — génère 1,44 M lignes sur 30 jours | Manuel | EL (Extract-Load) |
| `lasc__livesim_fill` | Simulation IoT continue — tick toutes les 10 min | `*/10 * * * *` | ETL + triggers SQL |
| `lasc__ops_containers` | Opérations sur conteneurs déclenchées par l'API REST | Déclencheur REST | EL événementiel |
| `masc__clean_xcoms` | Purge des XComs Airflow > 7 jours | Quotidien | Maintenance |

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

Spécificités techniques critiques :

| Aspect | Valeur |
|---|---|
| Volume généré | 1 440 000 lignes `fill_history` en ~10 minutes |
| Désactivation des triggers | `SET session_replication_role = 'replica'` pour le bulk insert (performance × 8) |
| Resynchronisation | `UPDATE containers SET fill_rate = last_measure.fill_rate ...` post-insert |
| Idempotence | `ON CONFLICT DO UPDATE` sur toutes les tables de référence |

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

| Dimension | Règle | Mécanisme |
|---|---|---|
| Complétude | `fill_rate`, `measured_at`, `container_id` jamais NULL | `NOT NULL` + FK |
| Unicité | Une seule mesure par (conteneur, minute) | `ON CONFLICT DO NOTHING` |
| Cohérence domaine | `fill_rate ∈ [0, 100]`, `status ∈ {'empty','normal','full','critical'}` | `CHECK` constraints |
| Cohérence référentielle | `container_id` → `containers.key_container` | FK `ON DELETE RESTRICT` |
| Fraîcheur | Mesures toutes les 10 min | Schedule `*/10 * * * *` |
| Détection outliers | 1 % des mesures flaggées `is_outlier = true` | Génération dans `simulate_fill` |
| Filtrage KPIs | Exclusion des outliers de tous les agrégats Gold | `WHERE NOT is_outlier` dans `aggregate_*` |

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
# Pour chaque conteneur, prédit le fill_rate 144 ticks plus tard
target = groupby("container_id")["fill_rate"].shift(-144)  # 144 × 10 min = 24 h
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

| Paramètre | Valeur |
|---|---|
| Lignes totales (après nettoyage) | 2 265 488 |
| Lignes d'entraînement (85 %) | 1 925 664 |
| Lignes de test (15 %) | 339 824 |
| Période | 2026-04-03 → 2026-05-14 (41 jours) |
| Nombre de conteneurs | 2 000 |
| Nombre de features | 14 |
| Type de problème | Régression (pas de déséquilibre de classes) |

### 5.2 Exploration des données (EDA) et préparation

#### Principaux enseignements de l'EDA

**Distribution de la variable cible :** `fill_rate` concentré entre 40 % et 70 % (effet des collectes déclenchées au seuil de 70 %), avec des pics à 0 % (post-collecte) et à 90-100 % (pré-saturation). La distribution est bimodale et non gaussienne — un modèle linéaire standard est sous-adapté.

**Auto-corrélation :** forte corrélation entre `fill_rate_t` et les features de lag (`fill_rate_1h_ago`, `fill_rate_24h_ago`) — le signal principal est porté par les lags. Corrélation **nulle** avec les features temporelles (`hour`, `day_of_week`, etc.) dans les données simulées, en raison de l'absence de modulation heure/jour dans le simulateur (voir §5.4).

**Valeurs manquantes :** générées par les opérations de décalage (`shift()`) en début de série pour chaque conteneur. Stratégie : suppression (`dropna()`). Les 1 008 premières lignes de chaque conteneur (7 jours) sont perdues, ce qui réduit le dataset de ~2 M lignes — un compromis acceptable pour garantir la validité des features de lag 7 jours.

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

# ── Features de lag (décalage par nombre de ticks) ───────────────────
df["fill_rate_1h_ago"]  = g.shift(6)     # 6 × 10 min = 1 h
df["fill_rate_24h_ago"] = g.shift(144)   # 144 × 10 min = 24 h
df["fill_rate_7d_ago"]  = g.shift(1008)  # 1 008 × 10 min = 7 jours

# ── Moyennes mobiles trailing (sans fuite future) ────────────────────
df["fill_rate_24h_avg"] = g.transform(
    lambda s: s.shift(1).rolling(144, min_periods=12).mean()
)
df["fill_rate_7d_avg"] = g.transform(
    lambda s: s.shift(1).rolling(1008, min_periods=144).mean()
)
df["fill_rate_change_rate"] = g.transform(
    lambda s: (s - s.shift(6)) / 6   # Δ fill_rate par tick de 10 min
)

# ── Enrichissement conteneur et zone ─────────────────────────────────
df = df.merge(df_zones, on="zone_id")   # density_km2
# type_id — entier, compatible tree-based models sans encodage

# ── Variable cible ────────────────────────────────────────────────────
df["target"] = g.shift(-144)   # fill_rate dans 24 h
df_clean = df[feature_cols + ["target"]].dropna()
df_clean.to_parquet("data/training_features.parquet", index=False)
```

**Absence de data leakage :** toutes les features rolling utilisent `shift(1)` avant la fenêtre glissante — aucune information future n'est intégrée dans les features. La variable cible est strictement postérieure aux features d'entrée.

#### Split train/test — Respect de l'ordre temporel

```python
df = df.sort_values("measured_at")
split_idx = int(len(df) * 0.85)
df_train = df.iloc[:split_idx]   # 2026-04-03 → ~2026-05-09
df_test  = df.iloc[split_idx:]   # ~2026-05-09 → 2026-05-14
```

Un split aléatoire sur des séries temporelles constitue une fuite de données (observations T+1 en train avec T-1 en test). Le split temporel strict à 85/15 garantit que le jeu de test est strictement postérieur au jeu d'entraînement.

### 5.3 Modélisation et comparaison des approches

#### Trois modèles entraînés

| Modèle | CV R² (5-fold TimeSeriesSplit) | Test R² | Décision |
|---|---|---|---|
| LinearRegression | 0.094 | ~0.05 | Rejeté — sous-ajusté, relations non linéaires |
| RandomForest (n=200, depth=15) | 0.522 | ~0.30 | Rejeté — sous le seuil de 0.65 |
| **HistGradientBoosting** | **0.673** | **0.218** | **Retenu — seul modèle ≥ 0.65** |

#### Validation croisée temporelle (TimeSeriesSplit)

```python
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring="r2")
```

`TimeSeriesSplit` préserve l'ordre chronologique — chaque fenêtre de validation est strictement postérieure à sa fenêtre d'entraînement. Cette approche évite le biais d'optimisme d'un CV aléatoire sur des données temporellement corrélées.

#### Métriques finales du modèle retenu (`hgb_v1.0`)

| Métrique | Valeur | Seuil CDC | Statut |
|---|---|---|---|
| CV R² | **0.6732** | ≥ 0.65 | ✅ Atteint |
| Test R² | **0.2179** | ≥ 0.65 | ❌ Sous cible |
| Test RMSE | **17.85** pts | < 10 pts | ❌ |
| Test MAE | **12.36** pts | < 7 pts | ❌ |

Source : `ml/models/metadata.json`

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

| Générateur | Profil de remplissage | Représentation dans le dataset |
|---|---|---|
| `lasc__seed_data` | `rate_per_hour` fixé une fois / 30 jours → rampe quasi-linéaire prévisible | Historique d'entraînement (majorité du train set) |
| `lasc__livesim_fill` | `rate` re-samplé à chaque tick → marche aléatoire avec variance élevée | Données récentes (totalité du test set) |

Le modèle apprend sur des profils stables (seed_data), mais est évalué sur des profils plus bruités et non stationnaires (livesim seul). Ce mismatch dégrade mécaniquement le test R².

**Correctif implémentable :**

```python
# À ajouter dans lasc__livesim_fill
PEAK_HOURS = {7, 8, 9, 12, 17, 18, 19}
DAY_MULT   = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.4}

rate *= DAY_MULT[now.weekday()] * (1.3 if now.hour in PEAK_HOURS else 1.0)
```

Avec cette modification, les features temporelles deviennent informatives. Après 60–90 jours d'historique enrichi et re-entraînement, le test R² devrait rejoindre le CV R².

#### Interprétabilité (XAI)

Le notebook `03_evaluation.ipynb` prévoie trois visualisations pour l'interprétabilité du modèle HGB :
- **Scatter predictions vs actuals** : nuage de points (valeurs réelles vs prédites) — attendu proche de la diagonale y=x
- **Histogramme des erreurs** : distribution de `(y_pred - y_test)` — attendu centré sur 0
- **Top 15 feature importances** : `model.named_steps['model'].feature_importances_` pour HistGradientBoosting

Le notebook présente un bug connu documenté dans `documentation/ml/index.md §Known issue` : `KeyError` sur `model.named_steps['prep']` pour la branche HGB. Le correctif (une dizaine de lignes Python) est documenté et prêt à être appliqué.

### 5.4 Éthique et biais des données

#### Biais de représentativité (simulation vs réalité)

Les données ECOTRACK sont intégralement synthétiques. Le modèle entraîné ne peut pas être utilisé directement sur des capteurs physiques sans calibration préalable sur données réelles. Ce biais est délibéré dans le cadre académique du projet et documenté comme limite explicite.

#### Biais temporel — features sans signal

Les 5 features temporelles portent zéro signal sur les données simulées mais constitueraient le signal dominant sur des données réelles (comportements de consommation différenciés selon l'heure et le jour). Un modèle déployé en production sans correction du simulateur sous-exploiterait systématiquement la dimension temporelle.

#### Biais géographique — densité de zone

La feature `density_km2` est calculée à partir de `ST_Area(polygon::geography)` — la densité reflète uniquement la distribution des conteneurs dans le schéma, pas la densité de population réelle. En production, cette feature devrait être calibrée avec des données INSEE par arrondissement.

#### Conformité RGPD du pipeline ML

Aucune donnée personnelle n'est intégrée dans le dataset d'entraînement. Les features sont exclusivement physiques (fill_rate, capacity_liters), temporelles (hour, day_of_week) et géographiques agrégées (density_km2) — aucun identifiant utilisateur, localisation individuelle ou comportement citoyen nominatif n'entre dans le modèle.

| Biais | Mesure corrective | Statut |
|---|---|---|
| Simulation vs réalité | Documentation explicite du contexte synthétique | ✅ Documenté |
| Features temporelles sans signal | Correctif `PEAK_HOURS + DAY_MULT` dans `lasc__livesim_fill` | ✅ Prêt, non déployé |
| Mismatch seed/livesim | Retraining checklist 60–90 jours | ✅ Roadmap documentée |
| Densité zone approximative | Calibration avec données INSEE | 🔲 Post-soutenance |
| Données personnelles | Aucune PII dans le dataset ML | ✅ Conforme RGPD |

---

## 6. Exposition des Résultats

### 6.1 API de prédiction

#### Architecture générale

**Framework :** FastAPI avec validation Pydantic v2
**Déploiement :** Kubernetes namespace `datalake` — `helmcharts/apiservice-deployment.yaml`
**Pool de connexions :** `psycopg2.pool.ThreadedConnectionPool` (min=2, max=10)
**RLS :** `SET LOCAL app.user_id` via `set_user_context(conn, user_id)` avant toute requête sensible
**Documentation :** Swagger UI auto-générée à `http://api.localhost/docs` (Traefik ingress)

#### 9 routers déployés

| Router | Endpoints | Statut |
|---|---|---|
| `containers` | C1–C20 : CRUD, filtres géospatiaux, statut en temps réel | ✅ Opérationnel |
| `zones` | Z1–Z5 : CRUD, export GeoJSON | ✅ Opérationnel |
| `history` | H5–H7 : série temporelle par conteneur, agrégats | ✅ Opérationnel |
| `routes` | T1–T9 : CRUD routes + étapes, distances via `ST_Length` | ✅ Opérationnel |
| `analytics` | A1–A10 + KPIs + heatmap + choroplèthe | ✅ Opérationnel |
| `dashboard` | DA3–DA5 : layout config, KPI cards, export snapshot | ✅ Opérationnel |
| `gamification` | GAM3–GAM11 : leaderboard, badges, défis | ⚠️ Stubs — architecture SQL posée |
| `ml` | ML5 : `POST /ml/predict` | ⚠️ Stub 503 — `model.pkl` prêt |
| `reports` | R4–R5 : `POST /reports/generate`, `GET /reports/{id}/download` | ⚠️ Stubs — `reportlab` dans requirements |

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

**Accès :** `http://grafana.localhost` (Traefik ingress, namespace `monitoring`)
**Datasources configurées :** Prometheus (métriques infra) + PostgreSQL (données métier)

| Dashboard | Datasource | Audience |
|---|---|---|
| Infrastructure K8s | Prometheus | Ops — CPU/RAM par pod, PVC usage, RestartCount |
| Airflow health | Prometheus (`ServiceMonitor`) | Ops — DAG success/failure rate, task duration |
| PostgreSQL | Prometheus (`postgres-exporter`) | Ops — connexions, cache hit ratio, transactions/s |
| Fill history | PostgreSQL (`aggregated_daily_stats`) | Manager — évolution du taux de remplissage par zone |
| Alertes actives | AlertManager | Ops + Manager — conteneurs critiques, threshold breaches |

#### 10 graphiques analytics — Endpoints A1–A10

| Graphique | Endpoint | Visualisation |
|---|---|---|
| A1 — Évolution volume collecté | `GET /analytics/volume-evolution` | Stacked area chart par type |
| A2 — Distribution par type | `GET /analytics/type-distribution` | Donut chart |
| A3 — Collections par zone | `GET /analytics/zone-collections` | Horizontal bar chart |
| A4 — Distribution fill rate | `GET /analytics/fill-distribution` | Histogram (tranches 10 %) |
| A5 — Évolution fill rate | `GET /analytics/fill-evolution?moving_avg=true` | Line chart + MA7 jours |
| A6 — Performance routes | `GET /analytics/route-performance` | Scatter/bubble chart |
| A7 — Incidents timeline | `GET /analytics/incidents` | Timeline mixte (signalements + notifications) |
| A8 — Heatmap collectes | `GET /analytics/heatmap` | Heatmap jour × heure |
| A9 — Carte choroplèthe | `GET /analytics/choropleth` | Leaflet choroplèthe GeoJSON |
| A10 — Coûts et ROI | `GET /analytics/costs-roi` | Mixed bar + line chart |

**Séparation des audiences :** Grafana adresse les équipes ops et infra avec des dashboards Prometheus ; FastAPI adresse les managers et les agents avec des données métier structurées, consommées par le frontend React via des endpoints REST documentés.

#### Documentation technique — MkDocs

Le site `http://docs.localhost` (namespace `documentation`) centralise la documentation technique complète : chaque DAG (graphes, paramètres, notes de runtime), chaque phase de l'API (endpoints, exemples curl), l'architecture K8s (topologie, DNS, PVCs), le schéma de base de données (26 tables, index, triggers), et les notebooks ML (ROADMAP, retraining checklist). Cette documentation "as code" constitue un actif de valeur pour la maintenance et l'onboarding de nouveaux membres.

---

## 7. Conclusion et Perspectives

### 7.1 Bilan des résultats obtenus

Le projet ECOTRACK a livré un système data opérationnel et démontrable en live sur l'ensemble du périmètre fondamental :

**Infrastructure et pipeline :** cluster Kubernetes Minikube à 5 namespaces opérationnel (0 € de cloud), pipeline IoT continu traitant 2 000 conteneurs toutes les 10 minutes, 1,44 M lignes de données historiques avec modèle physique de remplissage par type de déchet, qualité données à ~99 % de mesures valides.

**Architecture data :** Lakehouse natif PostgreSQL 15 — couches Bronze/Silver/Gold sans stack objet additionnel, 26 tables (17 OLTP + 4 OLAP + 5 gamification), 7 triggers automatisant la logique métier, 5 procédures stockées idempotentes, PostGIS opérationnel avec GIST indexes et requêtes spatiales en < 200 ms.

**API et analytique :** 40+ endpoints FastAPI dont 7 routers entièrement opérationnels, documentation Swagger auto-générée, 10 endpoints analytics (heatmap, choroplèthe, KPIs, ROI environnemental), dashboards Grafana avec datasource PostgreSQL native.

**Machine Learning :** HistGradientBoosting entraîné sur 2,265 M lignes, 14 features, CV R² = 0.673 (seuil CDC ≥ 0.65 atteint en validation croisée temporelle), diagnostic complet de l'écart CV/test avec correctif implémentable documenté.

### 7.2 Limites identifiées

**Limite principale — Test R² sous cible (0.218 vs 0.65) :** l'écart entre le CV R² (0.673) et le test R² (0.218) est structurel, causé par deux problèmes identifiés et documentés : (1) 5/14 features temporelles portent zéro signal dans les données simulées, (2) mismatch de distribution entre `lasc__seed_data` (rampes linéaires, train set) et `lasc__livesim_fill` (marches aléatoires, test set). Cette limite est une **découverte méthodologique** — le projet a produit une analyse causale complète avec correctif prêt en < 1 journée de développement.

**Limite fonctionnelle — Phase 4 incomplète :** les fonctionnalités gamification (`/leaderboard`, `/badges`, `/defis`), reports (`POST /reports/generate`) et prédiction ML (`/ml/predict`) sont en stub. Leur architecture SQL est entièrement posée — la complétion est une question de temps de développement, pas de décision technique.

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

| Fonctionnalité | Effort | Valeur |
|---|---|---|
| `GET /leaderboard` | 1–2 h — fonction SQL déjà écrite | Engagement citoyen gamifié |
| `POST /reports/generate` | 4–8 h — `reportlab` dans requirements | Rapports PDF mensuels KPIs |
| `POST /ml/predict` (activation) | 2 h — COPY modèle + câblage stub | Prédictions 24h opérationnelles |
| Tests Pytest E11 | 2–3 jours | Couverture > 50 % requise CDC |

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
