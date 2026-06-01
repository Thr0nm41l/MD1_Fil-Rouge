# PROJET ECOTRACK — M1 DATA & ANALYTICS
> Extraction des sections filière **🟢 M1 DATA & ANALYTICS (RNCP 38822)** issues des 6 templates BLOC 1.

---

## DOCUMENT 1 — ÉTUDE DE FAISABILITÉ

### II. FAISABILITÉ TECHNIQUE DATA

> **Critères RNCP Ce1.1.2 / A1.3 :** Analyse contraintes techniques et faisabilité

#### A. Architecture Data Lake
- **Storage :** MinIO (S3-compatible) pour 180M mesures/an (~50 GB/an)
- **Bronze Layer :** Données brutes JSON/Parquet
- **Silver Layer :** Données nettoyées + validation qualité
- **Gold Layer :** Agrégats + KPIs pré-calculés

#### B. Pipeline ETL / Streaming
- **Streaming :** Apache Kafka pour ingestion temps réel (< 2s latence)
- **Processing :** Apache Spark 3.5 pour traitement batch (nuit)
- **Orchestration :** Apache Airflow pour DAGs (7 pipelines quotidiens)
- **Validation :** Pydantic + Great Expectations (qualité > 95%)

#### C. Base de Données Analytique
- **TimescaleDB :** Extension PostgreSQL pour séries temporelles
- **Hypertables :** Partitionnement automatique par date
- **Compression :** Réduction 90% après 7 jours
- **Rétention :** 2 ans données brutes, 5 ans agrégats

#### D. Visualisation et BI
- **Dashboards :** Apache Superset OU Metabase (open-source)
- **Rapports :** Pandas + Matplotlib pour exports PDF
- **API Analytics :** FastAPI + cache Redis (requêtes < 100ms)

---

## DOCUMENT 2 — VEILLE TECHNOLOGIQUE

### II. COMPARAISON DES TECHNOLOGIES DATA

> **Critères RNCP Ce1.2.2 / A1.2 :** Analyse comparative objective

#### A. Traitement Batch : Apache Spark vs Dask vs Ray

Tableau comparatif — critères × note /10 :

| Critère | Spark | Dask | Ray |
|---|---|---|---|
| Performance (scalabilité horizontale) | /10 | /10 | /10 |
| API Python (compatibilité Pandas) | /10 | /10 | /10 |
| Écosystème (Kafka, S3, ML) | /10 | /10 | /10 |
| Déploiement (complexité cluster) | /10 | /10 | /10 |
| Coût (ressources + licences) | /10 | /10 | /10 |
| **TOTAL** | **/50** | **/50** | **/50** |

> **CHOIX RECOMMANDÉ :** [Spark / Dask / Ray] — à justifier

#### B. Streaming : Apache Kafka vs Apache Pulsar vs RabbitMQ

Critères : Débit, Latence, Durabilité, Complexité, Communauté
Focus cas ECOTRACK : 180M mesures/an, latence < 2s

| Critère | Kafka | Pulsar | RabbitMQ |
|---|---|---|---|
| Débit | /10 | /10 | /10 |
| Latence | /10 | /10 | /10 |
| Durabilité | /10 | /10 | /10 |
| Complexité | /10 | /10 | /10 |
| Communauté | /10 | /10 | /10 |
| **TOTAL** | **/50** | **/50** | **/50** |

> **CHOIX RECOMMANDÉ :** [Kafka / Pulsar / RabbitMQ] — à justifier

#### C. Visualisation : Apache Superset vs Metabase vs Grafana

Critères : Facilité dashboards, Connecteurs BDD, Performance, Coût
Pour dashboards analytics temps réel

| Critère | Superset | Metabase | Grafana |
|---|---|---|---|
| Facilité création dashboards | /10 | /10 | /10 |
| Connecteurs BDD | /10 | /10 | /10 |
| Performance | /10 | /10 | /10 |
| Coût | /10 | /10 | /10 |
| Communauté | /10 | /10 | /10 |
| **TOTAL** | **/50** | **/50** | **/50** |

> **CHOIX RECOMMANDÉ :** [Superset / Metabase / Grafana] — à justifier

---

### III.B. TENDANCES DATA & ANALYTICS 2025

1. **Data Lakehouses (Delta Lake, Apache Iceberg)** : Fusion Data Lake + Data Warehouse
   → Impact ECOTRACK : Requêtes SQL directes sur Data Lake

2. **DataOps et MLOps** : Automatisation pipelines data/ML
   → Impact : CI/CD pour pipelines, versioning datasets

3. **Real-time Analytics (Flink, Materialize)** : Analytics sans pré-agrégation
   → Impact : Dashboards temps réel avec latence minimale

4. **Data Quality Observability (Great Expectations, Monte Carlo)** : Détection anomalies automatique
   → Impact : Alertes proactives sur dégradation qualité données

---

## DOCUMENT 3 — ARCHITECTURE LOGICIELLE

### II. ARCHITECTURE DATA LAKE & PIPELINES

> **Critères RNCP Ce1.3.1 / A2.1 :** Architecture complète et cohérente

#### A. Architecture Data Lake (3 Layers)

**1. Bronze Layer (Raw Data)**
- **Storage :** MinIO (S3-compatible), 100 GB initial
- **Format :** JSON + Parquet (columnar)
- **Partitionnement :** `/year=2025/month=01/day=15/`
- **Rétention :** Données brutes 2 ans

**2. Silver Layer (Cleaned Data)**
- **Nettoyage :** doublons supprimés, valeurs aberrantes filtrées
- **Validation :** Great Expectations (qualité > 95%)
- **Enrichissement :** coordonnées GPS → adresse + données météo
- **Format :** Delta Lake (ACID transactions)

**3. Gold Layer (Aggregated Data)**
- **Agrégats :** KPIs pré-calculés (par heure, jour, semaine)
- **Stockage :** TimescaleDB (requêtes SQL rapides)
- **Marts :** `taux_remplissage`, `tournees_optimisees`, `incidents`
- **Rétention :** 5 ans agrégats

#### B. Architecture Pipeline ETL

**1. Streaming Pipeline (Temps Réel)**
- **Ingestion :** Apache Kafka (3 brokers, replication factor 2)
- **Topics :** `iot_measurements`, `alerts`, `events`
- **Processing :** Spark Structured Streaming
- **Latence cible :** < 2s end-to-end
- **Sink :** TimescaleDB + S3 Bronze Layer

**2. Batch Pipeline (Nuit)**
- **Orchestration :** Apache Airflow (7 DAGs quotidiens)
- **Processing :** Apache Spark 3.5 (cluster 3 workers)
- **Tâches :** Bronze → Silver (2h) | Silver → Gold (1h) | Rapports (30 min)
- **Monitoring :** Alertes Airflow si échec

#### C. Architecture Serving

**1. API Analytics (FastAPI)**
- **Endpoints :** `/metrics`, `/trends`, `/predictions`
- **Cache Redis :** Requêtes fréquentes, TTL 5 min
- **Performance cible :** < 100ms P95

**2. Dashboards BI**
- **Outil :** Apache Superset (ou Metabase)
- **Connexion :** TimescaleDB (Gold Layer)
- **Dashboards :** Opérationnel, Stratégique, Technique
- **Refresh :** Toutes les 5 minutes

#### D. Data Quality & Observability
- **Validation :** Great Expectations (tests qualité automatisés quotidiens)
- **Monitoring :** Alertes si qualité < 95%
- **Lineage :** Tracking origine données Bronze → Silver → Gold
- **Profiling :** Statistiques descriptives automatiques

---

## DOCUMENT 4 — MODÉLISATION

> Ce template est **commun à toutes les filières**. Il n'y a pas de section spécifique DATA & Analytics — vous choisissez **une seule méthode** parmi :
>
> - **BPMN 2.0** → modéliser les processus métier (remontée alerte, optimisation tournée)
> - **UML** → modéliser l'architecture orientée objet (classes, séquences, use cases)
> - **MERISE** → modéliser les données relationnelles (MCD, MLD, MPD avec PostGIS)
>
> **Recommandation filière DATA :** MERISE (MCD/MLD/MPD) ou UML pour représenter le modèle de données analytique.

---

## DOCUMENT 5 — PLANIFICATION AGILE

### II. USER STORIES DATA & ANALYTICS

> **Critères RNCP Ce1.4.1 / A1.4**

| ID | User Story | Priorité | SP |
|---|---|---|---|
| US-001 | En tant que Data Analyst, je veux visualiser les tendances de remplissage sur 6 mois afin d'optimiser les ressources | MUST | 8 |
| US-002 | En tant que Système, je veux ingérer 180M mesures/an sans perte afin de garantir l'intégrité des données | MUST | 13 |
| US-003 | En tant que Pipeline, je veux nettoyer les données avec > 95% de qualité afin de fiabiliser les analyses | MUST | 8 |
| US-004 | En tant que Dashboard, je veux afficher les KPIs temps réel (< 2s latence) afin d'aider la décision | SHOULD | 5 |

> **À compléter jusqu'à 15-20 user stories.**

---

### III. PLANIFICATION PAR SPRINT (LIVRABLES DATA)

| Sprint | Semaines | Objectif | Livrables DATA |
|---|---|---|---|
| Sprint 1 | S1-S2 | Socle Technique | Data Lake MinIO + Airflow + Spark configuré |
| Sprint 2 | S3-S4 | Module IoT & Données | Pipeline Kafka → Bronze Layer opérationnel |
| Sprint 3 | S5-S6 | Interface Utilisateur | Silver Layer + premières visualisations |
| Sprint 4 | S7-S8 | Optimisation & Analytics | Gold Layer + agrégats KPIs |
| Sprint 5 | S9-S10 | Dashboard & Reporting | Superset/Metabase connecté TimescaleDB |
| Sprint 6 | S11-S12 | Application Mobile (si applicable) | API Analytics FastAPI + cache Redis |
| Sprint 7 | S13-S14 | Tests & Sécurité | Tests qualité Great Expectations + monitoring |
| Sprint 8 | S15-S16 | Déploiement & Documentation | Pipeline prod + documentation technique |

---

### V. KPIs DATA & ANALYTICS

| # | KPI | Formule | Cible | Fréquence |
|---|---|---|---|---|
| 1 | Qualité des données | (Données valides / Total) × 100 | ≥ 95% | Journalier |
| 2 | Latence pipeline | Temps ingestion → disponibilité | < 2s | Temps réel |
| 3 | Volume données traitées | Mesures/jour | 500K/jour | Journalier |
| 4 | Taux d'erreur pipeline | Échecs / Exécutions | < 1% | Journalier |
| 5 | Fraîcheur données | Délai dernière mise à jour | < 5 min | Temps réel |
| 6 | Précision modèles ML | Accuracy prédictions | ≥ 85% | Hebdo |

---

### VI. RISQUES SPÉCIFIQUES DATA

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Perte de données | Faible | Élevé | Backups 3-2-1 + réplication |
| Qualité données < 95% | Moyenne | Moyen | Validation Pydantic + alertes Great Expectations |
| Latence pipeline > 2s | Moyenne | Moyen | Optimisation Spark + caching Redis |

---

## DOCUMENT 6 — AUDIT INITIAL

### II. ANALYSE SWOT — FILIÈRE DATA

> **Critères RNCP Ce1.1.2 / A1.1 :** Analyse stratégique

#### Forces spécifiques DATA
- Pipeline robuste : Airflow + Spark
- Data Lake 3 layers structuré (Bronze / Silver / Gold)
- Outils BI performants (Superset)
- Expertise data quality (Great Expectations)

#### Faiblesses spécifiques DATA
- Latence pipeline > 2s possible sur volume élevé
- Qualité données brutes < 95% lors de la phase initiale
- Coûts stockage cloud importants (180M mesures/an)

---

### III.B. RISQUES DATA (DÉTAILLÉS)

> **Critères RNCP Ce1.5.2 / A1.5 :** Gestion des risques

**RISQUE 8 : Perte de données (corruption, suppression)**
- Probabilité : Faible | Impact : **Critique** | Criticité : ÉLEVÉE
- Mitigation : Backups automatisés 3-2-1 (3 copies, 2 médias, 1 off-site S3 Glacier), réplication BDD synchrone, snapshots S3 quotidiens, tests restore trimestriels documentés.

**RISQUE 9 : Qualité données inférieure à 95%**
- Probabilité : Moyenne | Impact : Moyen | Criticité : MOYENNE
- Mitigation : Validation Pydantic stricte en ingestion, Great Expectations tests automatisés quotidiens, alertes Slack si < 95%, pipeline nettoyage Silver Layer robuste.

**RISQUE 10 : Latence pipeline supérieure à 2s**
- Probabilité : Moyenne | Impact : Moyen | Criticité : MOYENNE
- Mitigation : Optimisation Spark (broadcast joins, partitionnement optimal), cache Redis sur agrégats fréquents, Kafka tuning (batch size 100 KB, compression Snappy), monitoring APM continu.

---

### IV.B. QUICK WINS DATA

> **Critères RNCP Ce1.4.1 / A1.4 :** Priorisation actions à fort impact

| # | Action | Effort | Impact | Bénéfice |
|---|---|---|---|---|
| QW4 | Validation Pydantic stricte sur ingestion | 4h | Élevé | Qualité données +15%, erreurs détectées à la source |
| QW5 | Partitionnement TimescaleDB par date automatique | 1 jour | Élevé | Requêtes 3× plus rapides (scan partitions ciblées) |
| QW6 | Agrégats pré-calculés (rollups horaires/quotidiens) | 1 jour | Élevé | Dashboards temps réel, latence API analytics ↓ 80% |
| QW7 | Alertes automatiques data quality (< 95%) | 4h | Moyen | Détection proactive problèmes, réaction rapide équipe data |

---

*Document généré depuis les 6 templates BLOC 1 — filière M1 DATA & ANALYTICS uniquement.*
