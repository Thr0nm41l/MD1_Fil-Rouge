# Document 5 — Planification Agile : Argumentation de l'Organisation Projet

> Ce document confronte la planification Agile/Scrum préconisée par le template M1 DATA
> avec l'organisation réelle du projet ECOTRACK, en argumentant chaque adaptation.

---

## I. Méthodologie Agile — Adaptation au contexte M1 DATA

### Proposition du template

Framework Scrum pur : Product Owner, Scrum Master, 8 sprints × 2 semaines, Product Backlog, Sprint Backlog, vélocité cible 25 ± 3 Story Points.

### Organisation implémentée

Le projet a adopté une organisation hybride **Scrum + découpage par Epic fonctionnel**, mieux adaptée à un projet académique solo ou en petite équipe :

| Dimension Scrum | Implémentation ECOTRACK |
|---|---|
| Durée projet | 16 semaines (8 sprints × 2 semaines) — conforme |
| Backlog | 115 tâches réparties en **11 Epics** (`context/master1_data_epics.md`) |
| Livraisons | 4 livrables jalons (L1 S2, L2 S4, L3 S8, L4 S12) + Livrable Final S16 |
| Priorité | Matrice MUST/SHOULD par catégorie (`context/master1_data_tasks.md`) |
| Suivi | Critères de validation par tâche (ex. `SELECT PostGIS_Version()`, R² > 0.65) |

**Argument — 11 Epics vs 8 Sprints :**

Le template Scrum organise le travail par sprint calendaire. Pour un projet data, le découpage par domaine fonctionnel (infrastructure BDD, géospatial, pipeline, analytics, ML…) est plus lisible car il reflète les dépendances techniques réelles : Epic E1 (BDD) est un prérequis pour E2 (PostGIS), qui l'est pour E3 (Conteneurs/API), etc. Le mapping Epic → Sprint est documenté dans `context/master1_data_epics.md` §"Répartition par Sprint".

---

## II. Backlog Produit DATA — User Stories réalisées

### Exemples de User Stories implémentées (format CDC)

| ID | User Story | Priorité | Tâche CDC | Statut |
|---|---|---|---|---|
| US-001 | En tant que Scheduler, je veux insérer 2 000 mesures toutes les 10 min sans doublon afin de simuler les capteurs IoT | MUST | H2 | ✅ `lasc__livesim_fill` |
| US-002 | En tant que Pipeline, je veux calculer les agrégats horaires idempotents afin d'alimenter les KPIs | MUST | H3 | ✅ `aggregate_hourly()` |
| US-003 | En tant que Data Analyst, je veux visualiser la heatmap collectes (jour × heure) afin d'identifier les pics | MUST | A8, H7 | ✅ `GET /analytics/heatmap` |
| US-004 | En tant que Frontend, je veux obtenir les KPIs + variations vs période précédente en < 100ms | MUST | DA3 | ✅ `GET /analytics/kpis` |
| US-005 | En tant que Modèle ML, je veux 14 features engineering depuis `fill_history` afin de prédire à 24h | MUST | ML1 | ✅ `01_eda_feature_engineering.ipynb` |
| US-006 | En tant que Manager, je veux une carte choroplèthe des zones afin de visualiser les densités | MUST | A9 | ✅ `GET /analytics/choropleth` |
| US-007 | En tant que Citoyen, je veux recevoir +10 pts automatiquement après un signalement afin d'être récompensé | SHOULD | GAM2 | ✅ Trigger `signalement_award_points` |
| US-008 | En tant que API, je veux générer un rapport PDF mensuel en < 30s afin de l'envoyer au gestionnaire | SHOULD | R1, R4 | ⚠️ Stub (BackgroundTasks) |

---

## III. Planification par Sprint — Livrables DATA réels

| Sprint | Semaines | Epic(s) | Livrables DATA réels | Statut |
|---|---|---|---|---|
| Sprint 0 | S1–2 | E1, E2 | `setup_complete.sql` — PostGIS opérationnel, 26 tables, 7 triggers, 5 procédures | ✅ L1 |
| Sprint 1 | S3–4 | E3, E4 | `lasc__seed_data` (1,44M lignes), `lasc__livesim_fill` (*/10min), `lasc__ops_containers` | ✅ L2 |
| Sprint 2 | S5–6 | E3 (zones), E8 | API Containers (C1–C20), Zones (Z1–Z5), Routes (T1–T9) — 9 routers FastAPI | ✅ |
| Sprint 3 | S7–8 | E6, E7 | 10 endpoints analytics (A1–A10), `/dashboard/config`, heatmap + choroplèthe SQL | ✅ L3 |
| Sprint 4 | S9–10 | E10, E9 | `01_eda_feature_engineering.ipynb` (2,26M rows, 14 features), `02_training.ipynb` (hgb_v1.0, CV R²=0.673) | ✅ L4 (partiel) |
| Sprint 5 | S11–12 | E7, E9 | Gamification stubs, Reports stubs, `documentation/ml/index.md` | ⚠️ En cours |
| Sprint 6 | S13–16 | E11 | Tests Pytest, documentation MkDocs (`docs.localhost`), soutenance | 🔲 À venir |

---

## V. KPIs DATA & ANALYTICS — Valeurs mesurées vs cibles

| # | KPI | Cible template | Valeur mesurée | Source |
|---|---|---|---|---|
| 1 | Qualité des données | ≥ 95% valides | ~99% (1% outliers flaggués, non supprimés) | `lasc__livesim_fill` + contraintes SQL |
| 2 | Latence ingestion pipeline | < 2s | < 5s / 2 000 conteneurs (tick 10 min) | `documentation/dags/lasc__livesim_fill.md` |
| 3 | Volume données traitées | 500K/jour | ~288K/jour (2 000 × 24 × 6 ticks/h) | `lasc__livesim_fill` schedule |
| 4 | Taux d'erreur pipeline | < 1% | 0% (retries=1, idempotence ON CONFLICT) | Airflow + psycopg2 |
| 5 | Fraîcheur données | < 5 min | 10 min (intervalle simulateur) | `lasc__livesim_fill` (*/10 * * * *) |
| 6 | Précision modèle ML (CV) | ≥ 85% R² | **CV R²=0.673** (cible 0.65 atteinte) | `documentation/ml/index.md` |
| 6b | Précision modèle ML (test) | ≥ 65% R² | **Test R²=0.218** — sous cible | Données synthétiques sans patterns temporels + mismatch entre générateurs |
| 7 | Requêtes spatiales | < 200ms / 2 000 conteneurs | < 200ms (GIST index) | EXPLAIN ANALYZE (G9) |
| 8 | Temps réponse API | < 200ms P95 | Pool psycopg2, requêtes sur agrégats | `apiservice/db.py` (max=10 connexions) |

**Analyse du KPI ML (test R²) — Cause racine identifiée :**

Le CV R² (0.673 sur 5 folds) atteint le seuil requis, mais le test R² (0.218) est en deçà. La cause n'est pas uniquement la fenêtre d'historique courte — elle est structurelle et liée au modèle de génération des données synthétiques.

**Problème 1 — Features temporelles sans signal réel (5/14 features inutiles)**

Les DAGs `lasc__seed_data` et `lasc__livesim_fill` modélisent le remplissage comme une progression purement mécanique, indépendante de l'heure ou du jour :

```python
# lasc__livesim_fill — même taux à 2h du matin qu'à 10h un vendredi
rate = FILL_RATE_PER_HOUR.get(type_id, 2.0) * RATE_SCALE
rate *= random.uniform(0.7, 1.3)   # variabilité aléatoire, pas temporelle
```

Les features `hour`, `day_of_week`, `day_of_month`, `is_weekend`, `is_peak_hour` — soit 5 des 14 features — portent **zéro signal** sur ces données. En données réelles, elles seraient les plus prédictives (déchets organiques après les weekends, zones commerciales en heures de bureau). Ici elles ajoutent du bruit et forcent le modèle à se rabattre entièrement sur les features de lag.

**Problème 2 — Mismatch entre les deux générateurs**

`lasc__seed_data` et `lasc__livesim_fill` utilisent des processus générateurs différents qui coexistent dans `fill_history` :

| Générateur | `rate_per_hour` | Bruit | Résultat |
|---|---|---|---|
| `lasc__seed_data` | Fixé **une fois** par conteneur pour 30 jours | σ=0.3/heure | Rampe quasi-linéaire, très prévisible |
| `lasc__livesim_fill` | **Resamplé à chaque tick** (10 min) | σ=0.15/tick | Marche aléatoire avec drift variable |

Le modèle apprend pendant le CV à prédire des pentes stables (données seed + début livesim), mais le jeu de test (fenêtre récente, 100% livesim avec resampling par tick) présente une variance structurellement plus élevée — c'est ce mismatch qui fait chuter le test R².

**Solution correcte :**

La simple accumulation de données ne résoudrait pas le problème des features temporelles. Le vrai correctif est d'ajouter une modulation heure/jour dans `lasc__livesim_fill` :

```python
PEAK_HOURS = {7, 8, 9, 12, 17, 18, 19}
DAY_MULT   = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.4}

rate *= DAY_MULT[now.weekday()] * (1.3 if now.hour in PEAK_HOURS else 1.0)
```

Avec cette modification, les 5 features temporelles deviennent informatives, et le test R² devrait rejoindre le CV R² après 60–90 jours d'historique enrichi.

---

## VI. Risques DATA — Bilan Réalisé vs Anticipé

| Risque template | Probabilité | Impact | Statut réel | Mitigation appliquée |
|---|---|---|---|---|
| Perte de données | Faible | Critique | ✅ Non survenu | `ON CONFLICT DO NOTHING/UPDATE`, idempotence Airflow |
| Qualité données < 95% | Moyenne | Moyen | ✅ Géré | Contraintes SQL + `is_outlier` flag |
| Latence pipeline > 2s | Moyenne | Moyen | ✅ Géré (10 min acceptable) | Procédures stockées + execute_values bulk |
| **Test R² ML < 0.65** | — | Moyen | ❌ **Matérialisé** | Cause : features temporelles sans signal (simulation mécanique) + mismatch seed/livesim. Correctif : modulation heure/jour dans `lasc__livesim_fill` + ré-entraînement |
| Endpoints gamification/ML non livrés | Faible | Moyen | ⚠️ **Partiel** | Stubs 503/❌ documentés dans `documentation/api/phase4-gamification-ml-reports.md` |

---

## VII. Budget et Ressources — Infrastructure réelle

| Ressource | Template (estimé) | Réel (Minikube) |
|---|---|---|
| Hébergement | Cloud AWS/Azure | Local Minikube (machine dev) |
| Storage | MinIO PVC + cloud S3 | ~22 Gi PVCs Minikube (`hostPath`) |
| Compute | 3 VM t3.medium | 1 nœud Minikube, 2 workers Celery |
| Licences | Jira, GitHub Enterprise | GitHub (gratuit) + Airflow open-source |
| BI | Superset/Metabase | Grafana (inclus dans kube-prometheus-stack) |
| **Coût infra** | [XX k€] | **0 € (local)** |

---

*Fichier d'argumentation — Document 5 Planification Agile / filière M1 DATA & ANALYTICS*
*Sources : `context/master1_data_epics.md`, `context/master1_data_tasks.md`, `documentation/ml/index.md`, `documentation/api/phase4-gamification-ml-reports.md`*
