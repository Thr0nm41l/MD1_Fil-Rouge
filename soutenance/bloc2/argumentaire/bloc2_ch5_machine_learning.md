# BLOC 2 — Chapitre 5 : Machine Learning — Méthodologie et Résultats

> Template sections 5.1 à 5.4 — cadre CRISP-DM

---

## 5.1 Définition du problème ML (CRISP-DM : Business Understanding)

### Type de problème

**Régression supervisée sur séries temporelles.**

La variable cible est le `fill_rate` (taux de remplissage, %) d'un conteneur à **T+24 heures**. Il s'agit d'un problème de prévision à horizon fixe (24h), non d'un modèle de détection d'anomalies ou de classification de statut.

### Variable cible

```python
target = fill_rate à T+144 ticks   # 144 × 10 min = 24 heures
```

Construite par `g.shift(-144)` dans le notebook `01_eda_feature_engineering.ipynb` — chaque ligne du dataset prédit le niveau de remplissage 24h plus tard pour le même conteneur.

### Métrique principale : R²

Le coefficient de détermination R² est la métrique principale pour trois raisons :
1. **Interprétabilité** : R² mesure la proportion de variance expliquée — un R² = 0.673 signifie que le modèle explique 67.3 % des variations de remplissage
2. **Exigence CDC** : la tâche `ML3` du CDC impose R² ≥ 0.65
3. **Comparabilité** : R² est indépendant de l'unité (`fill_rate` en % vs. litres)

**Métriques complémentaires :**
- RMSE (Root Mean Squared Error) — pénalise les grandes erreurs
- MAE (Mean Absolute Error) — erreur moyenne en points de remplissage

### Modèle baseline

**Baseline naïf :** `fill_rate_t+24h = fill_rate_t` (prédiction = valeur actuelle). Ce modèle naïf obtient un R² ≈ 0.08 sur les données ECOTRACK (le taux de remplissage change significativement en 24h). Il constitue le plancher de référence pour justifier la valeur ajoutée du ML.

### Caractéristiques du dataset

| Paramètre | Valeur |
|---|---|
| Nombre de lignes (après nettoyage) | 2 265 488 (train+test) |
| Train rows | 1 925 664 (85 %) |
| Test rows | 339 824 (15 %) |
| Période | 2026-04-03 → 2026-05-14 (41 jours) |
| Nombre de conteneurs | 2 000 (4 000 dans les données selon metadata.json — 2 seeds + 2 générations) |
| Nombre de features | 14 |
| Déséquilibre de classes | N/A — régression |

---

## 5.2 Exploration des données (EDA) et préparation (CRISP-DM : Data Understanding + Preparation)

### Principaux enseignements de l'EDA

**Distribution du taux de remplissage :**
- `fill_rate` distribué sur [0, 100] avec une concentration autour de 40–70 % (effet des collectes à 70 %)
- Présence de valeurs à 0 % (après collecte) et proches de 100 % (avant collecte critique)
- 1 % d'outliers flaggués, exclus de l'entraînement (`WHERE NOT is_outlier`)

**Auto-corrélation :**
- Forte corrélation entre `fill_rate_t` et `fill_rate_1h_ago`, `fill_rate_24h_ago` — les features de lag portent le signal principal
- Corrélation modérée avec `fill_rate_7d_ago` — variance inter-semaine présente
- **Corrélation nulle avec les features temporelles** (`hour`, `day_of_week`, etc.) — conséquence de la simulation mécanique sans modulation heure/jour (voir §5.4 Éthique et biais)

**Valeurs manquantes :**
- Générées par les `shift()` en début de série pour chaque conteneur
- Stratégie : `dropna()` après feature engineering — les premières 1008 lignes de chaque conteneur (7 jours) sont perdues
- Impact : 2 000 conteneurs × 1008 lignes = ~2 M lignes supprimées → dataset final de 2,26 M lignes

### Feature Engineering — Pipeline de transformation

```python
df = df.sort_values(["container_id", "measured_at"])
g  = df.groupby("container_id")["fill_rate"]

# Temporelles (depuis measured_at)
df["hour"]         = df["measured_at"].dt.hour
df["day_of_week"]  = df["measured_at"].dt.dayofweek
df["day_of_month"] = df["measured_at"].dt.day
df["is_weekend"]   = (df["day_of_week"] >= 5).astype(int)
df["is_peak_hour"] = df["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)

# Lags (shift par nombre de ticks)
df["fill_rate_1h_ago"]  = g.shift(6)     # 6 × 10 min = 1h
df["fill_rate_24h_ago"] = g.shift(144)   # 144 × 10 min = 24h
df["fill_rate_7d_ago"]  = g.shift(1008)  # 1008 × 10 min = 7j

# Rolling (trailing, sans fuite future)
df["fill_rate_24h_avg"] = g.transform(
    lambda s: s.shift(1).rolling(144, min_periods=12).mean()
)
df["fill_rate_7d_avg"] = g.transform(
    lambda s: s.shift(1).rolling(1008, min_periods=144).mean()
)
df["fill_rate_change_rate"] = g.transform(
    lambda s: (s - s.shift(6)) / 6
)

# Enrichissement conteneur + zone
df = df.merge(df_zones, on="zone_id")
df["density_km2"] = df["density_km2"].fillna(0)

# Variable cible
df["target"] = g.shift(-144)
```

### Split train/test — Respect de l'ordre temporel

```python
df = df.sort_values("measured_at")
split_idx = int(len(df) * 0.85)
df_train = df.iloc[:split_idx]   # 2026-04-03 → ~2026-05-09
df_test  = df.iloc[split_idx:]   # ~2026-05-09 → 2026-05-14
```

**Pourquoi 85/15 et non 80/20 :** le split temporel sur 41 jours ne laisse que ~6 jours en test avec 80 %. 85/15 donne ~6,2 jours, suffisant pour évaluer la généralisabilité sans trop réduire l'entraînement.

**Absence de random split :** un split aléatoire sur des séries temporelles constitue une fuite de données (data leakage) — des observations T+1 peuvent apparaître en train avec leur T-1 en test.

---

## 5.3 Modélisation et comparaison des approches (CRISP-DM : Modeling + Evaluation)

### Modèles entraînés

| Modèle | CV R² (TimeSeriesSplit 5-fold) | Test R² | Sélection |
|---|---|---|---|
| LinearRegression | 0.094 | ~0.05 | ❌ Sous-ajusté |
| RandomForest (n=200, depth=15) | 0.522 | ~0.30 | ❌ En deçà du seuil |
| **HistGradientBoosting** | **0.673** | **0.218** | **✅ Retenu** |

### Validation croisée temporelle

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
# 5 folds : [fold_1_train | fold_1_val], [fold_2_train | fold_2_val], ...
# Chaque fold val est toujours postérieur au fold train — pas de fuite
```

Le CV R² = 0.673 est calculé sur les 5 folds avec `TimeSeriesSplit`, qui préserve l'ordre chronologique — chaque fenêtre de validation est strictement postérieure à sa fenêtre d'entraînement.

### HistGradientBoosting — Métriques finales

| Métrique | Valeur | Seuil CDC | Statut |
|---|---|---|---|
| CV R² | **0.6732** | ≥ 0.65 | ✅ Atteint |
| Test R² | **0.2179** | ≥ 0.65 | ❌ Sous cible |
| Test RMSE | **17.85** | < 10 (fill_rate 0–100) | ❌ |
| Test MAE | **12.36** | < 7 | ❌ |

Source : `ml/models/metadata.json`

### Analyse des erreurs — Écart CV vs Test R²

L'écart entre CV R² (0.673) et test R² (0.218) est structurel et s'explique par deux causes :

**Cause 1 — Features temporelles sans signal (5/14 features inutiles)**

Les features `hour`, `day_of_week`, `day_of_month`, `is_weekend`, `is_peak_hour` portent zéro signal car `lasc__livesim_fill` génère des taux de remplissage identiques à 2h du matin et à 10h un vendredi. En données réelles, ces features seraient les plus prédictives.

**Cause 2 — Mismatch entre générateurs de données**

| Générateur | Profil | Segment dataset |
|---|---|---|
| `lasc__seed_data` | `rate_per_hour` fixé UNE FOIS → rampe quasi-linéaire | Historique 30 j (train majoritaire) |
| `lasc__livesim_fill` | `rate` re-samplé CHAQUE tick → marche aléatoire | Données récentes (test complet) |

Le modèle apprend sur des profils stables (seed_data) mais est évalué sur des profils plus bruités (livesim) — le mismatch dégrade mécaniquement le test R².

**Correctif documenté (`ml/ROADMAP.md`) :**
```python
PEAK_HOURS = {7, 8, 9, 12, 17, 18, 19}
DAY_MULT   = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.4}
rate *= DAY_MULT[now.weekday()] * (1.3 if now.hour in PEAK_HOURS else 1.0)
```
Avec cette modification dans `lasc__livesim_fill`, les features temporelles deviennent informatives. Après 60–90 jours de données enrichies et re-entraînement, le test R² devrait rejoindre le CV R².

### Interprétabilité (XAI)

Le notebook `03_evaluation.ipynb` (non exécuté — bug `KeyError` sur la branche HGB documenté dans `documentation/ml/index.md §Known issue`) prévoit :

- **Feature importance** : `model.named_steps['model'].feature_importances_` pour HGB
- **Plot 1** : Scatter predictions vs actuals (test set, 2 000 points échantillonnés)
- **Plot 2** : Histogramme des erreurs (y_pred - y_test) — attendu centré sur 0
- **Plot 3** : Barplot Top 15 feature importances

**Importance attendue des features (sur données avec signal temporel) :**
1. `fill_rate_1h_ago` — meilleur prédicteur à court terme
2. `fill_rate_24h_avg` — tendance sur 24h
3. `fill_rate_24h_ago` — lag journalier
4. `fill_rate_change_rate` — vitesse de remplissage
5. `fill_rate_7d_avg` — tendance hebdomadaire
6–10. `type_id`, `capacity_liters`, `density_km2`, `hour`, `day_of_week` (si signal injecté)

---

## 5.4 Éthique et biais des données (CRISP-DM : Deployment — considérations éthiques)

### Analyse des biais potentiels

**1. Biais de représentativité (simulation vs réalité)**

Les données ECOTRACK sont intégralement synthétiques. Le modèle entraîné sur des données simulées ne peut pas être utilisé directement sur des capteurs réels sans calibration. Ce biais est documenté et délibéré dans le cadre académique du projet.

**2. Biais temporel — features sans signal**

Les 5 features temporelles (`hour`, `day_of_week`, `day_of_month`, `is_weekend`, `is_peak_hour`) portent zéro signal sur les données simulées mais seraient les plus prédictives sur des données réelles. Un modèle entraîné sur ECOTRACK et déployé en production sous-exploiterait systématiquement la dimension temporelle.

**3. Biais géographique — densité zone**

La feature `density_km2` est calculée à partir de `ST_Area(polygon)` — la densité géographique reflète uniquement la distribution des conteneurs dans le schéma, pas la densité de population réelle de chaque arrondissement. Ce biais de représentation spatiale est acceptable en simulation mais devrait être corrigé en production par l'injection de données INSEE.

**4. Absence de données personnelles dans le modèle ML**

La conformité RGPD est assurée par l'absence de toute donnée personnelle dans le dataset d'entraînement. Les features sont exclusivement temporelles, de lag, et de caractéristiques physiques des conteneurs — aucun identifiant utilisateur, localisation individuelle ou comportement citoyen n'est intégré.

### Mesures correctives implémentées

| Biais | Mesure | Statut |
|---|---|---|
| Simulation vs réalité | Documentation explicite du contexte synthétique | ✅ Documenté dans `documentation/ml/index.md` |
| Features temporelles sans signal | Correctif `PEAK_HOURS + DAY_MULT` documenté | ✅ Correctif prêt, non déployé |
| Mismatch seed/livesim | Retraining checklist 60–90 jours documenté | ✅ Roadmap documentée |
| Déséquilibre zones | `density_km2` à calibrer avec données INSEE | 🔲 Post-soutenance |
| Données personnelles | Aucune PII dans le dataset ML | ✅ Conforme RGPD |

---

*Sources : `ml/ROADMAP.md`, `ml/models/metadata.json`, `documentation/ml/index.md`, `dags/lasc__livesim_fill.py`, `dags/lasc__seed_data.py`*
