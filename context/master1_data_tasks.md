# Tâches Obligatoires — Master 1 Data (ECOTRACK)

**Projet :** ECOTRACK — Plateforme intelligente de gestion des déchets urbains
**Périmètre :** 115 tâches (70% du projet complet)
**Durée :** 4 mois (16 semaines)

---

## Vue d'Ensemble par Catégorie

| Catégorie                           | Tâches M1   | Priorité |
|-------------------------------------|-------------|----------|
| Infrastructure BDD                  | 6/6         | MUST     |
| PostGIS (Géospatial)                | 10/10       | **MUST** |
| CRUD Conteneurs (aspect data)       | 20/26       | MUST     |
| Zones géographiques                 | 5/5         | MUST     |
| Historique remplissage              | 8/8         | MUST     |
| Analytics avancés                   | 10/14       | **MUST** |
| Optimisation tournées (aspect data) | 10/12       | MUST     |
| Gamification (leaderboard)          | 11/15       | MUST     |
| ML prédictif                        | 5/6         | **MUST** |
| Rapports                            | 8/10        | MUST     |
| Dashboard personnalisable           | 6/7         | MUST     |
| Tests data                          | 3/5         | MUST     |
| Documentation                       | 4/5         | MUST     |
| **TOTAL**                           | **115/164** | —        |

---

## 1. PostGIS et Données Géospatiales (10 tâches)

Objectif : maîtriser la modélisation et les requêtes géospatiales avec l'extension PostGIS.

| #   | Tâche                 | Description                                               | Critère de validation                            |
|-----|-----------------------|-----------------------------------------------------------|--------------------------------------------------|
| G1  | Installation PostGIS  | Activer l'extension PostgreSQL                            | `SELECT PostGIS_Version();` retourne un résultat |
| G2  | Migration POINT       | Convertir lat/lng en `GEOMETRY(Point, 4326)`              | Toutes les positions des conteneurs migrées      |
| G3  | Migration POLYGON     | Convertir les zones en `GEOMETRY(Polygon, 4326)`          | Tous les polygones de zones migrés               |
| G4  | Index spatiaux GIST   | Créer des index GIST sur toutes les colonnes géométriques | `EXPLAIN` montre l'utilisation des index         |
| G5  | Requêtes ST_Distance  | Calculer la distance entre deux conteneurs                | Résultat retourné en mètres                      |
| G6  | Requêtes ST_Within    | Lister les conteneurs dans un polygone de zone            | Tous les conteneurs d'une zone retournés         |
| G7  | Requêtes ST_DWithin   | Lister les conteneurs dans un rayon autour d'un point     | Conteneurs dans 1 km retournés                   |
| G8  | Requêtes ST_Buffer    | Créer une zone tampon autour d'un point                   | Buffer de 500 m fonctionnel                      |
| G9  | Optimisation requêtes | Analyser et optimiser avec `EXPLAIN ANALYZE`              | Temps d'exécution < 200 ms pour 2 000 conteneurs |
| G10 | Tests de performance  | Benchmark des requêtes spatiales                          | Rapport de performances produit                  |

### Fonctions PostGIS à maîtriser

| Fonction               | Usage                                           |
|------------------------|-------------------------------------------------|
| `ST_Distance()`        | Distance entre deux géométries (en mètres)      |
| `ST_Within()`          | Tester si un point est dans un polygone         |
| `ST_DWithin()`         | Tester si une géométrie est à moins de N mètres |
| `ST_Buffer()`          | Créer une zone tampon                           |
| `ST_Intersects()`      | Tester l'intersection de deux géométries        |
| `ST_Area()`            | Calculer la surface en m²                       |
| `ST_Centroid()`        | Calculer le centre géométrique                  |
| `ST_MakePoint()`       | Créer un point depuis lat/lng                   |
| `ST_GeomFromGeoJSON()` | Importer une géométrie depuis GeoJSON           |

### Contraintes techniques

- Utiliser le SRID **4326** (WGS84 — système GPS mondial)
- Index spatiaux **GIST** obligatoires sur toutes les colonnes `GEOMETRY`
- Index **B-tree** sur toutes les colonnes temporelles
- Table `fill_history` **partitionnée par mois**

---

## 2. Analytics et DataViz Avancés (10 tâches)

Objectif : produire au minimum 8 types de visualisations avancées.

| #   | Graphique                        | Type              | Difficulté | Bibliothèque   |
|-----|----------------------------------|-------------------|------------|----------------|
| A1  | Évolution volume collecté        | Aires empilées    | Moyenne    | Recharts       |
| A2  | Répartition par type de déchet   | Donut             | Faible     | Chart.js       |
| A3  | Collectes par zone               | Bar horizontal    | Faible     | Chart.js       |
| A4  | Distribution taux de remplissage | Histogramme       | Moyenne    | Chart.js       |
| A5  | Évolution taux moyen             | Line chart        | Faible     | Recharts       |
| A6  | Performance des tournées         | Scatter plot      | Moyenne    | Recharts       |
| A7  | Incidents et alertes             | Timeline          | Élevée     | Custom / D3.js |
| A8  | Heatmap collectes jour × heure   | Heatmap           | Élevée     | Nivo / D3.js   |
| A9  | Carte choroplèthe par zone       | Carte choroplèthe | Élevée     | Leaflet        |
| A10 | Analyse coûts et ROI             | Mixed chart       | Moyenne    | Recharts       |

### Spécifications clés

**A8 — Heatmap Jour × Heure**
- Axes : X = Heure (0–23h), Y = Jour (Lun–Dim)
- Couleur : dégradé blanc → jaune → rouge selon le nombre de collectes
- Objectif : identifier les créneaux de pointe

**A9 — Carte Choroplèthe**
- Données : densité de conteneurs par zone (conteneurs/km²)
- Couleur : dégradé vert → jaune → orange → rouge
- Interaction : popup au clic sur une zone

### Structure du dashboard analytics

- **6 KPI cards** : volume, nombre de collectes, taux de remplissage moyen, coût, etc. (avec variation en %)
- **Grille 2×4** de graphiques
- **Date picker** pour filtrer la période
- Boutons : Exporter PDF, Exporter Excel, Rapport automatique

---

## 3. Machine Learning Prédictif (5 tâches)

Objectif : prédire le taux de remplissage d'un conteneur à 24 heures.

| #   | Tâche                | Description                                           | Critère de validation        |
|-----|----------------------|-------------------------------------------------------|------------------------------|
| ML1 | Feature engineering  | Créer les variables prédictives                       | 8+ features créées           |
| ML2 | Modèle de régression | Implémenter LinearRegression et RandomForestRegressor | Les deux modèles implémentés |
| ML3 | Entraînement         | Split train/test 80/20, entraîner les modèles         | Modèles entraînés            |
| ML4 | Évaluation           | Calculer RMSE, MAE, R² et comparer les modèles        | R² > 0.65                    |
| ML5 | API de prédiction    | Endpoint `POST /api/ml/predict`                       | Temps de réponse < 100 ms    |

### Features à créer (8 minimum)

**Temporelles :** `hour`, `day_of_week`, `day_of_month`, `is_weekend`, `is_peak_hour`

**Lag (valeurs passées) :** `fill_rate_1h_ago`, `fill_rate_24h_ago`, `fill_rate_7d_ago`

**Rolling (moyennes mobiles) :** `fill_rate_24h_avg`, `fill_rate_7d_avg`, `fill_rate_change_rate`

**Conteneur :** `capacity`, `type_encoded`, `zone_density`

### Métriques d'évaluation

| Métrique | Formule               | Objectif |
|----------|-----------------------|----------|
| RMSE     | √(Σ(ŷ − y)² / n)      | < 10%    |
| MAE      | Σ\|ŷ − y\| / n        | < 7%     |
| R²       | 1 − (SS_res / SS_tot) | > 0.65   |

### Graphiques d'évaluation à produire
- Courbe prédictions vs réalité (scatter plot)
- Distribution des erreurs (histogramme)
- Feature importance (bar chart)

---

## 4. Infrastructure BDD (6 tâches)

Concevoir une base de données PostgreSQL + PostGIS avec séparation OLTP / OLAP.

### Tables à implémenter

| Table                    | Type | Description                                   |
|--------------------------|------|-----------------------------------------------|
| `containers`             | OLTP | Colonne `location GEOMETRY(Point, 4326)`      |
| `zones`                  | OLTP | Colonne `polygon GEOMETRY(Polygon, 4326)`     |
| `routes`                 | OLTP | Colonne `path GEOMETRY(LineString, 4326)`     |
| `fill_history`           | OLAP | Historique temporel, **partitionné par mois** |
| `aggregated_daily_stats` | OLAP | Statistiques pré-calculées                    |
| `ml_predictions`         | OLAP | Prédictions du modèle ML                      |

---

## 5. Pipeline ETL (inclus dans les 115 tâches)

Objectif : automatiser l'ingestion et la transformation des données.

| Étape         | Description                                                                     |
|---------------|---------------------------------------------------------------------------------|
| **Extract**   | Collecte depuis capteurs IoT (MQTT/HTTP), API REST, formulaires, CSV            |
| **Transform** | Validation, nettoyage, dédoublonnage, gestion des valeurs manquantes/aberrantes |
| **Load**      | Insertion dans PostgreSQL avec contrôle de qualité                              |

---

## 6. Rapports Automatisés (8 tâches)

- Générateur de rapports **PDF** et **Excel**
- Analyse des coûts et ROI
- Export déclenché depuis le dashboard analytics

**Bibliothèques :** `reportlab` ou `pdfkit` (PDF) / `openpyxl` ou `xlsxwriter` (Excel)

---

## 7. Tests et Documentation (7 tâches)

| Catégorie                | Tâches | Critères                                                                            |
|--------------------------|--------|-------------------------------------------------------------------------------------|
| Tests Python (Pytest)    | 3      | Couverture > 50%                                                                    |
| Documentation (DCT Data) | 4      | 25–30 pages : modèle de données, algorithmes ML, dictionnaire de données, pipelines |

---

## Livrables et Jalons

| Livrable                      | Semaine | Points  | Contenu                                                                          |
|-------------------------------|---------|---------|----------------------------------------------------------------------------------|
| **L1 — Modèle Data**          | S2      | 20 pts  | MCD/MLD avec types PostGIS, script de migration, dictionnaire de données         |
| **L2 — Pipeline ETL**         | S4      | 20 pts  | Script ETL fonctionnel, rapport qualité données, documentation pipeline          |
| **L3 — Dashboards Analytics** | S8      | 35 pts  | 8 graphiques, heatmap + choroplèthe, dashboard responsive, documentation         |
| **L4 — ML + Rapports**        | S12     | 35 pts  | Modèle ML (R² > 0.65), API prédiction, générateur de rapports, notebooks Jupyter |
| **Livrable Final**            | S16     | 130 pts | Projet complet + soutenance                                                      |

---

## Grille d'Évaluation (130 points)

| Domaine                                                | Points | Seuil de validation |
|--------------------------------------------------------|--------|---------------------|
| Technique Data (PostGIS, ETL, analytics, performances) | 45 pts | ≥ 27/45 (60%)       |
| Machine Learning                                       | 20 pts | ≥ 12/20 (60%)       |
| DataViz (heatmap, choroplèthe, dashboards, UX)         | 20 pts | —                   |
| Documentation (DCT Data, dictionnaire, notebooks)      | 15 pts | —                   |
| Présentation et démo                                   | 20 pts | —                   |
| Qualité & Tests                                        | 10 pts | —                   |

**Validation globale :** note ≥ 78/130 (60%) + PostGIS opérationnel + R² > 0.65 + 8 graphiques fonctionnels

---

## Stack Technique

| Couche           | Technologies                                                         |
|------------------|----------------------------------------------------------------------|
| Base de données  | PostgreSQL 15+ + PostGIS 3.3+                                        |
| Backend / ETL    | Python 3.11+, FastAPI 0.104+ ou Flask 3.0+, Pandas 2.0+, NumPy 1.24+ |
| Machine Learning | Scikit-learn 1.3+                                                    |
| DataViz frontend | Recharts 2.8+, Chart.js 4.4+, @nivo/heatmap ou D3.js, Leaflet 1.9+   |
| Rapports         | reportlab / pdfkit (PDF), openpyxl / xlsxwriter (Excel)              |
| Tests            | Pytest                                                               |
| Notebooks        | Jupyter Lab / Google Colab                                           |

---

## Checklist Pré-Soutenance

**3 jours avant :**
- [ ] Application déployée avec dashboards accessibles
- [ ] Modèle ML entraîné et API `/predict` fonctionnelle
- [ ] DCT Data complet (25–30 pages)
- [ ] Notebooks Jupyter exportés en PDF
- [ ] Dictionnaire de données à jour
- [ ] Tests Pytest passants (couverture > 50%)

**Jour J :**
- [ ] Démonstration dashboards préparée
- [ ] Exemple de prédiction ML en direct
- [ ] Slides de présentation (20–25)
- [ ] Données de démo réalistes
