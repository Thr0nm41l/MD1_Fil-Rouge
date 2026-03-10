# Epics — Master 1 Data (ECOTRACK)

115 tâches réparties en 10 epics fonctionnels.

---

## Récapitulatif

| Epic | Intitulé                                | Tâches       | Semaines cibles |
|------|-----------------------------------------|--------------|-----------------|
| E1   | Fondations Data & Infrastructure BDD    | 6            | S1–2            |
| E2   | Modélisation Géospatiale (PostGIS)      | 10           | S1–2            |
| E3   | Gestion des Conteneurs & Zones          | 25           | S3–5            |
| E4   | Ingestion IoT & Historique Remplissage  | 8            | S3–4            |
| E5   | Pipeline ETL & Qualité des Données      | inclus E1/E4 | S3–4            |
| E6   | Analytics & DataViz Avancés             | 10           | S5–8            |
| E7   | Dashboard & Rapports Automatisés        | 14           | S7–10           |
| E8   | Optimisation des Tournées (couche Data) | 10           | S5–8            |
| E9   | Gamification & Leaderboard              | 11           | S6–9            |
| E10  | Machine Learning Prédictif              | 5            | S9–12           |
| E11  | Tests, Qualité & Documentation          | 7            | S13–16          |


**Total 115**

---

## EPIC 1 — Fondations Data & Infrastructure BDD

**Objectif :** Mettre en place la base PostgreSQL + PostGIS et concevoir le schéma de données (OLTP + OLAP).

**Tâches (6) :**

| ID   | Tâche | Critère de validation |
|------|-------|-----------------------|
| BDD1 | Création base PostgreSQL et activation de l'extension PostGIS | `SELECT PostGIS_Version();` retourne un résultat |
| BDD2 | Conception et création des tables OLTP (`containers`, `zones`, `routes`, `users`, `signalements`) | Scripts DDL sans erreur, toutes les FK présentes |
| BDD3 | Conception du Data Warehouse star schema (table de faits `fill_history` + dimensions `dim_time`, `dim_container`, `dim_zone`) | Schéma validé, requêtes analytiques fonctionnelles |
| BDD4 | Création des tables OLAP agrégées (`aggregated_daily_stats`, `ml_predictions`) | Données accessibles en < 50ms |
| BDD5 | Partitionnement de `fill_history` par mois | `EXPLAIN` montre l'usage du partitionnement |
| BDD6 | Stratégie d'indexation globale : index B-tree sur colonnes temporelles, index GIST sur colonnes géométriques | `EXPLAIN ANALYZE` confirme l'usage des index |

---

## EPIC 2 — Modélisation Géospatiale (PostGIS)

**Objectif :** Maîtriser la modélisation et les requêtes spatiales avec PostGIS.

**Tâches (10) :**

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| G1 | Installation et configuration de PostGIS | `SELECT PostGIS_Version();` retourne un résultat |
| G2 | Migration des positions lat/lng en `GEOMETRY(Point, 4326)` | Toutes les positions des conteneurs migrées (SRID 4326) |
| G3 | Migration des zones en `GEOMETRY(Polygon, 4326)` | Tous les polygones de zones migrés |
| G4 | Création des index spatiaux GIST sur toutes les colonnes géométriques | `EXPLAIN` confirme l'utilisation des index GIST |
| G5 | Implémentation de `ST_Distance` — distance entre conteneurs | Résultat en mètres, précis avec cast `::geography` |
| G6 | Implémentation de `ST_Within` — conteneurs dans un polygone de zone | Tous les conteneurs d'une zone retournés correctement |
| G7 | Implémentation de `ST_DWithin` — conteneurs dans un rayon | Conteneurs dans 1 km retournés, index utilisé |
| G8 | Implémentation de `ST_Buffer` — zone tampon autour d'un point | Buffer de 500 m fonctionnel |
| G9 | Optimisation des requêtes spatiales avec `EXPLAIN ANALYZE` | Toutes les requêtes spatiales < 200 ms pour 2 000 conteneurs |
| G10 | Tests de performance et benchmark des requêtes spatiales | Rapport de performances produit |

**Fonctions à maîtriser :** `ST_Distance`, `ST_Within`, `ST_DWithin`, `ST_Buffer`, `ST_Intersects`, `ST_Area`, `ST_Centroid`, `ST_MakePoint`, `ST_GeomFromGeoJSON`

---

## EPIC 3 — Gestion des Conteneurs & Zones

**Objectif :** Exposer les données des conteneurs et zones via l'API, avec filtres avancés, import/export et opérations spatiales.

### Conteneurs (20 tâches)

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| C1 | `GET /containers` — liste paginée avec filtres (zone, type, statut, taux) | Réponse < 200ms, pagination correcte |
| C2 | `GET /containers/:id` — détail conteneur + dernière mesure IoT | Données complètes retournées |
| C3 | `POST /containers` — création avec coordonnées GPS (converties en GEOMETRY) | Conteneur inséré avec `GEOMETRY(Point, 4326)` |
| C4 | `PUT /containers/:id` — modification (position, type, capacité, seuils) | Mise à jour persistée |
| C5 | `DELETE /containers/:id` — suppression logique (soft delete) | Conteneur marqué inactif, non supprimé physiquement |
| C6 | `GET /containers/map` — données GeoJSON pour carte Leaflet | Format GeoJSON valide, toutes les propriétés présentes |
| C7 | Import batch de conteneurs depuis CSV/JSON (avec validation) | Rapport d'import : succès, erreurs, doublons |
| C8 | Export conteneurs en CSV et GeoJSON | Fichiers téléchargeables avec données complètes |
| C9 | Filtres avancés : zone, type de déchet, statut, taux de remplissage min/max | Combinaisons de filtres fonctionnelles |
| C10 | `GET /containers/:id/history` — série temporelle des mesures | Données triées par date, filtrable par période |
| C11 | `GET /containers/critical` — conteneurs avec taux > seuil configurable | Liste retournée avec taux en temps réel |
| C12 | `POST /containers/:id/measures` — ingestion d'une mesure IoT | Mesure validée et insérée dans `fill_history` |
| C13 | Validation et normalisation des données entrantes (valeurs 0–100%, timestamps) | Données aberrantes rejetées avec message d'erreur |
| C14 | Déduplication des mesures IoT (même capteur, même minute) | Aucun doublon dans `fill_history` |
| C15 | Détection et traitement des valeurs aberrantes (outliers) | Valeurs hors plage ignorées ou flagguées |
| C16 | Calcul automatique du statut conteneur (vide / normal / plein / critique) | Statut recalculé à chaque mesure |
| C17 | Système d'alertes automatiques au dépassement de seuil | Alerte générée si taux > seuil configuré par type |
| C18 | `GET /containers/stats` — statistiques globales (moyenne, médiane, taux débordement) | KPIs corrects et cohérents |
| C19 | Clustering spatial des conteneurs par zone dense (densité/km²) | Clusters calculés via `ST_Area` + `COUNT` |
| C20 | Mise en cache Redis des données de remplissage temps réel | TTL configuré, cache invalidé à chaque nouvelle mesure |

### Zones géographiques (5 tâches)

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| Z1 | `CRUD /zones` — création avec polygone GeoJSON, modification, suppression | Polygone stocké en `GEOMETRY(Polygon, 4326)` |
| Z2 | `GET /zones/:id/containers` — conteneurs d'une zone via `ST_Within` | Liste correcte, index GIST utilisé |
| Z3 | `GET /zones/stats` — statistiques par zone (nb conteneurs, taux moyen, débordements) | Statistiques agrégées correctes |
| Z4 | Affectation automatique conteneur → zone lors de la création (`ST_Within`) | Zone déduite automatiquement depuis la position GPS |
| Z5 | `GET /zones/density` — densité de conteneurs par zone (conteneurs/km²) | Calcul via `COUNT(*) / ST_Area(polygon::geography)` |

---

## EPIC 4 — Ingestion IoT & Historique Remplissage

**Objectif :** Stocker, agréger et rendre exploitable l'historique complet des mesures IoT (500 000 mesures/jour, 12 mois).

**Tâches (8) :**

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| H1 | Table `fill_history` partitionnée par mois avec index B-tree sur `measured_at` | Requêtes sur période < 100ms |
| H2 | Pipeline d'ingestion IoT : réception → validation → insertion dans `fill_history` | Latence < 500ms par mesure |
| H3 | Agrégation horaire automatique (batch toutes les heures) | Table `aggregated_hourly_stats` alimentée |
| H4 | Agrégation journalière automatique (batch quotidien) | Table `aggregated_daily_stats` alimentée |
| H5 | `GET /history/:container_id` — série temporelle avec filtres de période | Données correctes, format exploitable pour graphiques |
| H6 | Détection de patterns temporels (heures et jours de pic de remplissage) | Rapport de patterns produit (SQL window functions) |
| H7 | `GET /history/heatmap-data` — données groupées par `(day_of_week, hour)` pour heatmap | Format `{day, hour, count}` prêt pour Nivo/D3.js |
| H8 | Stratégie d'archivage des données > 12 mois (partitions détachées ou table archive) | Espace disque maîtrisé, données accessibles |

---

## EPIC 5 — Pipeline ETL & Qualité des Données

> Cet epic est transversal : ses tâches sont intégrées dans E1 (BDD) et E4 (Ingestion IoT). Il représente l'ensemble des processus **Extract → Transform → Load** du projet.

**Périmètre fonctionnel :**

| Étape | Responsabilité | Tâches associées |
|-------|---------------|-----------------|
| **Extract** | Collecte depuis capteurs IoT (MQTT/HTTP), API REST, imports CSV | H2, C7 |
| **Transform** | Validation, nettoyage, déduplication, détection outliers, normalisation | C13, C14, C15, H3, H4 |
| **Load** | Insertion OLTP + alimentation DW + agrégats | BDD3, BDD4, H1, H3, H4 |

**Outils :** scripts Python (Pandas), Airflow pour l'orchestration, Pytest pour les tests de qualité.

---

## EPIC 6 — Analytics & DataViz Avancés

**Objectif :** Produire 10 types de visualisations couvrant l'ensemble des dimensions métier.

**Tâches (10) :**

| ID | Graphique | Type | Bibliothèque | Critère |
|----|-----------|------|-------------|---------|
| A1 | Évolution du volume collecté par type de déchet | Aires empilées | Recharts | Séries par type, tooltip, légende cliquable |
| A2 | Répartition par type de déchet | Donut | Chart.js | Pourcentages + valeurs absolues, highlight survol |
| A3 | Nombre de collectes par zone | Bar horizontal | Chart.js | Trié par volume, filtrable par période |
| A4 | Distribution des taux de remplissage | Histogramme | Chart.js | Intervalles de 10%, courbe de densité |
| A5 | Évolution du taux de remplissage moyen | Line chart | Recharts | Moyenne mobile 7 jours en option |
| A6 | Performance des tournées (distance vs volume) | Scatter plot | Recharts | Bulle = nb conteneurs, axes configurables |
| A7 | Incidents et alertes dans le temps | Timeline | Custom / D3.js | Filtrable par type d'incident |
| A8 | Heatmap collectes par jour × heure | Heatmap | Nivo / D3.js | Axe X = heure (0–23h), Y = jour (Lun–Dim), dégradé blanc→rouge |
| A9 | Carte choroplèthe — densité par zone | Carte choroplèthe | Leaflet | Dégradé vert→rouge, popup au clic avec stats |
| A10 | Analyse coûts et ROI | Mixed chart (bar + line) | Recharts | Coûts en barres, économies en ligne |

**Endpoints API à créer :**

| Endpoint | Données retournées |
|----------|--------------------|
| `GET /analytics/volume-evolution` | Séries temporelles par type de déchet |
| `GET /analytics/type-distribution` | Répartition % par type |
| `GET /analytics/zone-collections` | Collectes par zone |
| `GET /analytics/fill-distribution` | Distribution des taux |
| `GET /analytics/heatmap` | Matrice `(day_of_week × hour, count)` |
| `GET /analytics/choropleth` | Densité conteneurs/km² par zone |
| `GET /analytics/costs-roi` | Coûts, distances, économies estimées |
| `GET /analytics/kpis` | 6 KPIs principaux avec variations vs période précédente |

---

## EPIC 7 — Dashboard & Rapports Automatisés

**Objectif :** Fournir un dashboard analytics interactif et un générateur de rapports PDF/Excel.

### Dashboard personnalisable (6 tâches)

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| DA1 | Structure du dashboard analytics principal (grille responsive 2×4) | Layout correct sur desktop et tablette |
| DA2 | Date picker global et sélecteur de période (7j / 30j / 3m / custom) | Tous les graphiques se mettent à jour |
| DA3 | 6 KPI cards avec valeur, unité et variation vs période précédente | Données correctes, variation en % colorée |
| DA4 | Personnalisation du layout — choix des graphiques à afficher | Préférences sauvegardées en base |
| DA5 | Sauvegarde de la configuration par utilisateur (gestionnaire) | Configuration restaurée à la reconnexion |
| DA6 | Export snapshot du dashboard en PDF | PDF généré avec tous les graphiques visibles |

### Rapports automatisés (8 tâches)

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| R1 | Générateur de rapport mensuel PDF (structure + graphiques intégrés) | PDF lisible, graphiques inclus |
| R2 | Générateur de rapport hebdomadaire Excel (données brutes + onglets) | Fichier .xlsx valide, données cohérentes |
| R3 | Contenu rapport : KPIs, évolutions, top zones, incidents, comparaison N-1 | Toutes les sections présentes |
| R4 | `POST /reports/generate` — déclenchement à la demande | Rapport généré < 30s |
| R5 | Stockage des rapports générés et endpoint de téléchargement | Fichiers persistants, lien de téléchargement stable |
| R6 | Calcul automatisé de l'analyse coûts et ROI | Formules : coût/km, économies tournées optimisées |
| R7 | Rapport par zone géographique (performance par secteur) | Données segmentées par zone |
| R8 | Rapport performance tournées (distance, durée, nb collectes, taux remplissage moyen) | Métriques calculées depuis l'historique |

---

## EPIC 8 — Optimisation des Tournées (couche Data)

**Objectif :** Modéliser les tournées, exposer les données nécessaires à l'optimisation et calculer les KPIs de performance.

**Tâches (10) :**

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| T1 | Modélisation table `routes` avec trajet `GEOMETRY(LineString, 4326)` et étapes ordonnées | Schéma DDL valide, données géométriques insérées |
| T2 | `GET /routes` — liste des tournées avec filtres (date, zone, agent, statut) | Réponse paginée < 200ms |
| T3 | `GET /routes/:id` — détail tournée avec conteneurs ordonnés et géométrie | GeoJSON du trajet retourné |
| T4 | Calcul des distances optimales entre conteneurs (`ST_Distance`) | Distances en mètres, cohérentes avec Google Maps |
| T5 | Sélection des conteneurs à collecter selon seuil de remplissage configurable (défaut 70%) | Seuls les conteneurs > seuil inclus |
| T6 | `POST /routes/:id/export` — export feuille de route PDF/JSON pour agents | Document lisible avec ordre, adresses, distances |
| T7 | Enregistrement des collectes effectuées (horodatage, agent, volume réel) | Traçabilité complète dans `fill_history` |
| T8 | `GET /routes/stats` — performance globale (distance totale, collectes, débordements évités) | KPIs corrects sur la période sélectionnée |
| T9 | Calcul des KPIs par tournée : distance parcourue, durée, nb conteneurs, volume collecté | Calculés depuis les données terrain |
| T10 | Analyse comparative avant/après optimisation (distance économisée, CO₂) | Réduction distance mesurable (objectif : -20%) |

---

## EPIC 9 — Gamification & Leaderboard

**Objectif :** Modéliser et exposer le système de points, badges, défis et classements pour les 15 000 citoyens.

**Tâches (11) :**

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| GAM1 | Modèle de données gamification (`user_points`, `badges`, `user_badges`, `defis`, `defi_participations`) | Schéma DDL valide, relations correctes |
| GAM2 | Système de points : règles d'attribution (+10 pts signalement, +5 pts action éco, etc.) | Points crédités automatiquement après action |
| GAM3 | `GET /leaderboard` — classement global (top 100 citoyens par points) | Trié par points, inclut rang et pseudo |
| GAM4 | `GET /leaderboard/weekly` et `/monthly` — classements périodiques | Données filtrées sur la bonne période |
| GAM5 | Catalogue de badges défini (30+ badges : premiers signalements, streaks, zones, etc.) | Liste complète avec conditions d'obtention |
| GAM6 | Attribution automatique des badges via triggers SQL ou batch | Badge attribué dans la minute suivant la condition |
| GAM7 | `GET /users/:id/badges` — badges obtenus et progression vers les suivants | Données complètes, progression calculée |
| GAM8 | Système de défis : création, inscription, suivi de progression | Défi créé, inscriptions enregistrées |
| GAM9 | `GET /defis` — liste des défis actifs avec progression collective | Données temps réel, barre de progression |
| GAM10 | Calcul et attribution automatique des récompenses en fin de défi | Récompenses attribuées dans les 24h après la fin |
| GAM11 | `GET /users/:id/impact` — impact environnemental citoyen (CO₂ économisé, signalements, points) | Calcul cohérent avec les données terrain |

---

## EPIC 10 — Machine Learning Prédictif

**Objectif :** Prédire le taux de remplissage des conteneurs à 24h pour anticiper les débordements.

**Tâches (5) :**

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| ML1 | Feature engineering : création de 8+ variables prédictives (temporelles, lag, rolling, conteneur) | 8+ features créées et documentées dans un notebook |
| ML2 | Implémentation de 2 modèles : `LinearRegression` et `RandomForestRegressor` (Scikit-learn) | Les deux modèles entraînés et comparés |
| ML3 | Entraînement avec split train/test 80/20, cross-validation | Modèles entraînés, pas de data leakage |
| ML4 | Évaluation et comparaison des modèles (RMSE, MAE, R²) + graphiques d'évaluation | R² > 0.65 pour le meilleur modèle |
| ML5 | `POST /api/ml/predict` — endpoint de prédiction (container_id + horizon) | Temps de réponse < 100ms, format JSON |

**Features à créer :**

| Catégorie | Features |
|-----------|----------|
| Temporelles | `hour`, `day_of_week`, `day_of_month`, `is_weekend`, `is_peak_hour` |
| Lag | `fill_rate_1h_ago`, `fill_rate_24h_ago`, `fill_rate_7d_ago` |
| Rolling | `fill_rate_24h_avg`, `fill_rate_7d_avg`, `fill_rate_change_rate` |
| Conteneur | `capacity`, `type_encoded`, `zone_density` |

**Métriques cibles :** RMSE < 10%, MAE < 7%, R² > 0.65

---

## EPIC 11 — Tests, Qualité & Documentation

**Objectif :** Garantir la fiabilité du code et produire la documentation attendue en soutenance.

### Tests data (3 tâches)

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| TEST1 | Tests unitaires Python (Pytest) des fonctions ETL, ML et analytics | Couverture > 50%, tous les tests passent |
| TEST2 | Tests d'intégration des endpoints API analytics | Tous les endpoints répondent avec le bon format |
| TEST3 | Tests de performance SQL : benchmark des requêtes principales | Toutes les requêtes < 200ms sur jeu de données complet |

### Documentation (4 tâches)

| ID | Tâche | Critère de validation |
|----|-------|-----------------------|
| DOC1 | DCT Data (25–30 pages) : architecture, modèle de données, algorithmes ML, choix techniques | Document complet, relu et validé |
| DOC2 | Dictionnaire de données : toutes les tables documentées (colonnes, types, descriptions) | 100% des tables couvertes |
| DOC3 | Notebooks Jupyter : EDA, entraînement ML, visualisations exploratoires | Notebooks exécutables, commentés |
| DOC4 | Documentation pipeline ETL et data lineage (flux de données source → destination) | Schéma de flux + description des transformations |

---

## Répartition par Sprint (indicative)

| Sprint   | Semaines | Epics                    | Jalons                                                |
|----------|----------|--------------------------|-------------------------------------------------------|
| Sprint 0 | S1–2     | E1, E2                   | Architecture validée, PostGIS opérationnel            |
| Sprint 1 | S3–4     | E3 (conteneurs), E4      | Pipeline ingestion IoT fonctionnel                    |
| Sprint 2 | S5–6     | E3 (zones), E8, début E9 | API données complète, tournées                        |
| Sprint 3 | S7–8     | E6, E7 (dashboard)       | 8 graphiques + heatmap + choroplèthe — **Livrable 3** |
| Sprint 4 | S9–10    | E10 (ML), E9 (gamif.)    | Modèle ML entraîné (R² > 0.65)                        |
| Sprint 5 | S11–12   | E7 (rapports), E9 (fin)  | Rapports PDF/Excel, API prédiction — **Livrable 4**   |
| Sprint 6 | S13–16   | E11                      | Tests, optimisation, DCT Data, soutenance             |
