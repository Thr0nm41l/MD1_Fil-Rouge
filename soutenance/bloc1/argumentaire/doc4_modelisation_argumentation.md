# Document 4 — Modélisation : Argumentation du Choix et de l'Implémentation

> Le template demande de choisir **une seule méthode** parmi BPMN, UML et MERISE.
> Ce document argumente le choix de **MERISE** (MCD → MLD → MPD) et démontre
> comment chaque niveau de modélisation est réalisé dans le projet ECOTRACK.

---

## Justification du choix : MERISE

### Pourquoi MERISE et pas BPMN ou UML ?

| Méthode | Pertinence pour ECOTRACK filière DATA | Décision |
|---|---|---|
| **BPMN** | Adapté aux processus métier (remontée alerte, optimisation tournée) — orienté flux, pas données | Secondaire (processus couverts par les DAGs Airflow) |
| **UML** | Utile pour l'architecture orientée objet des services (API, schemas Pydantic) — pas central en DATA | Secondaire (couverts par `apiservice/schemas/`) |
| **MERISE** | Modélise les données relationnelles — directement aligné sur la mission filière DATA : concevoir un schéma PostgreSQL OLTP + OLAP | **Retenu** |

Le CDC (`context/master1_data_tasks.md`) exige en livrable L1 : « MCD/MLD avec types PostGIS, script de migration, dictionnaire de données ». MERISE est donc la méthode naturelle.

---

## A. Modèle Conceptuel de Données (MCD)

### Entités principales identifiées

| Entité | Attributs clés | Cardinalités |
|---|---|---|
| ZONE | name, postal_code, polygon (SRID 4326) | 1 zone contient 0,N conteneurs |
| CONTAINER | location (POINT), capacity_liters, fill_rate, status, fill_threshold_pct | 1 conteneur appartient à 1 zone |
| CONTAINER_TYPE | name, description, fill_threshold_pct | 1 type classifie 0,N conteneurs |
| DEVICE | model, firmware_version, battery_pct, last_seen | 1 device est attaché à 1 conteneur |
| FILL_HISTORY | fill_rate, temperature, battery_pct, is_outlier, measured_at | 1 conteneur a 0,N mesures (table de faits) |
| USER | email, name, first_name, password, created_at | 1 user a 0,N rôles |
| ROLE | name (Admin, Manager, Worker, User) | 0,N users ont 0,N rôles |
| TEAM | name, zone_id, team_manager | 1 team couvre 1 zone |
| ROUTE | status, distance_m, path (LINESTRING) | 1 route a 1,N étapes |
| ROUTE_STEP | step_order, collected, volume_collected_l | 1 route_step cible 1 conteneur |
| COLLECTION | collected_at, fill_rate_before, fill_rate_after, volume_collected_l | 1 collection = 1 événement de vidage |
| SIGNALEMENT | description, status, created_at, resolved_at | 1 citoyen crée 0,N signalements |

**Entités OLAP / analytiques :**

| Entité | Description |
|---|---|
| AGGREGATED_HOURLY_STATS | KPIs pré-calculés par heure × conteneur |
| AGGREGATED_DAILY_STATS | KPIs pré-calculés par jour × conteneur + overflow_count |
| ML_PREDICTIONS | Prédictions modèle ML (horizon 24h) avec `actual_fill_rate` ex-post |

**Entités Gamification :**

| Entité | Description |
|---|---|
| USER_POINTS | Ledger append-only des points gagnés |
| BADGES | Catalogue 30 badges avec `condition_sql` |
| USER_BADGES | Attribution badges (UNIQUE user × badge) |
| DEFIS | Défis collectifs avec `target_value` |
| DEFI_PARTICIPATIONS | Progression individuelle par défi |

---

## B. Modèle Logique de Données (MLD)

Les relations many-to-many sont matérialisées par des tables de jonction :

```
ROLE          (key_role, name)
ZONES         (key_zone, name, postal_code, #polygon:GEOMETRY(Polygon,4326))
CONTAINER_TYPE(key_type, name, description, fill_threshold_pct)
USERS         (key_user, email, name, first_name, password, created_at)
TEAMS         (key_teams, #zone_id, #team_manager, name)
CONTAINERS    (key_container, #location:GEOMETRY(Point,4326), #type_id, #zone_id,
               capacity_liters, fill_rate, status, fill_threshold_pct,
               last_updated, is_active)
DEVICE        (key_device, #container_id, model, firmware_version,
               battery_pct, last_seen, is_active)

-- Tables de jonction
USER_ROLE     (key_user_role, #user_key, #role_key)
USER_TEAM     (key_user_team, #key_user, #key_team, affectation_date)

-- OLTP événementiel
FILL_HISTORY  (key_history, measured_at, #container_id, #device_id,
               fill_rate, temperature, battery_pct, is_outlier)
               [PARTITION BY RANGE (measured_at)]
COLLECTIONS   (key_collection, #container_id, #agent_id, #route_id,
               collected_at, fill_rate_before, fill_rate_after, volume_collected_l)
SIGNALEMENTS  (key_signalement, #container_id, #user_id, #zone_id,
               description, status, created_at, resolved_at)
ROUTES        (key_route, #team_id, #path:GEOMETRY(LineString,4326),
               status, distance_m, planned_at, completed_at)
ROUTE_STEPS   (key_step, #route_id, #container_id, step_order,
               collected, collected_at, volume_collected_l)

-- OLAP
AGGREGATED_HOURLY_STATS (key, #container_id, bucket_hour,
                         avg_fill_rate, min_fill_rate, max_fill_rate, measurement_count)
AGGREGATED_DAILY_STATS  (key, #container_id, stat_date,
                         avg_fill_rate, min_fill_rate, max_fill_rate,
                         measurement_count, overflow_count, collection_count)
ML_PREDICTIONS          (key, #container_id, predicted_at, horizon_hours,
                         predicted_fill_rate, actual_fill_rate, model_version)

-- Gamification
USER_POINTS        (key, #user_id, points, action_type, earned_at)
BADGES             (key, name, category, description, points_value, condition_sql)
USER_BADGES        (key, #user_id, #badge_id, earned_at)   [UNIQUE user × badge]
DEFIS              (key, title, type, target_value, reward_points, ends_at, is_active)
DEFI_PARTICIPATIONS(key, #defi_id, #user_id, progress, completed, completed_at)
```

---

## C. Modèle Physique de Données (MPD) — Extraits SQL PostgreSQL

### Spécificités PostGIS (SRID 4326 — WGS84)

```sql
-- Zones — polygone de délimitation géographique
CREATE TABLE public.zones (
    key_zone    SERIAL PRIMARY KEY,
    postal_code INTEGER UNIQUE,
    name        VARCHAR(100),
    polygon     GEOMETRY(Polygon, 4326)   -- ST_Within, ST_Area, ST_Centroid
);

-- Containers — position GPS
CREATE TABLE public.containers (
    key_container      SERIAL PRIMARY KEY,
    location           GEOMETRY(Point, 4326) NOT NULL,  -- ST_MakePoint(lng, lat)
    type_id            INTEGER REFERENCES container_type(key_type),
    zone_id            INTEGER REFERENCES zones(key_zone),
    fill_rate          NUMERIC(5,2) CHECK (fill_rate >= 0 AND fill_rate <= 100),
    status             VARCHAR(20) CHECK (status IN ('empty','normal','full','critical')),
    fill_threshold_pct NUMERIC(5,2) NOT NULL DEFAULT 70.00,
    is_active          BOOLEAN NOT NULL DEFAULT true
);

-- Routes — tracé GPS du parcours de collecte
CREATE TABLE public.routes (
    key_route   SERIAL PRIMARY KEY,
    path        GEOMETRY(LineString, 4326),  -- ST_Length::geography → distance en m
    distance_m  NUMERIC(10,2),
    status      VARCHAR(20)
);
```

### Table de faits OLAP partitionnée

```sql
-- fill_history — table de faits IoT, partitionnée par mois
CREATE TABLE public.fill_history (
    key_history    BIGINT NOT NULL DEFAULT nextval('fill_history_key_seq'),
    measured_at    TIMESTAMP NOT NULL,
    container_id   INTEGER,
    device_id      INTEGER,
    fill_rate      NUMERIC(5,2) CHECK (fill_rate >= 0 AND fill_rate <= 100),
    temperature    NUMERIC(5,1),
    battery_pct    NUMERIC(5,2),
    is_outlier     BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (key_history, measured_at)   -- partition key incluse
) PARTITION BY RANGE (measured_at);

-- Partitions pré-créées 2025
CREATE TABLE fill_history_2025_01
    PARTITION OF fill_history FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
-- ... (2024, 2025, 2026 + _default)
```

### Index clés

```sql
-- Spatial — GIST obligatoire pour ST_Within, ST_DWithin, ST_Distance
CREATE INDEX containers_location_gist_idx ON containers USING gist (location);
CREATE INDEX zones_polygon_gist_idx       ON zones      USING gist (polygon);
CREATE INDEX routes_path_gist_idx         ON routes     USING gist (path);

-- Temporel — pattern dominant H5: série temporelle par conteneur
CREATE INDEX fill_history_container_time_idx
    ON fill_history (container_id, measured_at DESC);

-- Partiels — optimisation requêtes courantes
CREATE INDEX containers_status_active_idx
    ON containers (status) WHERE is_active = true;
```

### Triggers automatisant la logique métier

| Trigger | Table | Événement | Effet |
|---|---|---|---|
| `containers_assign_zone` | `containers` | BEFORE INSERT/UPDATE location | Résout `zone_id` via `ST_Within` |
| `fill_history_update_container` | `fill_history` | AFTER INSERT | Sync `fill_rate`, `status`, `last_updated` |
| `fill_history_alert` | `fill_history` | AFTER INSERT | Crée notification si seuil dépassé |
| `signalement_award_points` | `signalements` | AFTER INSERT | +10 pts au citoyen déclarant |
| `user_badges_award_points` | `user_badges` | AFTER INSERT | Points badge + notification |

---

## Conclusion du choix MERISE

MERISE est la méthode la plus adaptée à la filière DATA car elle structure directement le schéma PostgreSQL qui est le livrable central du projet. Les trois niveaux MCD → MLD → MPD correspondent exactement aux trois étapes de conception réalisées :
1. **MCD** : identification des entités et relations lors de l'Epic E1 (BDD1–BDD2)
2. **MLD** : traduction en tables relationnelles avec types et cardinalités (BDD3, BDD4)
3. **MPD** : script `database/setup_complete.sql` avec types PostGIS, partitionnement, index, triggers et procédures — le MPD **est** le livrable L1 du CDC

---

*Fichier d'argumentation — Document 4 Modélisation / filière M1 DATA & ANALYTICS*
*Sources : `database/setup_complete.sql`, `documentation/database/setup_complete.md`, `context/master1_data_tasks.md` (L1)*
