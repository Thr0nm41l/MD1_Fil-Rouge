# Synthèse des compétences Bloc 2 — BESNIARD Thomas

> Dossier analysé : `ECOTRACK_Dossier_Professionnel_BLOC2_PROSE.md`
> Dernière mise à jour : 2026-06-09

---

## Tableau de synthèse

| # | Compétence | Statut | Section(s) du dossier | Ce qui est couvert | Ce qui manque |
|---|---|:---:|---|---|---|
| 1 | **Concevoir un processus de collecte et de traitement** en déterminant le référentiel de données, en créant des procédures de sélection/extraction et des solutions de stockage afin de préparer le paramétrage des outils ETL | ✅ Présente | §2.2, §2.3, §3.1, §4.1 | Référentiel décrit (6 sources, caractérisation 4V en §2.2). Architecture de stockage Bronze/Silver/Gold justifiée (§2.3, §3.1). Pipeline ETL en 4 étapes documenté (§4.1). Paramétrage des outils (Airflow, psycopg2 `execute_values`, procédures stockées) explicité | RAS — compétence bien couverte |
| 2 | **Élaborer une doctrine de collecte exhaustive** en décrivant les étapes et calculs de traitement et de visualisation dans le respect des normes juridiques et des procédures de sécurité des données | ✅ Présente | §4.1, §4.2, §6.2, §2.2 (RGPD) | Doctrine ETL formalisée : 7 règles de qualité (§4.2), stratégie audit-first `is_outlier`, triggers de propagation synchrones (§3.1). Visualisation documentée : 5 dashboards Grafana + 10 endpoints analytics A1–A10 (§6.2). Normes RGPD : bcrypt facteur 12, RLS `SET LOCAL app.user_id`, aucune PII dans le dataset ML (§2.2) | RAS — compétence couverte |
| 3 | **Intégrer des données à la solution de traitement** en extrayant les sources, en automatisant les flux et en transformant les données de différentes sources pour les harmoniser avant stockage | ✅ Présente | §4.1, §3.1 | Extraction documentée (requête SQL sur `containers` + `devices`, §4.1 étape 1). Automatisation des flux : 4 DAGs Airflow avec schedules et déclencheurs distincts. Transformation détaillée : modèle physique de remplissage par type, bruit gaussien σ=0,15, clamping `[0, 100]`, flag `is_outlier`. Harmonisation Silver via filtre `NOT is_outlier` et trigger géospatial `containers_assign_zone` | RAS — compétence couverte |
| 4 | **Alimenter les environnements de stockage** en lançant la procédure de chargement et en supervisant son bon fonctionnement pour disposer d'une base structurée, actualisée et exploitable | ✅ Présente | §4.1, §4.2, §3.1 | Chargement bulk idempotent via `execute_values` + `ON CONFLICT DO NOTHING` (§4.1 étape 3). Supervision : `pg_stat_statements`, `ServiceMonitors` Prometheus sur Airflow/PostgreSQL/Redis (§4.2). Base actualisée toutes les 10 minutes, qualité ~99 % mesures valides. Bootstrap `lasc__seed_data` : 1,44 M lignes en ~10 minutes avec désactivation contrôlée des triggers | RAS — compétence couverte |
| 5 | **Installer et paramétrer des solutions de stockage de données massives** en structurant des bases NoSQL, en organisant des systèmes de fichiers distribués et de stockage répartis afin d'obtenir un environnement opérationnel et conforme | ✅ Présente | §2.3 (nouveau §), `argumentaire/argumentaire_competence5_NoSQL_distribue.md` | Trois composants NoSQL/distribués explicitement documentés : **Redis** (broker Celery, NoSQL KV en mémoire, dépendance critique du pipeline), **Apache Parquet** (format columnar distribué du Feature Store, 2,265 M lignes, compatible Spark/Delta Lake sans modification de code), **PostgreSQL partitionné** (36 partitions mensuelles = sharding temporel équivalent Cassandra/TimescaleDB, partition pruning documenté). Quatre alternatives évaluées et rejetées avec justification : TimescaleDB, Delta Lake/Iceberg, MinIO, MongoDB. Argumentaire oral structuré (3 min) avec seuils de déclenchement des technologies et scénario ×10 volume. | RAS — compétence couverte |
| 6 | **Mettre les données à disposition des Data Scientists / Analysts** selon un format exploitable en s'appuyant sur les données de référence pour garantir la qualité et consolider les systèmes de stockage (Data Warehouse / Data Lake) | ✅ Présente | §3.2, §6.1, §4.2 | Feature Store Parquet versionné (`ml/data/training_features.parquet`, 2,265 M lignes × 14 features) directement consommable par `pd.read_parquet()` (§3.2). API FastAPI 40+ endpoints avec documentation Swagger auto-générée (§6.1). Couche Gold (Data Warehouse) exposée via `aggregated_*_stats`. Qualité garantie par contraintes SQL + flag `is_outlier` + monitoring (§4.2) | RAS — compétence couverte |
| 7 | **Analyser de gros volumes de données** en développant des algorithmes et en réalisant des analyses statistiques et techniques pour produire des résultats chiffrés et quantifiés | ✅ Présente | §5.1, §5.2, §5.3 | 2 265 488 lignes analysées (§5.1). EDA complète : distribution bimodale, autocorrélation des lags, analyse des valeurs manquantes (§5.2). 3 algorithmes comparés avec métriques chiffrées : LinearRegression (CV R²=0,094), RandomForest (CV R²=0,522), **HistGradientBoosting (CV R²=0,673)** (§5.3). Diagnostic causal de l'écart CV/test avec identification de 2 causes structurelles. Baseline naïve établie à R²≈0,08 | RAS — compétence bien couverte |
| 8 | **Présenter les résultats aux utilisateurs** sous forme de rapports structurés et intelligibles en exploitant des outils de restitution, en ajoutant des moyens de segmentation et d'organisation pour garantir la compréhension | ✅ Présente | §6.1, §6.2, §6.3 | Outils de restitution : 10 endpoints analytics A1–A10, 5 dashboards Grafana, **router `reports` entièrement opérationnel** (`POST /reports/generate` → 202, `GET /reports/{id}/download` → `FileResponse`). Rapports structurés : PDF (`reportlab`, table KPI + Top Zones, en-tête `#2d6a4f`) et Excel (`openpyxl`, feuilles Summary + Zones). Segmentation sur 3 axes : type de rapport (monthly/weekly/custom), zone géographique (`zone_id`), utilisateur (`user_id`). Génération asynchrone `BackgroundTasks` avec cycle `pending`→`processing`→`ready` tracé dans la table `reports` | RAS — compétence couverte |
| 9 | **Tester l'architecture d'exploitation** en concevant des tests de validation et en les menant sur l'environnement de recette pour garantir le bon fonctionnement et décider de la mise en production | ✅ Présente | `apiservice/tests/`, `documentation/tests/index.md` | Suite Pytest complète : 58 tests répartis en 5 fichiers couvrant l'API (contrats de réponse, pagination, 404), la qualité des données (fill_rate ∈ [0,100], taux d'outliers ≤ 5 %, PII absentes), l'intégrité du schéma (26 tables, ≥ 36 partitions), l'idempotence pipeline (`ON CONFLICT DO NOTHING` vérifié par insertion puis rollback), et le modèle ML (CV R² ≥ 0,65, 14 features, absence de data leakage). Deux modes : 18 tests unitaires (mock DB, sans infra), 40 tests d'intégration (PostgreSQL live via port-forward). Documentation technique en anglais dans `documentation/tests/index.md` avec tableau CDC Coverage Map | RAS — compétence couverte |
| 10 | **Rédiger le bilan des tests dans un procès-verbal de recette** après consignation des résultats dans un tableau afin de valider la mise en production par une instance décisionnaire | ✅ Présente | `soutenance/bloc2/rendus/ECOTRACK_PV_Recette.md` | PV de recette formalisé : 33 cas de test structurés en 8 domaines (Infrastructure, BDD, ETL, Qualité, API, ML, Sécurité, Monitoring), résultats obtenus vs critères CDC, statut go/⚠️ par cas. 4 réserves documentées avec effort estimé et engagement de livraison (R-01 gamification 1–2h, R-02 reports PDF 4–8h, R-03 `/ml/predict` 2h, R-04 test R² sous cible + checklist re-entraînement). Décision finale explicite : **mise en production autorisée sous réserves**. Instance décisionnaire identifiée (Métropole de Lyon / Jury INGETIS). Bloc signatures avec champs date | RAS — compétence couverte |

---

## Résumé exécutif

| Statut | Nombre | Compétences |
|:---:|:---:|---|
| ✅ Présente | 10 | #1 Collecte/traitement, #2 Doctrine, #3 Intégration, #4 Alimentation stockage, **#5 NoSQL/distribué**, #6 Mise à disposition, #7 Analyse volumétrique, **#8 Rapports structurés**, #9 Tests de validation, #10 PV de recette |
| ⚠️ Partielle | 0 | — |
| ❌ Absente | 0 | — |

---

## Points d'attention prioritaires avant soutenance

Toutes les compétences sont désormais couvertes (10/10 ✅). Aucun point bloquant restant avant la soutenance.

**À préparer pour l'oral :**
- **Compétence #5 (NoSQL/distribué)** : maîtriser l'argumentaire dans `argumentaire/argumentaire_competence5_NoSQL_distribue.md` — réponse en 3 parties (Redis/Parquet/partitionnement, alternatives rejetées, scénario ×10 volume).
- **Compétence #8 (Rapports structurés)** : pouvoir démontrer `POST /reports/generate` + `GET /reports/{id}/download` en live, ou décrire le cycle `pending → ready` et les deux formats PDF/Excel.
- **Compétence #9 (Tests)** : lancer `pytest apiservice/tests/ -m "not integration"` pour les 18 tests unitaires sans infrastructure.

---

## Livrables produits

| Livrable | Fichier | Compétence(s) adressée(s) |
|---|---|---|
| Dossier professionnel (version prose) | `rendus/ECOTRACK_Dossier_Professionnel_BLOC2_PROSE.md` | #1 à #8, #5 (§2.3 NoSQL), #8 (§6.3 rapports) |
| PV de recette | `rendus/ECOTRACK_PV_Recette.md` | #9, #10 |
| Suite de tests Pytest (58 tests) | `apiservice/tests/` | #9 |
| Documentation technique des tests | `documentation/tests/index.md` | #9 |
| Argumentaire oral NoSQL/distribué | `argumentaire/argumentaire_competence5_NoSQL_distribue.md` | #5 |
