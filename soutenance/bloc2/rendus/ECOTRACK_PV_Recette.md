# Procès-Verbal de Recette — ECOTRACK v1.0

---

| Champ | Valeur |
|---|---|
| **Projet** | ECOTRACK — Plateforme de gestion intelligente des déchets urbains |
| **Version recettée** | v1.0 — commit `8ee83c1` (branche `soutenance/Thomas`) |
| **Commanditaire** | Métropole de Lyon — Direction de la Propreté Urbaine |
| **Instance décisionnaire** | Jury de soutenance INGETIS / Métropole de Lyon (client fictif) |
| **Testeur** | Thomas Besniard — M1 Data & Analytics |
| **Environnement** | Minikube v1.x — macOS Darwin 25.5.0 — 5 namespaces Kubernetes |
| **Date de recette** | \_\_\_\_ / \_\_\_\_ / 2026 |
| **Référentiel de critères** | `context/master1_data_tasks.md` — 115 tâches CDC |

---

## 1. Objet et périmètre de la recette

La présente recette vise à valider la conformité de la plateforme ECOTRACK v1.0 au cahier des charges fonctionnel et technique. Elle couvre l'ensemble du périmètre v1.0 défini dans les Epics E1 à E11, à l'exception des fonctionnalités explicitement placées en **réserve** (cf. §4).

Le système recetté comprend :
- L'infrastructure Kubernetes (5 namespaces, 6 Helm releases)
- La base de données PostgreSQL 15 + PostGIS (26 tables, 7 triggers, 5 procédures stockées)
- Les 4 DAGs Airflow (pipeline IoT continu, bootstrap, opérations, maintenance)
- L'API REST FastAPI (9 routers, 40+ endpoints)
- Les dashboards Grafana (5 dashboards, datasources Prometheus + PostgreSQL)
- Le modèle ML `hgb_v1.0` (HistGradientBoosting, 14 features, 2 265 488 lignes)
- La documentation MkDocs (`http://docs.localhost`)

---

## 2. Tableau des cas de test

### 2.1 Infrastructure & Déploiement

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| INF-01 | Démarrage du cluster Kubernetes | 5 namespaces actifs (`airflow`, `datalake`, `monitoring`, `traefik`, `documentation`) | 5 namespaces Running, 6 Helm releases déployées | ✅ |
| INF-02 | Accessibilité des services via Ingress Traefik | `api.localhost`, `grafana.localhost`, `docs.localhost`, `pgadmin.localhost` résolus | Routing hostname-based opérationnel via Traefik v3 | ✅ |
| INF-03 | Persistance des données PostgreSQL | Les données survivent à un redémarrage du pod `postgres-postgresql` | PVC `hostPath` ~22 Gi monté, données persistées entre redémarrages | ✅ |
| INF-04 | Connectivité inter-namespaces | Le scheduler Airflow atteint PostgreSQL via DNS interne | `postgres-postgresql.datalake.svc.cluster.local:5432` accessible depuis namespace `airflow` | ✅ |

### 2.2 Base de données & Schéma

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| BDD-01 | Création du schéma complet | 26 tables créées, contraintes `CHECK` / `FK` / `NOT NULL` actives | Schéma `setup_complete.sql` exécuté sans erreur, 26 tables présentes | ✅ |
| BDD-02 | Partitionnement de `fill_history` | 36 partitions mensuelles pré-créées (2024–2026) + partition `_default` | Partitions vérifiées via `pg_inherits` | ✅ |
| BDD-03 | Index spatiaux PostGIS | Requêtes `ST_Within` sur 2 000 conteneurs < 200 ms | Index GIST sur `containers.location` et `zones.polygon` — latence < 200 ms mesurée | ✅ |
| BDD-04 | Trigger `fill_history_update_container` | `containers.fill_rate` et `status` mis à jour à chaque INSERT dans `fill_history` | Synchronisation vérifiée après insertion manuelle de mesures | ✅ |
| BDD-05 | Trigger `fill_history_alert` | Insertion dans `notifications` si `fill_rate > fill_threshold_pct` | Notifications générées automatiquement lors des dépassements de seuil | ✅ |
| BDD-06 | Trigger `containers_assign_zone` | `zone_id` résolu automatiquement via `ST_Within(location, polygon)` à l'insertion | Attribution de zone vérifiée sur 2 000 conteneurs | ✅ |
| BDD-07 | Row Level Security | Un utilisateur ne peut lire que ses propres données dans `signalements` et `notifications` | `SET LOCAL app.user_id` vérifié — les requêtes inter-utilisateurs retournent 0 lignes | ✅ |

### 2.3 Pipeline ETL — DAGs Airflow

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| ETL-01 | DAG `lasc__seed_data` — génération initiale | 1 440 000 lignes `fill_history` générées sur 30 jours | 1 440 000 lignes insérées en ~10 minutes ; `aggregated_hourly_stats` et `aggregated_daily_stats` peuplés | ✅ |
| ETL-02 | DAG `lasc__seed_data` — idempotence | Re-run sans duplication ni erreur | `ON CONFLICT DO UPDATE/NOTHING` — données cohérentes après plusieurs re-runs | ✅ |
| ETL-03 | DAG `lasc__livesim_fill` — cycle nominal | ~2 000 lignes insérées par tick, durée < 5 s, agrégations Gold mises à jour | Durée mesurée < 5 s ; `aggregated_hourly_stats` mis à jour par `ON CONFLICT DO UPDATE` | ✅ |
| ETL-04 | DAG `lasc__livesim_fill` — idempotence | Re-run d'un tick déjà traité sans doublon | `ON CONFLICT DO NOTHING` sur `(container_id, measured_at)` — 0 doublon | ✅ |
| ETL-05 | DAG `lasc__ops_containers` — collecte | INSERT dans `collections`, `containers.fill_rate` remis à 5,0 | Collecte enregistrée, état conteneur réinitialisé | ✅ |
| ETL-06 | DAG `masc__clean_xcoms` | Suppression des XComs > 7 jours | XComs purgés quotidiennement sans erreur | ✅ |

### 2.4 Qualité des données

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| QUA-01 | Taux de données valides | ≥ 95 % de mesures valides (CDC) | ~99 % de mesures valides — 1 % flaggées `is_outlier`, 0 % de violations `CHECK` | ✅ |
| QUA-02 | Contrainte domaine `fill_rate` | Rejet de toute valeur hors `[0, 100]` | Contrainte `CHECK (fill_rate >= 0 AND fill_rate <= 100)` active — insertions hors domaine rejetées | ✅ |
| QUA-03 | Filtrage outliers dans les agrégats Gold | `aggregated_*_stats` exclut les lignes `is_outlier = true` | Filtre `WHERE NOT is_outlier` vérifié dans `CALL aggregate_hourly()` et `CALL aggregate_daily()` | ✅ |
| QUA-04 | Fraîcheur des données | Nouvelles mesures disponibles dans `aggregated_hourly_stats` < 10 min après ingestion | Mise à jour toutes les 10 minutes par `lasc__livesim_fill` — fraîcheur ≤ 10 min | ✅ |

### 2.5 API REST FastAPI

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| API-01 | Documentation Swagger | Swagger UI accessible à `http://api.localhost/docs` | Documentation auto-générée Pydantic v2 accessible | ✅ |
| API-02 | Router `containers` (C1–C20) | CRUD complet, filtres géospatiaux, statut temps réel | 20 endpoints opérationnels — CRUD, `ST_Within`, statut `fill_rate` | ✅ |
| API-03 | Router `zones` (Z1–Z5) | CRUD et export GeoJSON | 5 endpoints opérationnels — export `ST_AsGeoJSON(polygon)` | ✅ |
| API-04 | Router `history` (H5–H7) | Série temporelle par conteneur, agrégats horaires/quotidiens | Endpoints opérationnels — pagination `LIMIT/OFFSET`, requêtes sur `fill_history` et `aggregated_*` | ✅ |
| API-05 | Router `routes` (T1–T9) | CRUD routes et étapes, distance `ST_Length` | 9 endpoints opérationnels — distance en mètres via `ST_Length(path::geography)` | ✅ |
| API-06 | Router `analytics` (A1–A10 + KPIs) | 10 endpoints analytics + KPIs + heatmap + choroplèthe | Opérationnels — heatmap, choroplèthe GeoJSON, KPI cards avec variation %, ROI CO₂ | ✅ |
| API-07 | Latence API analytics | Temps de réponse P95 < 200 ms (CDC) | Agrégats pré-calculés dans les tables Gold — latence < 200 ms mesurée | ✅ |
| API-08 | Pool de connexions PostgreSQL | Requêtes concurrentes sans timeout | `ThreadedConnectionPool` (max=10) — pas de saturation sous charge nominale | ✅ |
| API-09 | Router `gamification` (GAM3–GAM11) | Endpoints leaderboard, badges, défis opérationnels | **Stubs** — réponses statiques — cf. Réserve R-01 | ⚠️ |
| API-10 | Router `reports` (R4–R5) | Génération et téléchargement de rapports PDF et Excel | Opérationnel — génération async `BackgroundTasks`, PDF (`reportlab`) + Excel (`openpyxl`), table `reports` avec cycle `pending`→`processing`→`ready` | ✅ |
| API-11 | Router `ml` — `POST /ml/predict` | Prédiction 24h retournée avec `predicted_fill_rate` et `model_version` | **Stub 503** — modèle disponible, câblage non effectué — cf. Réserve R-02 | ⚠️ |

### 2.6 Machine Learning

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| ML-01 | Feature engineering sans data leakage | Toutes les features rolling utilisent `shift(1)` avant la fenêtre glissante | Vérifié dans `01_eda_feature_engineering.ipynb` — aucune fuite future | ✅ |
| ML-02 | Split temporel train/test | Jeu de test strictement postérieur au jeu d'entraînement | Split 85/15 sur `measured_at` trié — train : 2026-04-10→05-03, test : 2026-05-03→05-09 | ✅ |
| ML-03 | Validation croisée temporelle | `TimeSeriesSplit(n_splits=5)` préserve l'ordre chronologique | CV R² = **0,673** ≥ seuil CDC 0,65 ✅ | ✅ |
| ML-04 | Métrique test R² | R² ≥ 0,65 sur le jeu de test (CDC) | Test R² = **0,218** — sous cible — cf. Réserve R-03 | ⚠️ |
| ML-05 | Feature Store Parquet | `training_features.parquet` lisible par `pd.read_parquet()` | 2 265 488 lignes × 14 features — fichier valide | ✅ |
| ML-06 | Persistance du modèle | `model.pkl` chargeable par `joblib.load()` | `hgb_v1.0` chargeable, `metadata.json` à jour (`trained_at: 2026-05-14`) | ✅ |

### 2.7 Sécurité & Conformité RGPD

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| SEC-01 | Hachage des mots de passe | Mots de passe stockés en bcrypt — aucun mot de passe en clair en base | Bcrypt facteur 12 via `pwd_context.hash()` — colonne `password` hachée | ✅ |
| SEC-02 | Anonymisation des données IoT | `fill_history` ne contient aucun identifiant utilisateur direct | `container_id` sans lien PII — `user_id` absent de la table de faits | ✅ |
| SEC-03 | Absence de PII dans le dataset ML | Le fichier `training_features.parquet` ne contient aucune colonne PII | 14 features vérifiées : physiques, temporelles, géographiques agrégées — 0 PII | ✅ |
| SEC-04 | Row Level Security PostgreSQL | Les politiques RLS sont actives sur les tables sensibles | RLS activée sur `users`, `signalements`, `notifications`, `user_role` | ✅ |

### 2.8 Observabilité & Monitoring

| ID | Cas de test | Critère d'acceptation | Résultat obtenu | Statut |
|---|---|---|---|:---:|
| MON-01 | Dashboards Grafana opérationnels | 5 dashboards accessibles à `http://grafana.localhost` | Infrastructure K8s, Airflow health, PostgreSQL, Fill history, Alertes actives — tous accessibles | ✅ |
| MON-02 | Datasource PostgreSQL Grafana | Requêtes SQL directes sur `aggregated_daily_stats` depuis Grafana | Datasource configurée et fonctionnelle | ✅ |
| MON-03 | Alertes `threshold_breach` | Notification générée dès `fill_rate > fill_threshold_pct` | Trigger `fill_history_alert` vérifié sur données de test | ✅ |
| MON-04 | Documentation MkDocs | Site `http://docs.localhost` accessible avec DAGs, API, BDD, ML documentés | Site MkDocs opérationnel — DAGs, phases API, schéma BDD, notebooks ML documentés | ✅ |

---

## 3. Récapitulatif des statuts

| Statut | Nombre | % |
|:---:|:---:|:---:|
| ✅ Validé | 30 | 91 % |
| ⚠️ Réserve | 3 | 9 % |
| ❌ Bloquant | 0 | 0 % |
| **Total** | **33** | **100 %** |

---

## 4. Réserves

Les points suivants sont recettés avec réserve. Ils ne bloquent pas la mise en production de la version v1.0 sur le périmètre fondamental, mais font l'objet d'un engagement de livraison documenté.

**R-01 — Module Gamification (API-09)**
Les endpoints GAM3–GAM11 (`/leaderboard`, `/badges`, `/defis`) retournent des réponses statiques. L'architecture SQL est entièrement posée (tables `user_points`, `badges`, `user_badges`, `defis`, `defi_participations`, trigger `signalement_award_points` opérationnel). Effort estimé : 1–2 heures par endpoint.
*Engagement : livraison en v1.1 post-soutenance.*

**R-02 — Endpoint de prédiction ML (API-11)**
`POST /ml/predict` retourne HTTP 503. Le modèle `hgb_v1.0` (`model.pkl`, `metadata.json`) est entraîné et disponible dans `ml/models/`. L'activation nécessite une instruction `COPY ml/models/model.pkl /ml/models/model.pkl` dans le Dockerfile et un `kubectl rollout restart deployment/apiservice -n datalake`.
*Engagement : activation en v1.1 — effort estimé : 2 heures.*

**R-03 — Test R² du modèle ML (ML-04)**
Le test R² = 0,218 est inférieur au seuil CDC de 0,65. Le CV R² = 0,673 atteint le seuil en validation croisée temporelle. L'écart est structurel et documenté : (1) 5/14 features temporelles portent un signal nul dans les données simulées, (2) mismatch de distribution entre `lasc__seed_data` (train set, rampes linéaires) et `lasc__livesim_fill` (test set, marches aléatoires). Le correctif est prêt (`PEAK_HOURS` + `DAY_MULT` dans `lasc__livesim_fill`) ; le re-entraînement après 60–90 jours d'historique enrichi est documenté dans `ml/ROADMAP.md §Retraining Checklist`.
*Engagement : re-entraînement après accumulation de 60–90 jours d'historique avec signal temporel enrichi.*

---

## 5. Décision

> Le périmètre fondamental de la plateforme ECOTRACK v1.0 est **validé avec réserves**.
>
> Les 30 cas de test sans réserve couvrent l'infrastructure Kubernetes, le schéma de données, les 4 DAGs Airflow, la qualité des données, les 6 routers API entièrement opérationnels (dont la génération de rapports PDF/Excel), la démarche ML (CV R² ≥ 0,65 atteint), la conformité RGPD et l'observabilité Grafana.
>
> Les 3 réserves (R-01 à R-03) correspondent à des fonctionnalités en stub (gamification, ML endpoint) et à un écart de performance ML en test, sans caractère bloquant sur le périmètre opérationnel v1.0. Un plan de levée des réserves est documenté avec engagements de livraison.
>
> **Décision : MISE EN PRODUCTION AUTORISÉE sous réserves R-01 à R-03.**

---

## 6. Signatures

| Rôle | Nom | Signature | Date |
|---|---|---|---|
| Testeur / Développeur | Thomas Besniard | | \_\_\_\_ / \_\_\_\_ / 2026 |
| Représentant commanditaire | Métropole de Lyon — Direction Propreté Urbaine | | \_\_\_\_ / \_\_\_\_ / 2026 |
| Instance décisionnaire | Jury INGETIS M1 Data & Analytics | | \_\_\_\_ / \_\_\_\_ / 2026 |

---

*Référentiel : `context/master1_data_tasks.md` · `ml/models/metadata.json` · `documentation/ml/index.md` · `documentation/dags/` · `documentation/api/`*
*Version du système : commit `8ee83c1` — branche `soutenance/Thomas`*
