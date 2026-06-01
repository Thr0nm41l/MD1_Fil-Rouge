# Document 6 — Audit Initial : Argumentation et Bilan du Projet

> Ce document applique le cadre d'audit initial (SWOT, risques, Quick Wins, recommandations)
> à l'état réel du projet ECOTRACK au moment de la soutenance, en confrontant le prévisionnel
> du template avec les résultats effectivement obtenus.

---

## I. Objectifs de l'Audit — Constat à date

L'audit initial avait pour périmètre :
- Analyser la faisabilité avant démarrage
- Identifier les risques et les Quick Wins à fort impact

Cet audit **ex-post** évalue ce qui a été livré, ce qui est en cours, et ce qui reste à implémenter, en s'appuyant sur l'état réel des fichiers et de la documentation technique.

---

## II. ANALYSE SWOT — Bilan à date de soutenance

### A. Forces — Ce qui a été livré et fonctionne

**Forces communes (confirmées) :**
- Méthodologie structurée (11 Epics, 115 tâches, critères de validation par tâche) — `context/master1_data_epics.md`
- Infrastructure Kubernetes production-ready (Minikube, 5 namespaces, 6 Helm releases, Traefik ingress, MkDocs) — `documentation/helmcharts/k8s-architecture.md`
- Documentation technique complète : chaque DAG, chaque composant infra, chaque phase API est documenté dans `documentation/`

**Forces spécifiques DATA — réalisées :**

| Force | Preuve |
|---|---|
| Schéma PostgreSQL complet (26 tables OLTP + OLAP, 7 triggers, 5 procédures, 4 extensions) | `database/setup_complete.sql` |
| Pipeline IoT continu opérationnel (`lasc__livesim_fill`, */10 min, 2 000 conteneurs, triggers actifs) | `documentation/dags/lasc__livesim_fill.md` |
| API FastAPI complète — 9 routers, 40+ endpoints, pool psycopg2, RLS, GeoJSON | `documentation/api/` phases 1–3 ✅ |
| 10 endpoints analytics (A1–A10) + KPIs + heatmap + choroplèthe | `documentation/api/phase3-analytics.md` |
| PostGIS opérationnel — GIST indexes, ST_Within/DWithin/Distance/Area/Buffer | `setup_complete.sql` §9 Indexes |
| ML entraîné — `hgb_v1.0`, 2,26M lignes, 14 features, CV R²=0.673 | `documentation/ml/index.md` |
| Données de démo réalistes — 1,44M lignes historique 30j avec modèle physique par type | `documentation/dags/lasc__seed_data.md` |

### B. Faiblesses — Écarts par rapport aux cibles

| Faiblesse | Cause | Impact |
|---|---|---|
| **Test R²=0.218 (cible 0.65)** | Historique de ~41 jours trop court pour le lag 7j | Endpoint `/ml/predict` en stub 503 |
| **ML4 evaluation notebook non exécuté** | Bug `KeyError` dans `03_evaluation.ipynb` sur la branche HGB | Plots `pred_vs_actual.png`, `error_distribution.png`, `feature_importance.png` absents |
| **Endpoints gamification non implémentés** (`/leaderboard`, `/badges`, `/defis`) | Phase 4 en cours | CDC E9 partiellement couvert |
| **Reports non implémentés** (`POST /reports/generate`, `GET /reports/{id}/download`) | Phase 4 en cours | R4–R5 en stub |
| **ML5 endpoint stub** | Dépend de ML4 validé + déploiement `model.pkl` dans le pod | `/ml/predict` retourne 503 |

### C. Opportunités — Leviers identifiés

1. **Extension de l'historique** : avec 60–90 jours dans `fill_history`, le re-entraînement du modèle ML devrait atteindre le test R² > 0.65 (cf. retraining checklist `documentation/ml/index.md`)
2. **Fix ML4 en 15 min** : le bug `KeyError` sur `03_evaluation.ipynb` est documenté avec le correctif exact dans `documentation/ml/index.md §Known issue in 03_evaluation.ipynb` — une correction d'une dizaine de lignes Python
3. **API prédiction activable** : `model.pkl` et `metadata.json` existent dans `ml/models/`. L'activation de `/ml/predict` nécessite uniquement de brancher le stub dans `apiservice/routers/ml.py` (Option A : `COPY` dans Dockerfile, ou Option B : PVC mount)
4. **Grafana + datasource PostgreSQL** : tous les dashboards opérationnels sont accessibles sur `http://grafana.localhost` sans développement supplémentaire

### D. Menaces — Risques résiduels

1. **Retraining ML** : si l'historique est réinitialisé (re-run de `lasc__seed_data` sans précaution), le jeu de données d'entraînement est perdu — le `model.pkl` devient incohérent avec la nouvelle distribution de données
2. **Minikube en production** : l'infrastructure locale convient à la soutenance et au développement, pas à un déploiement réel multi-nœuds
3. **Pas de CI/CD** : les DAGs sont synchronisés via `git-sync` Airflow mais l'API Service nécessite un rebuild manuel du Docker image (`kubectl rollout`)

---

## III. RISQUES DATA — Bilan prévu vs réalisé

| # | Risque anticipé | Statut | Mitigation appliquée ou à appliquer |
|---|---|---|---|
| R8 | **Perte de données** (corruption/suppression) | ✅ Non survenu | Idempotence `ON CONFLICT`, Airflow retries=1 |
| R9 | **Qualité données < 95%** | ✅ Géré | Contraintes SQL + flag `is_outlier`, `aggregate_*` filtre `WHERE NOT is_outlier` |
| R10 | **Latence pipeline > 2s** | ✅ Géré | DAG < 5s / tick, `execute_values` bulk, GIST indexes |
| R11 | **Test R² ML sous cible** | ❌ **Matérialisé** | Ré-entraîner avec 60–90j historique (`documentation/ml/index.md §Retraining Checklist`) |
| R12 | **Bug ML4 evaluation** | ❌ **Matérialisé** | Fix documenté (`elif meta['model_type'] == 'hgb': ...`) — correctif prêt |
| R13 | **Endpoints gamification non livrés** | ⚠️ Partiel | Phase 4 en cours — architecture posée (tables + triggers + procédures SQL) |

---

## IV. QUICK WINS DATA — Bilan des actions réalisées

| # | Quick Win template | Statut | Résultat concret |
|---|---|---|---|
| QW4 | Validation Pydantic stricte sur ingestion | ✅ | Schemas `ContainerCreate`, `MeasureCreate` avec contraintes 0–100% ; rejets avec message d'erreur |
| QW5 | Partitionnement TimescaleDB → PostgreSQL natif | ✅ | `PARTITION BY RANGE (measured_at)`, 36 partitions mensuelles pré-créées, queries < 100ms |
| QW6 | Agrégats pré-calculés (rollups horaires/quotidiens) | ✅ | `aggregate_hourly` + `aggregate_daily` appelés dans chaque tick `lasc__livesim_fill` |
| QW7 | Alertes automatiques data quality < 95% | ✅ | Trigger `fill_history_alert` → `notifications` sur dépassement de seuil |
| QW+ | CI/CD DAGs via git-sync | ✅ | Airflow `git-sync` depuis GitHub — DAGs déployés automatiquement à chaque push |
| QW+ | Documentation technique MkDocs | ✅ | Site accessible sur `http://docs.localhost` (namespace `documentation`) |
| QW+ | Monitoring infra Prometheus + Grafana | ✅ | `ServiceMonitors` sur PostgreSQL, Redis, Airflow webserver ; alertes via AlertManager |

---

## V. RECOMMANDATIONS STRATÉGIQUES — Priorisation pour la soutenance

### Priorité 1 — Actions < 1 journée, impact fort sur l'évaluation

**R1 — Corriger ML4 (`03_evaluation.ipynb`)**
> Ajouter la branche `elif meta['model_type'] == 'hgb':` documentée dans `documentation/ml/index.md §Known issue`. Génère les 3 plots requis (`pred_vs_actual`, `error_distribution`, `feature_importance`) pour le livrable L4.

**R2 — Activer `/ml/predict` (ML5)**
> Remplacer le stub 503 dans `apiservice/routers/ml.py` par l'implémentation depuis `ml/ROADMAP.md §ML5`. `model.pkl` et `metadata.json` existent déjà. Bake le modèle dans le Docker image (Option A).

**R3 — Expliquer le test R² en soutenance**
> Le CV R² (0.673) atteint le seuil. Le test R² (0.218) reflète un historique insuffisant, pas un défaut de conception. La solution (60–90 jours, retraining checklist) est documentée — à présenter comme voie d'amélioration identifiée.

### Priorité 2 — Actions 1–3 jours

**R4 — Implémenter `/leaderboard` (GAM3/GAM4)**
> `get_leaderboard(limit, from, to)` est déjà une fonction SQL dans `setup_complete.sql`. L'endpoint est un simple `SELECT` avec tri — 1–2h de développement.

**R5 — Implémenter `POST /reports/generate` (R4)**
> La table `reports` existe. `reportlab` est dans `requirements.txt`. Le générateur PDF mensuel (KPIs + évolutions) alimente directement le score L4.

### Priorité 3 — Axes d'amélioration post-soutenance

**R6 — CI/CD API Service**
> Automatiser le rebuild Docker + rollout Kubernetes via GitHub Actions pour éliminer le déploiement manuel.

**R7 — Tests Pytest (Epic E11)**
> Couverture > 50% requise (CDC TEST1–TEST3). Les endpoints FastAPI sont testables via `httpx` + base de test dédiée.

**R8 — Retraining ML à 90 jours**
> Laisser `lasc__livesim_fill` tourner 60–90 jours, re-exécuter ML1 → ML2 → ML3 → ML4 → ML5. Test R² attendu > 0.65 avec 7-day lag features enrichies.

---

## VI. CONCLUSION DE L'AUDIT

### Bilan global

| Domaine | Tâches CDC | Livrées | Taux |
|---|---|---|---|
| Infrastructure BDD + PostGIS | E1 + E2 (16 tâches) | 16/16 | 100% ✅ |
| Conteneurs + Zones + History + Routes | E3 + E4 + E8 (43 tâches) | 43/43 | 100% ✅ |
| Analytics + Dashboard | E6 + E7 (24 tâches) | ~20/24 | ~83% ✅ |
| ML prédictif | E10 (5 tâches) | 3/5 (ML1–ML3 ✅, ML4–ML5 ⚠️) | 60% ⚠️ |
| Gamification | E9 (11 tâches) | ~4/11 (triggers + tables) | ~36% ⚠️ |
| Rapports | E7 rapports (8 tâches) | 0/8 (stubs) | 0% ❌ |
| Tests + Documentation | E11 (7 tâches) | ~4/7 (MkDocs ✅, Pytest ❌) | ~57% ⚠️ |

**FAISABILITÉ PROJET : FAVORABLE AVEC RÉSERVES**

Le socle data — schéma PostgreSQL, PostGIS, pipeline IoT, API analytics, ML entraîné — est opérationnel et démontrables en live. Les fonctionnalités en retard (gamification, rapports, ML5) ont leur architecture et leur schéma de données en place ; leur implémentation est une question de temps de développement, pas de décision technique.

---

*Fichier d'argumentation — Document 6 Audit Initial / filière M1 DATA & ANALYTICS*
*Sources : `documentation/ml/index.md`, `documentation/api/phase4-gamification-ml-reports.md`, `context/master1_data_epics.md`, `context/master1_data_tasks.md`, `documentation/helmcharts/k8s-architecture.md`*
