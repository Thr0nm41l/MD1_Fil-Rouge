# BLOC 2 — Chapitre 2 : Contexte et Problématique Data

> Template sections 2.1, 2.2, 2.3

---

## 2.1 Présentation de l'organisation et de la problématique métier

### Contexte organisationnel

ECOTRACK est une plateforme de gestion intelligente des déchets urbains pour une collectivité de 500 000 habitants répartis sur 5 arrondissements (zones géospatiales). L'organisation implique plusieurs profils utilisateurs :

| Rôle | Responsabilité | Besoin data |
|---|---|---|
| **Manager** (gestionnaire de zone) | Supervise les KPIs et planifie les collectes | Carte choroplèthe, heatmap, taux de remplissage moyen |
| **Worker** (agent de collecte) | Exécute les tournées, reporte les collectes | Statut conteneur en temps réel, route optimisée |
| **Admin** | Configure les zones, les conteneurs, les seuils d'alerte | CRUD complet sur toutes les entités |
| **Citoyen** | Signale les anomalies, consulte son score de participation | Leaderboard gamification, historique signalements |

### Problématique métier

Actuellement, les collectes s'effectuent selon des plannings fixes (deux fois par semaine), indépendamment du taux de remplissage réel des conteneurs. Ce modèle génère deux inefficacités symétriques :
- **Sur-collecte** : des bennes demi-pleines mobilisent un camion
- **Sous-collecte** : des conteneurs débordants génèrent des plaintes citoyennes et des amendes

**Question analytique centrale :**

> *Dans quelle mesure les données historiques de remplissage (séries temporelles IoT) permettent-elles de prédire le niveau de remplissage à horizon 24 heures avec une précision suffisante (R² ≥ 0.65) pour déclencher des tournées conditionnelles ?*

La réponse positive (CV R² = 0.673 sur le modèle `hgb_v1.0`) démontre la faisabilité d'une collecte à la demande (on-demand collection) réduisant le kilométrage estimé de 20 %.

---

## 2.2 Description des données disponibles

### Inventaire des sources de données

| Source | Type | Volume | Fréquence | Format | Qualité observée |
|---|---|---|---|---|---|
| `fill_history` | Structurée — série temporelle IoT | 1,44 M lignes / 30 jours (~18 M/an) | Toutes les 10 min | PostgreSQL table partitionnée | ~99 % valides (1 % `is_outlier`) |
| `containers` | Structurée — référentiel géospatial | 2 000 enregistrements | Statique (mise à jour sur événement) | PostgreSQL, GEOMETRY(Point, 4326) | 100 % complets |
| `zones` | Structurée — polygones géographiques | 5 zones | Statique | PostgreSQL, GEOMETRY(Polygon, 4326) | 100 % complets |
| `collections` | Structurée — événements de collecte | Variable (opérationnel) | Sur événement | PostgreSQL | Dépend du DAG `lasc__ops_containers` |
| `signalements` | Structurée — incidents citoyens | Variable | Sur événement | PostgreSQL | 100 % valides (contraintes SQL) |
| `aggregated_hourly/daily_stats` | Structurée — OLAP agrégée | ~48 K lignes / jour | Toutes les 10 min (recalcul incremental) | PostgreSQL | Dérivée de `fill_history` (qualité héritée) |

### Caractérisation des données selon les 4V

| Dimension | Valeur ECOTRACK |
|---|---|
| **Volume** | 1,44 M lignes historiques (30 j) ; ~288 K nouvelles mesures par jour ; 2,26 M lignes utilisées pour le ML |
| **Variété** | Séries temporelles numériques + géométries PostGIS (Point, Polygon, LineString) + texte (signalements, descriptions) |
| **Vélocité** | Ingestion toutes les 10 min (`lasc__livesim_fill`), propagation immédiate via triggers SQL |
| **Véracité** | Données synthétiques simulées — 1 % outliers intentionnels, contraintes CHECK sur `fill_rate ∈ [0, 100]` |

### Contraintes RGPD

Les données à caractère personnel sont restreintes à la table `users` (email, nom, prénom, mot de passe bcrypt). Les mesures IoT sont anonymisées — `fill_history` référence un `container_id` sans lien direct avec une personne physique.

**Mesures de conformité implémentées :**
- Mots de passe stockés en bcrypt (DAG `lasc__seed_data`, `pwd_context.hash()`)
- Row Level Security (RLS) sur `users`, `signalements`, `notifications`, `user_role` — chaque utilisateur ne voit que ses propres données
- `SET LOCAL app.user_id` injecté dans le context PostgreSQL via `set_user_context(conn, user_id)` avant chaque requête sensible (`apiservice/db.py`)

---

## 2.3 Choix du paradigme data et justification

### Comparaison des paradigmes

| Paradigme | Forces | Faiblesses | Adéquation ECOTRACK |
|---|---|---|---|
| **Data Warehouse** | Schéma strict, requêtes analytiques rapides, gouvernance forte | Rigidité du schéma, pas adapté aux données brutes, coût élevé | Partiellement — les tables OLAP (`aggregated_*`) correspondent à la logique DW |
| **Data Lake** | Flexibilité (tous formats), faible coût stockage, ML-friendly | Gouvernance difficile (data swamp), latence analytique | Partiellement — `fill_history` (raw, partitionnée) correspond à la Bronze Layer |
| **Data Lakehouse** | Combine DW (requêtes SQL directes) et Data Lake (données brutes), ACID, ML | Complexité opérationnelle (Delta Lake, Iceberg) | Architecture adoptée — PostgreSQL natif joue le rôle de Lakehouse |

### Architecture Lakehouse sur PostgreSQL — Justification

Le projet implémente un **Lakehouse natif PostgreSQL** sans framework Delta Lake ni Apache Iceberg, pour trois raisons :

**1. Adéquation au volume :** Delta Lake est optimal pour des volumes > 1 TB stockés en Parquet. Sur 18 M lignes/an (~2 Go), les performances PostgreSQL avec partitionnement natif sont équivalentes — les requêtes série temporelle sur `fill_history` s'exécutent en < 100 ms grâce au partition pruning et à l'index composite `(container_id, measured_at DESC)`.

**2. Unified storage :** PostgreSQL héberge simultanément les données brutes (`fill_history`), les agrégats (`aggregated_*_stats`), les prédictions ML (`ml_predictions`) et les métadonnées (`containers`, `zones`). Cette unification évite la fragmentation multi-stack (MinIO + TimescaleDB + PostgreSQL) et maintient la cohérence ACID sur l'ensemble du périmètre.

**3. Contrainte CDC :** Le cahier des charges (`context/master1_data_tasks.md`, tâche `BDD5`) impose PostgreSQL 15 + PostGIS. L'introduction d'un Data Lake objet (MinIO + Parquet) en parallèle aurait dupliqué la source de vérité sans bénéfice fonctionnel.

### Mapping couches Lakehouse → tables PostgreSQL

| Couche Lakehouse | Implémentation PostgreSQL | Rôle |
|---|---|---|
| **Bronze** (raw, immutable) | `fill_history` PARTITION BY RANGE (measured_at) | Données brutes IoT, `is_outlier` flag, jamais modifiées |
| **Silver** (cleaned, enriched) | `WHERE NOT is_outlier` dans les procédures + JOIN `containers/zones` | Filtrage et enrichissement implicite à l'agrégation |
| **Gold** (aggregated, business-ready) | `aggregated_hourly_stats`, `aggregated_daily_stats`, `ml_predictions` | KPIs pré-calculés, exposition API directe |

---

*Sources : `database/setup_complete.sql`, `context/master1_data_tasks.md`, `dags/lasc__seed_data.py`, `apiservice/db.py`*
