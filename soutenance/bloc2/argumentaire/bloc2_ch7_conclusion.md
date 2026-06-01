# BLOC 2 — Chapitre 7 : Conclusion et Perspectives

> Template section 7 — bilan, limites, améliorations, enseignements méthodologiques

---

## Bilan du projet data

### Résultats obtenus

Le projet ECOTRACK a livré un système de traitement et d'analyse de données opérationnel sur l'ensemble du périmètre fondamental :

**Infrastructure et pipeline :**
- Cluster Kubernetes Minikube 5 namespaces, 0 € d'infrastructure cloud
- Pipeline IoT continu opérationnel (`lasc__livesim_fill`, */10 min) avec triggers SQL temps réel
- 1,44 M lignes de données historiques (30 jours, 2 000 conteneurs) avec modèle physique de remplissage
- Qualité données : ~99 % de mesures valides (1 % outliers flaggués, 0 % de violations de contraintes)

**Architecture data :**
- Lakehouse natif PostgreSQL 15 — couches Bronze/Silver/Gold sans stack objet additionnel
- 26 tables (17 OLTP + 4 OLAP + 5 gamification), 7 triggers, 5 procédures stockées idempotentes
- PostGIS opérationnel — 3 types de géométries, 4 fonctions spatiales, GIST indexes

**API et analytique :**
- 40+ endpoints FastAPI (7/9 routers complets), documentation Swagger auto-générée
- 10 endpoints analytics (A1–A10) : évolution volume, heatmap, choroplèthe, KPIs, ROI
- Dashboards Grafana avec datasource PostgreSQL native

**Machine Learning :**
- HistGradientBoosting entraîné sur 2,26 M lignes, 14 features, pipeline CRISP-DM complet (ML1–ML3)
- CV R² = 0.673 — seuil CDC (≥ 0.65) atteint en validation croisée temporelle

### Limites identifiées

**Limite ML — Test R² sous cible (0.218 vs 0.65) :**
La limite principale du projet est l'écart entre le CV R² (0.673) et le test R² (0.218). Deux causes structurelles ont été identifiées et documentées :
1. 5/14 features temporelles portent zéro signal (simulation sans modulation heure/jour)
2. Mismatch entre `lasc__seed_data` (rampes quasi-linéaires) et `lasc__livesim_fill` (marches aléatoires)

Cette limite est une **découverte méthodologique** — le projet a produit une analyse causale complète avec correctif implémentable en < 1 journée de développement.

**Limite fonctionnelle — Phase 4 incomplète :**
Les fonctionnalités gamification (`/leaderboard`, `/badges`, `/defis`), reports (`POST /reports/generate`) et prédiction ML (`/ml/predict`) sont en stub. Leur architecture SQL est en place — la complétion est une question de temps de développement.

**Limite infrastructure — Minikube local :**
L'infrastructure est validée en local sur Minikube. Un déploiement cloud multi-nœuds nécessiterait une migration des PVCs `hostPath` vers des volumes persistants gérés (AWS EBS, GCP PD) et la configuration de la haute disponibilité PostgreSQL (streaming replication ou CloudNativePG).

---

## Améliorations pour une mise en production future

### Axe 1 — Qualité du modèle ML (priorité haute)

**Action immédiate (< 1 journée) :**
```python
# Dans lasc__livesim_fill — ajouter la modulation temporelle
PEAK_HOURS = {7, 8, 9, 12, 17, 18, 19}
DAY_MULT   = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.4}
rate *= DAY_MULT[now.weekday()] * (1.3 if now.hour in PEAK_HOURS else 1.0)
```

**Suivi :** laisser tourner 60–90 jours, puis re-exécuter ML1 → ML2 → ML3 → ML4 → ML5.
Test R² attendu > 0.65 avec features temporelles informatives et historique long terme.

### Axe 2 — MLOps et déploiement continu

- **Retraining automatique** : DAG Airflow mensuel déclenchant ML1 → ML5 si `COUNT(fill_history) > threshold`
- **Model registry** : MLflow Tracking pour versionner les expériences (remplace le `metadata.json` manuel)
- **A/B testing** : deux versions du modèle en production avec routage par conteneur (`model_version` dans `ml_predictions`)

### Axe 3 — CI/CD API Service

- GitHub Actions workflow : build Docker image → push registry → `kubectl rollout restart`
- Tests Pytest sur endpoints FastAPI (`httpx` + base PostgreSQL dédiée aux tests)
- Coverage > 50 % (CDC TEST1–TEST3, Epic E11)

### Axe 4 — Scalabilité infrastructure

- **PostgreSQL HA** : migration vers CloudNativePG (operator Kubernetes) avec streaming replication
- **Partitionnement automatique** : DAG Airflow créant les nouvelles partitions mensuelles en fin d'année
- **Archivage** : DAG `DETACH PARTITION fill_history_YYYY_MM` + export Parquet vers stockage objet froid
- **TimescaleDB** : si le volume dépasse 100 M lignes/an, migrer `fill_history` vers une hypertable TimescaleDB pour la compression automatique

### Axe 5 — Fonctionnalités en retard

| Fonctionnalité | Effort estimé | Valeur |
|---|---|---|
| `GET /leaderboard` | 1–2 h (fonction SQL déjà écrite) | Gamification + engagement citoyen |
| `POST /reports/generate` | 4–8 h (reportlab + openpyxl dans requirements.txt) | Rapport PDF mensuel KPIs |
| `POST /ml/predict` (activation) | 2 h (brancher stub + COPY dans Dockerfile) | Prédictions 24h en production |
| Tests Pytest E11 | 2–3 jours | Couverture > 50 % requise CDC |

---

## Enseignements méthodologiques

**1. La simulation de données n'est pas neutre pour le ML**

Le choix de la stratégie de génération de données synthétiques a des conséquences directes sur la qualité du modèle. Un simulateur sans modulation temporelle produit des features qui semblent pertinentes (heure, jour de semaine) mais sont statistiquement inertes. Cette leçon illustre pourquoi l'EDA doit inclure une vérification de la corrélation features/target **avant** l'entraînement.

**2. La séparation OLTP/OLAP dès la conception est un investissement**

Les tables `aggregated_hourly_stats` et `aggregated_daily_stats` ont réduit les temps de réponse API de plusieurs secondes (full scan `fill_history`) à < 100 ms. Cette décision architecturale, prise dès la conception du schéma (Epic E1), a conditionné la faisabilité de l'ensemble du projet analytique.

**3. L'idempotence comme principe de conception**

L'utilisation systématique de `ON CONFLICT DO UPDATE/DO NOTHING` sur toutes les tables, combinée à `session_replication_role = 'replica'` pour le bootstrap, a permis de relancer les DAGs de développement des dizaines de fois sans corruption de données.

**4. La documentation comme livrable de premier plan**

Le site MkDocs (`docs.localhost`) et les fichiers `documentation/` ont été produits en parallèle du code, pas en fin de projet. Cette approche "docs as code" a facilité la revue des choix techniques et constituera un asset de valeur pour une équipe rejoignant le projet.

---

*Sources : `documentation/ml/index.md`, `context/master1_data_tasks.md`, `context/master1_data_epics.md`, `ml/ROADMAP.md`, `apiservice/routers/`*
