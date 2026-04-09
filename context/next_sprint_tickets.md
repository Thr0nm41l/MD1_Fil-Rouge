# Sprint 1 — Tickets JIRA (S3–S4)

## Contexte
La base de données est opérationnelle (E1 complet, PostGIS activé). L'infrastructure Kubernetes/Airflow/Grafana tourne. L'objectif du Sprint 1 est de livrer **L2 — Pipeline ETL** (S4) : API de base, ingestion IoT, et agrégations automatisées.

---

## Epic E0 — Données de Seed

### DA-01 · Script de seed réaliste
**Objectif :** Peupler la base avec des données représentatives pour permettre le développement et les tests.

**Contenu :**
- 5 zones géographiques avec polygones GeoJSON (SRID 4326)
- 2 000 conteneurs répartis dans les zones avec coordonnées GPS cohérentes
- 1 utilisateur par rôle (Admin, Manager, Worker, User)
- 30 jours d'historique dans `fill_history` (~500 mesures/conteneur)
- Données de gamification : points, badges, défis

**Critère de validation :** `SELECT COUNT(*) FROM fill_history` > 1 000 000 lignes ; agrégations `aggregate_hourly()` et `aggregate_daily()` s'exécutent sans erreur.

**Stack :** Python, Faker, psycopg2

---

## Epic E2 — Validation PostGIS (G5–G10)

### DA-02 · Script de validation des requêtes spatiales
**Objectif :** Prouver que les fonctions PostGIS répondent aux critères de performance définis.

**Contenu :**
- Requête `ST_Distance` entre deux conteneurs → résultat en mètres (G5)
- Requête `ST_Within` → liste des conteneurs d'une zone (G6)
- Requête `ST_DWithin` → conteneurs dans un rayon de 1 km (G7)
- Requête `ST_Buffer` → zone tampon de 500 m autour d'un point (G8)
- `EXPLAIN ANALYZE` sur chaque requête, temps < 200 ms pour 2 000 conteneurs (G9)
- Rapport de benchmark produit (G10)

**Critère de validation :** Toutes les requêtes < 200 ms ; rapport `.md` avec les résultats `EXPLAIN ANALYZE`.

---

## Epic E3 — API Backend Conteneurs & Zones

### DA-03 · Skeleton FastAPI
**Objectif :** Mettre en place la structure du projet backend.

**Contenu :**
- Structure de dossiers (`routers/`, `models/`, `services/`, `db/`)
- Connexion PostgreSQL via `asyncpg` ou `SQLAlchemy async`
- Endpoint `GET /health` → `{ "status": "ok" }`
- Configuration via variables d'environnement (`.env`)
- Dockerfile + intégration dans le Helm chart existant

**Critère de validation :** `GET /health` répond 200 ; conteneur Docker buildable.

---

### DA-04 · CRUD Conteneurs — lecture
**Objectif :** Exposer les données des conteneurs en lecture.

**Endpoints :**
- `GET /containers` — liste paginée, filtres : `zone_id`, `type_id`, `status`, `fill_rate_min/max` (C1)
- `GET /containers/:id` — détail + dernière mesure IoT (C2)
- `GET /containers/map` — GeoJSON pour Leaflet (C6)
- `GET /containers/critical` — conteneurs au-dessus du seuil (C11)
- `GET /containers/stats` — KPIs globaux (C18)

**Critère de validation :** Réponse < 200 ms ; format GeoJSON valide sur `/map`.

---

### DA-05 · CRUD Conteneurs — écriture
**Objectif :** Permettre la gestion des conteneurs via l'API.

**Endpoints :**
- `POST /containers` — création avec coordonnées GPS converties en `GEOMETRY(Point, 4326)` (C3)
- `PUT /containers/:id` — modification position, type, capacité, seuils (C4)
- `DELETE /containers/:id` — soft delete (`is_active = false`) (C5)

**Critère de validation :** Insertion → zone assignée automatiquement par trigger ; soft delete ne supprime pas la ligne.

---

### DA-06 · CRUD Zones
**Objectif :** Gérer les zones géographiques via l'API.

**Endpoints :**
- `POST /zones` — création avec polygone GeoJSON (Z1)
- `GET /zones/:id` — détail zone
- `PUT /zones/:id` — modification (Z1)
- `DELETE /zones/:id` — suppression (Z1)
- `GET /zones/:id/containers` — conteneurs via `ST_Within` (Z2)
- `GET /zones/stats` — nb conteneurs, taux moyen, débordements (Z3)
- `GET /zones/density` — densité conteneurs/km² (Z5)

**Critère de validation :** Polygone stocké en `GEOMETRY(Polygon, 4326)` ; `ST_Within` utilisé sur `/containers`.

---

### DA-07 · Import/Export conteneurs
**Objectif :** Permettre les opérations batch sur les conteneurs.

**Contenu :**
- `POST /containers/import` — import CSV/JSON avec rapport (succès, erreurs, doublons) (C7)
- `GET /containers/export` — export CSV et GeoJSON téléchargeables (C8)

**Critère de validation :** Import de 500 lignes → rapport détaillé ; fichier GeoJSON exporté valide.

---

## Epic E4 — Pipeline IoT & Ingestion

### DA-08 · Endpoint ingestion IoT
**Objectif :** Recevoir et stocker les mesures des capteurs IoT.

**Contenu :**
- `POST /containers/:id/measures` — ingestion d'une mesure (C12)
- Validation : valeurs 0–100 %, timestamp cohérent (C13)
- Déduplication : rejet si même capteur + même minute (C14)
- Mise à jour automatique `fill_rate` et `status` sur le conteneur (via trigger existant)
- Alerte automatique si dépassement de seuil (via trigger existant)

**Critère de validation :** Latence < 500 ms ; aucun doublon dans `fill_history` ; alerte créée dans `notifications`.

---

### DA-09 · Historique des mesures
**Objectif :** Exposer les séries temporelles des mesures.

**Endpoints :**
- `GET /containers/:id/history` — série temporelle, filtrable par période (C10, H5)
- `GET /history/heatmap-data` — matrice `(day_of_week, hour, count)` (H7)

**Critère de validation :** Données triées par date ; format heatmap `{ day, hour, count }` prêt pour Nivo.

---

### DA-10 · DAG Airflow — agrégation horaire
**Objectif :** Automatiser le calcul des stats horaires.

**Contenu :**
- DAG `aggregate_hourly` — appel à `CALL aggregate_hourly(...)` toutes les heures
- Gestion des re-runs (procédure idempotente)
- Logs d'exécution dans Airflow

**Critère de validation :** Table `aggregated_hourly_stats` alimentée après chaque run ; re-run sur une heure passée produit le même résultat (H3).

---

### DA-11 · DAG Airflow — agrégation journalière
**Objectif :** Automatiser le calcul des stats journalières.

**Contenu :**
- DAG `aggregate_daily` — appel à `CALL aggregate_daily(...)` chaque nuit à 01h00
- Dépendance sur `aggregate_hourly` (attente fin du dernier run horaire)
- Logs d'exécution dans Airflow

**Critère de validation :** Table `aggregated_daily_stats` alimentée chaque matin ; `overflow_count` et `collection_count` cohérents avec `fill_history` (H4).

---

## Récapitulatif

| Ticket | Epic      | Priorité | Dépendances |
|--------|-----------|----------|-------------|
| DA-01  | Seed      | MUST     | —           |
| DA-02  | PostGIS   | MUST     | DA-01       |
| DA-03  | Backend   | MUST     | —           |
| DA-04  | Backend   | MUST     | DA-01, DA-03|
| DA-05  | Backend   | MUST     | DA-03       |
| DA-06  | Backend   | MUST     | DA-01, DA-03|
| DA-07  | Backend   | SHOULD   | DA-05       |
| DA-08  | IoT       | MUST     | DA-03       |
| DA-09  | IoT       | MUST     | DA-01, DA-03|
| DA-10  | Airflow   | MUST     | DA-01       |
| DA-11  | Airflow   | MUST     | DA-10       |

**Livrable L2 (S4) :** DA-01, DA-03, DA-08, DA-10, DA-11 sont les tickets critiques.
