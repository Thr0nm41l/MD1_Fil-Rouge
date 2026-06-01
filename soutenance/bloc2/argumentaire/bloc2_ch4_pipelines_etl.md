# BLOC 2 — Chapitre 4 : Pipelines ETL/ELT

> Template sections 4.1 (pipeline principal), 4.2 (qualité des données)

---

## 4.1 Description du pipeline principal

### Vue d'ensemble — 4 DAGs Airflow

| DAG | Rôle | Schedule | Pattern |
|---|---|---|---|
| `lasc__seed_data` | Bootstrap initial — génère la donnée historique (30 jours, 1,44 M lignes) | Manuel | EL (Extract-Load) sans transformation intermédiaire |
| `lasc__livesim_fill` | Simulation IoT continue — tick toutes les 10 min | `*/10 * * * *` | ETL (Extract-Transform-Load + triggers) |
| `lasc__ops_containers` | Opérations API-triggered — vide un conteneur ou reset batterie | Déclencheur REST | EL événementiel |
| `masc__clean_xcoms` | Hygiène Airflow — purge les XComs > 7 jours | Quotidien | Maintenance |

---

### DAG `lasc__livesim_fill` — Pipeline principal (ETL continu)

**Graph de tâches :**
```
start ──► simulate_fill ──► run_aggregations ──► end
```

#### Étape 1 — Extraction (`simulate_fill`, début)

```python
# Lecture de l'état courant : fill_rate + battery_pct pour tous les conteneurs actifs
SELECT c.key_container, c.fill_rate, c.type_id, d.battery_pct
FROM containers c
LEFT JOIN devices d ON d.container_id = c.key_container AND d.is_active = true
WHERE c.is_active = true
```

**Volume :** ~2 000 lignes lues par tick.

#### Étape 2 — Transformation (`simulate_fill`, calcul du tick)

```python
# Modèle physique par type de déchet
rate = FILL_RATE_PER_HOUR.get(type_id, 2.0) * RATE_SCALE
rate *= random.uniform(0.7, 1.3)     # variabilité ±30 %
new_fill = fill_rate + rate + random.gauss(0, 0.15)   # bruit gaussien σ=0.15

# Clamping physique [0, 100]
new_fill = max(0.0, min(100.0, new_fill))

# Flag outlier (1 % des mesures)
is_outlier = (random.random() < 0.01)
```

#### Étape 3 — Chargement (`simulate_fill`, bulk insert)

```python
# Insertion batch via execute_values (PostgreSQL COPY-equivalent)
psycopg2.extras.execute_values(
    cur,
    """INSERT INTO fill_history (measured_at, container_id, device_id, fill_rate,
       temperature, battery_pct, is_outlier)
       VALUES %s
       ON CONFLICT DO NOTHING""",
    rows,
    template="(%s, %s, %s, %s, %s, %s, %s)"
)
```

**Idempotence :** `ON CONFLICT DO NOTHING` sur `(container_id, measured_at)` arrondi à la minute — un re-run du DAG dans la même fenêtre temporelle ne génère pas de doublons.

**Triggers SQL actifs pendant le chargement :**
- `fill_history_update_container` (AFTER INSERT) : met à jour `containers.fill_rate`, `status` (`empty/normal/full/critical`), `last_updated`
- `fill_history_alert` (AFTER INSERT) : insère dans `notifications` si `fill_rate > fill_threshold_pct`

**Durée :** < 5 secondes pour 2 000 insertions + triggers.

#### Étape 4 — Agrégation (`run_aggregations`)

```python
# Appels aux procédures stockées idempotentes
cur.execute("CALL aggregate_hourly(%s)", (tick_ts,))
cur.execute("CALL aggregate_daily(%s)", (tick_ts.date(),))
```

Les procédures `aggregate_hourly` et `aggregate_daily` effectuent un `INSERT … ON CONFLICT DO UPDATE` sur `aggregated_hourly_stats` et `aggregated_daily_stats`. Elles filtrent `WHERE NOT is_outlier` pour garantir la qualité des KPIs Gold.

---

### DAG `lasc__seed_data` — Bootstrap initial (EL)

**Graph de tâches :**
```
start ──► [check_skip_users, seed_zones] ──► seed_containers ──► seed_devices
       ──► seed_fill_history ──► seed_collections ──► seed_signalements
       ──► run_aggregations ──► end
```

**Spécificités techniques :**

| Aspect | Valeur |
|---|---|
| Volume généré | 1 440 000 lignes `fill_history` (30 j × 2 000 conteneurs × ~144 ticks) |
| Durée | ~10 minutes |
| Optimisation | `SET session_replication_role = 'replica'` — désactive les triggers pour le bulk insert |
| Resynchronisation | `UPDATE containers SET fill_rate = last_measure.fill_rate ...` post-insert pour rétablir l'état cohérent |
| Idempotence | Tous les INSERTs : `ON CONFLICT DO UPDATE` (zones, conteneurs, devices) ou `DO NOTHING` (fill_history) |

**Différence clé avec `lasc__livesim_fill` :**
`lasc__seed_data` fixe `rate_per_hour` **une fois par conteneur** pour toute la période (rampe quasi-linéaire, σ=0.3/heure). `lasc__livesim_fill` re-sample `rate` à chaque tick (marche aléatoire, σ=0.15/tick). Ce mismatch est la cause racine du test R² ML bas (détaillé au §5).

---

### DAG `lasc__ops_containers` — Pipeline événementiel

**Déclencheur :** `POST /api/v1/dags/lasc__ops_containers/dagRuns` depuis FastAPI.

**Deux opérations :**
- `battery` : `UPDATE devices SET battery_pct = 100 WHERE container_id = :id`
- `unload` : INSERT dans `collections` (fill_rate_before/after, volume_collected_l) + `UPDATE containers SET fill_rate = 5.0`

**Concurrence :** `max_active_runs = 5` — gère les appels API simultanés sans deadlock.

**Gestion des erreurs :** `retries = 1` sur chaque tâche. En cas d'échec de `lasc__livesim_fill`, le tick manquant est ignoré (les capteurs IoT physiques emettent en continu — un tick manqué n'est pas une perte de données critique).

---

## 4.2 Qualité des données

### Règles de qualité implémentées

| Dimension | Règle | Mécanisme | Localisation |
|---|---|---|---|
| **Complétude** | `fill_rate`, `measured_at`, `container_id` jamais NULL | `NOT NULL` + FK | `setup_complete.sql` |
| **Unicité** | Une seule mesure par (conteneur, minute) | `ON CONFLICT DO NOTHING` + UNIQUE index partiel | `fill_history` + `lasc__livesim_fill` |
| **Cohérence domaine** | `fill_rate ∈ [0, 100]` | `CHECK (fill_rate >= 0 AND fill_rate <= 100)` | `setup_complete.sql` |
| **Cohérence référentielle** | `container_id` → `containers.key_container` | FK + `ON DELETE RESTRICT` | `setup_complete.sql` |
| **Fraîcheur** | Mesures toutes les 10 min (cible CDC < 5 min) | Schedule `*/10 * * * *` | `lasc__livesim_fill` |
| **Détection outliers** | 1 % des mesures flaggées `is_outlier = true` | Génération intentionnelle dans `simulate_fill` | `lasc__livesim_fill` |
| **Filtrage outliers** | Exclusion des outliers de tous les KPIs Gold | `WHERE NOT is_outlier` | `aggregate_hourly`, `aggregate_daily` |

### Stratégie de détection des outliers

Les outliers ne sont **pas supprimés** — ils sont flaggués (`is_outlier = true`) et conservés dans `fill_history` pour trois raisons :
1. **Audit** : la donnée brute est préservée pour debug et analyse rétrospective
2. **Idempotence** : supprimer une ligne crée des effets de bord lors des re-runs
3. **Conformité** : l'approche "flag, don't delete" est alignée avec les recommandations GDPR (droit à la rectification préféré à la suppression)

### Alertes sur dégradation de qualité

**Alerte temps réel :** le trigger `fill_history_alert` génère une `notification` de type `threshold_breach` dès qu'une mesure dépasse `containers.fill_threshold_pct`. Les notifications sont consultables via `GET /notifications` et configurent des alertes Grafana via la datasource PostgreSQL.

**Monitoring pipeline :** `pg_stat_statements` (activé dans `setup_complete.sql §2 Extensions`) trace les requêtes lentes. Les `ServiceMonitors` Prometheus surveillent :
- Airflow webserver (health `/health`)
- PostgreSQL (via `postgres-exporter`)
- Redis (via `redis-exporter`)

**KPI qualité mesuré :** ~99 % de mesures valides (1 % outliers flaggués intentionnellement, 0 % de données hors-contraintes grâce aux `CHECK` SQL).

### Gestion des erreurs et reprise

| Scénario | Comportement | Mitigation |
|---|---|---|
| Tick manqué (pod Airflow crash) | Les 2 000 mesures du tick sont absentes | Pas de reprise automatique — historique légèrement incomplet, sans impact sur les agrégats |
| Doublon d'insertion | `ON CONFLICT DO NOTHING` ignore silencieusement | Idempotence garantie |
| Violation de contrainte SQL | psycopg2 lève une exception → Airflow marque la tâche FAILED + alerte email | `retries = 1` — une retry automatique |
| Partition inexistante | Données redirigées vers `fill_history_default` | Pas de perte de données |

---

*Sources : `dags/lasc__livesim_fill.py`, `dags/lasc__seed_data.py`, `dags/lasc__ops_containers.py`, `documentation/dags/lasc__livesim_fill.md`, `database/setup_complete.sql`*
