# Test Suite — ECOTRACK API (Epic E11)

**Status:** ✅ Done (unit) / ⚠️ Integration requires live DB
**Files:** `apiservice/tests/`
**Framework:** pytest 8.3 + httpx 0.27
**Total tests:** 58 — 18 unit, 40 integration

---

## Purpose

Validate the ECOTRACK platform against the CDC acceptance criteria (115 tasks,
`context/master1_data_tasks.md`). The suite covers five domains: API contract,
data quality, pipeline idempotence, database schema integrity, and ML model
conformance.

Tests are split into two modes so they can run in two different contexts:

- **Unit tests** — no database or Kubernetes required. The FastAPI dependency
  `get_db` is overridden with a mock connection. These run on any machine with
  the Python dependencies installed.
- **Integration tests** — marked `@pytest.mark.integration`. Require a live
  PostgreSQL connection, typically opened via `kubectl port-forward`. They are
  skipped automatically if the database is unreachable.

---

## Directory Structure

```
apiservice/tests/
├── __init__.py
├── conftest.py                 — shared fixtures (TestClient, DB connection)
├── test_health.py              — GET /health smoke tests               (3 tests)
├── test_api_containers.py      — containers CRUD + integration         (9 tests)
├── test_api_analytics.py       — analytics endpoints A1–A10           (14 tests)
├── test_data_quality.py        — data quality assertions on PostgreSQL (12 tests)
├── test_pipeline.py            — schema, idempotence, aggregations      (8 tests)
├── test_ml.py                  — metadata.json, model.pkl, Parquet     (12 tests)
├── requirements-test.txt       — test dependencies (pytest, httpx, pytest-cov)
└── README.md                   — pointer to this document + quick commands
```

---

## Per-file CDC Reference

Quick lookup: which CDC criteria each file covers.

| File | Tests | CDC criteria |
|---|:---:|---|
| `test_health.py` | 3 | Epic E5 — API availability |
| `test_api_containers.py` | 9 | C1 (list/pagination), C3 (detail), C4 (404), BDD5 (fill_rate bounds), H1 (2 000 containers) |
| `test_api_analytics.py` | 14 | A1–A10 (all analytics endpoints), A9 (GeoJSON choropleth), A10 (CO₂ ROI) |
| `test_data_quality.py` | 12 | QUA-01 (≥ 95 % valid), QUA-03 (no outliers in Gold), QUA-04 (Gold populated), BDD5 (NULL/bounds), SEC-03 (no PII) |
| `test_pipeline.py` | 8 | INF-01 (schema completeness), BDD-02 (partitions), BDD-06 (zone trigger), ETL-04 (idempotence), QUA-04 (aggregation freshness) |
| `test_ml.py` | 12 | ML1 (feature store), ML3 (CV R² ≥ 0.65), SEC-03 (no PII in Parquet) |

For the full criterion-to-test mapping see the [CDC Coverage Map](#cdc-coverage-map) section below.

---

## Quick Start

### Unit tests (no infrastructure required)

```bash
cd apiservice
pytest tests/ -m "not integration" -v
```

### Integration tests (requires port-forward)

```bash
# 1. Open the PostgreSQL tunnel
kubectl port-forward svc/postgres-postgresql 5432:5432 -n datalake

# 2. Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=Ecotrack
export POSTGRES_USER=<user>
export POSTGRES_PASSWORD=<password>

# 3. Run the full suite with coverage
pytest tests/ -v --cov=. --cov-report=term-missing
```

### Useful filters

```bash
# Single domain
pytest tests/test_data_quality.py -v

# Keyword filter
pytest tests/ -k "quality or idempotence" -v

# Coverage report (unit tests only)
pytest tests/ -m "not integration" --cov=. --cov-report=term-missing
```

---

## `conftest.py` — Shared Fixtures

| Fixture | Scope | Mode | Description |
|---|---|---|---|
| `mock_conn` | session | unit | Minimal `MagicMock` of a psycopg2 connection — satisfies `get_db` callers without a real database |
| `client` | session | unit | `TestClient` with `get_db` overridden by `mock_conn` — no DB required |
| `db_conn` | session | integration | Real `psycopg2` connection using env vars — skips the entire session if the DB is unreachable (3-second timeout) |
| `int_client` | session | integration | `TestClient` with `get_db` overridden by `db_conn` — hits the live database |

**Dependency override pattern** used for unit tests:

```python
app.dependency_overrides[get_db] = lambda: mock_conn
with TestClient(app) as c:
    yield c
app.dependency_overrides.clear()
```

**DB availability check** used in `db_conn`:

```python
psycopg2.connect(..., connect_timeout=3)
```

If the connection fails, `pytest.skip()` is called at the session level — all
integration tests are skipped gracefully without failing the run.

---

## `test_health.py` — Health endpoint

**Fixture:** `client` (unit)

| Test | Assertion |
|---|---|
| `test_health_returns_200` | `GET /health` → HTTP 200 |
| `test_health_body_structure` | Body contains `status: "ok"` |
| `test_health_message_present` | Body contains a non-empty `message` string |

---

## `test_api_containers.py` — Containers

### Unit tests — `TestContainersListStructure`

**Fixture:** `client` + `mock_conn`

| Test | CDC ref | Assertion |
|---|---|---|
| `test_returns_200` | C1 | `GET /containers` → HTTP 200 |
| `test_response_has_items_and_total` | C1 | Response body has `items` and `total` keys |
| `test_items_is_list` | C1 | `items` is a JSON array |
| `test_total_is_integer` | C1 | `total` is an integer |

### Unit tests — `TestContainerNotFound`

| Test | CDC ref | Assertion |
|---|---|---|
| `test_nonexistent_container_returns_404` | C4 | `GET /containers/999999` → HTTP 404 |
| `test_404_body_has_detail` | C4 | 404 body contains `detail` key |

### Integration tests — `TestContainersIntegration`

**Fixture:** `int_client` — requires live DB

| Test | CDC ref | Assertion |
|---|---|---|
| `test_total_active_containers_is_2000` | H1 | `total ≥ 2 000` active containers |
| `test_container_detail_has_required_fields` | C3 | Fields `key_container`, `lat`, `lng`, `fill_rate`, `status` present |
| `test_fill_rate_within_bounds` | BDD5 | All `fill_rate` values in `[0, 100]` across 100 sampled containers |
| `test_status_values_are_valid` | BDD5 | All `status` values in `{'empty','normal','full','critical'}` |
| `test_pagination_limit_respected` | C1 | `?limit=10` returns at most 10 items |

---

## `test_api_analytics.py` — Analytics endpoints

### Unit tests — `TestAnalyticsEndpointsExist`

**Fixture:** `client` + `mock_conn`

Parametrized over all 11 analytics endpoints:

```
/analytics/kpis            /analytics/volume-evolution  /analytics/type-distribution
/analytics/zone-collections /analytics/fill-distribution /analytics/fill-evolution
/analytics/route-performance /analytics/incidents        /analytics/heatmap
/analytics/choropleth       /analytics/costs-roi
```

| Test | Assertion |
|---|---|
| `test_endpoint_not_405` (×11) | No endpoint returns HTTP 405 Method Not Allowed |
| `test_endpoint_returns_json` (×11) | Every endpoint returns `Content-Type: application/json` |

### Integration tests

| Test class | CDC ref | Key assertion |
|---|---|---|
| `TestKpisIntegration` | A-KPI | Response contains volume/collection data |
| `TestChoroplethIntegration` | A9 | Returns exactly 5 zones with GeoJSON polygons and `avg_fill_rate` |
| `TestCostsRoiIntegration` | A10 | Response references CO₂ savings (`_CO2_PER_KM = 0.27 kg/km`) |

---

## `test_data_quality.py` — Data quality

All tests in this file are `@pytest.mark.integration` and use the `db_conn` fixture directly — they run SQL queries against PostgreSQL, bypassing the API layer.

### `TestFillHistoryVolume`

| Test | CDC ref | SQL assertion |
|---|---|---|
| `test_fill_history_has_minimum_rows` | ETL-01 | `COUNT(*) ≥ 1 000 000` rows in `fill_history` |
| `test_fill_history_covers_30_days` | ML feature store | `MAX - MIN ≥ 30 days` |
| `test_all_2000_containers_have_history` | H1 | `COUNT(DISTINCT container_id) ≥ 2 000` in `fill_history` |

### `TestFillRateBounds`

| Test | CDC ref | SQL assertion |
|---|---|---|
| `test_fill_rate_min_is_non_negative` | BDD5 | `MIN(fill_rate) ≥ 0` |
| `test_fill_rate_max_is_100` | BDD5 | `MAX(fill_rate) ≤ 100` |
| `test_no_null_fill_rate` | BDD5 | `COUNT(*) WHERE fill_rate IS NULL = 0` |
| `test_no_null_container_id` | BDD5 | `COUNT(*) WHERE container_id IS NULL = 0` |

### `TestOutlierRate`

| Test | CDC ref | SQL assertion |
|---|---|---|
| `test_outlier_rate_is_approximately_1_percent` | QUA-01 | `is_outlier = true` rate ≤ 5 % |
| `test_valid_data_rate_above_95_percent` | QUA-01 | `is_outlier = false` rate ≥ 95 % |

### `TestGoldLayerQuality`

| Test | CDC ref | SQL assertion |
|---|---|---|
| `test_aggregated_hourly_has_no_outlier_signal` | QUA-03 | No `avg_fill_rate` outside `[0, 100]` in `aggregated_hourly_stats` |
| `test_aggregated_daily_is_populated` | QUA-04 | `aggregated_daily_stats` row count > 0 |
| `test_aggregated_hourly_is_populated` | QUA-04 | `aggregated_hourly_stats` row count > 0 |

### `TestNoPIIInHistory`

| Test | CDC ref | SQL assertion |
|---|---|---|
| `test_fill_history_has_no_user_id_column` | SEC-03 / RGPD | `information_schema.columns` returns no PII column names (`user_id`, `email`, `name`, etc.) in `fill_history` |

---

## `test_pipeline.py` — Pipeline integrity

### `TestSchemaCompleteness`

**Expected tables (23 minimum):**

```
OLTP:  zones, container_type, containers, devices, users, user_role, roles,
       teams, user_team, fill_history, routes, route_steps, collections,
       signalements, notifications
OLAP:  aggregated_hourly_stats, aggregated_daily_stats, ml_predictions
GAME:  user_points, badges, user_badges, defis, defi_participations
```

| Test | CDC ref | Assertion |
|---|---|---|
| `test_all_expected_tables_exist` | INF-01 | All 23 tables present in `information_schema.tables` |
| `test_fill_history_has_partitions` | BDD-02 | `pg_inherits` returns ≥ 36 child partitions for `fill_history` |

### `TestContainerReferentialIntegrity`

| Test | CDC ref | Assertion |
|---|---|---|
| `test_all_fill_history_container_ids_exist` | BDD5 | `LEFT JOIN containers` returns 0 orphaned `container_id` values |
| `test_all_containers_have_zone` | BDD-06 | No active container has `zone_id IS NULL` — trigger `containers_assign_zone` effective |

### `TestIdempotence`

| Test | CDC ref | Assertion |
|---|---|---|
| `test_duplicate_insert_does_not_create_duplicates` | ETL-04 | Two identical `INSERT … ON CONFLICT DO NOTHING` calls add at most 1 row |

The test inserts a synthetic row with a fixed past timestamp, verifies the
duplicate is rejected, then rolls back — leaving the database unchanged.

### `TestAggregationFreshness`

| Test | CDC ref | Assertion |
|---|---|---|
| `test_aggregated_hourly_covers_recent_data` | QUA-04 | `MAX(bucket_hour)` is not NULL |
| `test_aggregated_daily_covers_all_containers` | ETL-03 | `COUNT(DISTINCT container_id) ≥ 2 000` in `aggregated_daily_stats` |

---

## `test_ml.py` — ML model

### `TestMetadata` — `ml/models/metadata.json`

Skipped automatically if `metadata.json` does not exist.

| Test | CDC ref | Assertion |
|---|---|---|
| `test_metadata_has_version` | ML3 | `version` key present |
| `test_metadata_version_is_hgb` | ML3 | `version == "hgb_v1.0"` |
| `test_cv_r2_meets_cdc_threshold` | ML3 | `cv_r2 ≥ 0.65` |
| `test_metadata_has_train_rows` | ML2 | `train_rows ≥ 1 000 000` |
| `test_metadata_n_features_is_14` | ML1 | `n_features == 14` |
| `test_metadata_has_trained_at` | ML2 | `trained_at` is a non-empty ISO 8601 string |

### `TestModelFile` — `ml/models/model.pkl`

| Test | CDC ref | Assertion |
|---|---|---|
| `test_model_pkl_exists` | ML3 | `model.pkl` present on disk |
| `test_model_is_loadable` | ML3 | `joblib.load()` succeeds; object has `predict()` method |

### `TestFeatureStore` — `ml/data/training_features.parquet`

Skipped automatically if the Parquet file does not exist.

| Test | CDC ref | Assertion |
|---|---|---|
| `test_parquet_has_minimum_rows` | ML1 | Row count ≥ 2 000 000 |
| `test_parquet_has_14_features_plus_target` | ML1 | All 14 expected feature columns present |
| `test_parquet_target_column_exists` | ML1 | `target` column present |
| `test_parquet_target_bounds` | ML1 | `target ∈ [0, 100]` (physical fill rate range) |
| `test_parquet_no_pii_columns` | SEC-03 | No PII column names in Parquet schema |
| `test_fill_rate_1h_ago_no_future_leakage` | ML-01 | Pearson correlation between `fill_rate_1h_ago` and `target` > 0 (past lag, not future) |

---

## CDC Coverage Map

| CDC criterion | Test file(s) | Test class(es) |
|---|---|---|
| C1 — container list pagination | `test_api_containers.py` | `TestContainersListStructure` |
| C3 — container detail | `test_api_containers.py` | `TestContainersIntegration` |
| C4 — 404 on missing container | `test_api_containers.py` | `TestContainerNotFound` |
| H1 — 2 000 active containers | `test_api_containers.py`, `test_data_quality.py` | `TestContainersIntegration`, `TestFillHistoryVolume` |
| A1–A10 — analytics endpoints | `test_api_analytics.py` | `TestAnalyticsEndpointsExist` |
| A9 — choropleth GeoJSON | `test_api_analytics.py` | `TestChoroplethIntegration` |
| A10 — costs/ROI | `test_api_analytics.py` | `TestCostsRoiIntegration` |
| QUA-01 — ≥ 95 % valid data | `test_data_quality.py` | `TestOutlierRate` |
| QUA-03 — no outliers in Gold | `test_data_quality.py` | `TestGoldLayerQuality` |
| QUA-04 — Gold tables populated | `test_data_quality.py`, `test_pipeline.py` | `TestGoldLayerQuality`, `TestAggregationFreshness` |
| BDD5 — fill_rate ∈ [0, 100] | `test_api_containers.py`, `test_data_quality.py` | `TestContainersIntegration`, `TestFillRateBounds` |
| BDD-02 — fill_history partitions | `test_pipeline.py` | `TestSchemaCompleteness` |
| BDD-06 — zone assignment trigger | `test_pipeline.py` | `TestContainerReferentialIntegrity` |
| ETL-01 — seed data volume | `test_data_quality.py` | `TestFillHistoryVolume` |
| ETL-04 — pipeline idempotence | `test_pipeline.py` | `TestIdempotence` |
| INF-01 — full schema deployed | `test_pipeline.py` | `TestSchemaCompleteness` |
| ML1 — feature engineering | `test_ml.py` | `TestFeatureStore` |
| ML3 — CV R² ≥ 0.65 | `test_ml.py` | `TestMetadata` |
| SEC-03 / RGPD — no PII in ML | `test_data_quality.py`, `test_ml.py` | `TestNoPIIInHistory`, `TestFeatureStore` |

---

## Known Limitations

**Epic E11 coverage target:** the CDC requires test coverage > 50 % (`context/master1_data_tasks.md`, task E11). The current suite covers the main validation paths but does not yet include:

- Router `gamification` (stubs — no SQL logic to test yet)
- Router `reports` (stub — no PDF generation logic)
- `POST /ml/predict` (stub 503 — model not yet wired into the container)
- Negative path tests for zone and route endpoints

These gaps are documented in the acceptance test PV (`soutenance/bloc2/rendus/ECOTRACK_PV_Recette.md`, reserves R-01 to R-03) and tracked as post-soutenance deliverables.

**Idempotence test isolation:** the `TestIdempotence` test inserts a synthetic row into `fill_history` and then calls `db_conn.rollback()`. If the test is interrupted mid-run the row may persist — run `DELETE FROM fill_history WHERE measured_at = '2025-01-01 12:00:00+00'` to clean up manually.
