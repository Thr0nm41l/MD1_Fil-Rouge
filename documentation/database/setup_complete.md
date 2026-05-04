# ECOTRACK — Complete Database Design Document

> Documents `setup_complete.sql` — the full production-ready script.

## Script structure

| Section | Content                        |
|---------|--------------------------------|
| 1       | Database creation              |
| 2       | Extensions                     |
| 3       | Application role               |
| 4       | Sequences                      |
| 5       | OLTP tables (17 tables)        |
| 6       | OLAP tables (4 tables)         |
| 7       | Gamification tables (5 tables) |
| 8       | Sequence ownership             |
| 9       | Indexes                        |
| 10      | Functions & procedures         |
| 11      | Triggers                       |
| 12      | RLS policies                   |
| 13      | Grants                         |

---

## Extensions

| Extension            | Why                                                                                                                                 |
|----------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `postgis`            | Mandatory for all spatial types and functions (`ST_Within`, `ST_DWithin`, `ST_Distance`, `ST_Area`, etc.) — covers Epic E2 entirely |
| `pg_trgm`            | Enables GIN trigram indexes for fuzzy text search on `users_history`                                                                |
| `btree_gin`          | Allows GIN indexes to support standard B-tree operators alongside `pg_trgm`                                                         |
| `pg_stat_statements` | Tracks query execution statistics — required for performance benchmarking (G9, G10, TEST3)                                          |

---

## OLTP Tables

### `role`
Lookup table for the four application roles: `User` (citizen), `Worker` (field agent), `Manager` (zone manager), `Admin` (platform administrator). Roles drive all RLS policies — every permission check ultimately resolves to a role key. Seeded on first run; a `UNIQUE` constraint on `name` prevents accidental duplicates.

### `zones`
Represents a geographic area of the city managed by the platform. Each zone has a `name`, an optional `postal_code`, and a `polygon GEOMETRY(Polygon, 4326)` storing its boundary in WGS84 coordinates. The polygon is the foundation of all spatial operations: it is used to auto-assign containers to their zone on insert, to list containers within a zone (`ST_Within`), and to compute density and choropleth map data (`ST_Area`).

### `users`
Stores all platform users regardless of role. Key columns:
- `email` — unique identifier used for login, constrained to `NOT NULL UNIQUE`.
- `password` — stores a bcrypt hash (`varchar(255)`).
- `created_at` — used in streak-based badge calculations and audit reporting.

Row-level security is enabled with `FORCE`, meaning even the table owner cannot bypass policies without explicitly setting the `app.user_id` session variable.

### `container_type`
Lookup table for waste categories. Each type has a `name` (e.g. Verre, Plastique, Organique), a `description`, and a `fill_threshold_pct` — the fill percentage at which a container of that type should be collected. Thresholds vary by type: organic waste (65%) degrades faster and needs earlier collection than glass (80%). Individual containers can override this value with their own `fill_threshold_pct`. Seeded with 6 waste types on first run.

### `containers`
The central operational table. Represents a physical waste container in the field.

| Column                           | Description                                                                                                          |
|----------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `location GEOMETRY(Point, 4326)` | GPS position as a PostGIS point — enables all spatial queries (nearest container, containers in zone, radius search) |
| `type_id`                        | FK to `container_type` — determines waste category and default fill threshold                                        |
| `zone_id`                        | FK to `zones` — populated automatically by trigger using `ST_Within` on insert                                       |
| `capacity_liters`                | Physical capacity of the container, used to compute actual collected volume                                          |
| `fill_rate`                      | Current fill level (0–100%), updated automatically after each IoT measurement                                        |
| `status`                         | Human-readable status derived from `fill_rate` (see thresholds below)                                                |
| `fill_threshold_pct`             | Alert threshold for this specific container, overrides the type-level default                                        |
| `is_active`                      | Soft-delete flag — containers are never physically removed from the database                                         |
| `last_updated`                   | Timestamp of the most recent measurement, used to detect stale sensors                                               |

Status thresholds:

| Fill rate | Status     |
|-----------|------------|
| < 25%     | `empty`    |
| 25–70%    | `normal`   |
| 70–90%    | `full`     |
| ≥ 90%     | `critical` |

### `device`
Represents the physical IoT sensor attached to a container. Sensors are distinct hardware from the container itself — a sensor can be replaced or upgraded without changing the container record. Tracks `model`, `firmware_version`, `battery_pct`, and `last_seen`. Used to correlate aberrant measurements with specific hardware and to monitor the health of the sensor fleet.

### `teams`
A team is a group of workers assigned to one zone. Each team has a `zone_id` (the geographic area it covers) and a `team_manager` (FK to `users`). Teams are referenced when building routes — a route is assigned to a team, whose agents carry it out.

### `user_role`
Junction table linking users to their roles (many-to-many). A user can hold multiple roles simultaneously (e.g. both Worker and Manager). A `UNIQUE(user_key, role_key)` constraint prevents duplicate assignments. RLS policies query this table on every protected row access via `get_user_role()` and `has_role()`.

### `user_team`
Junction table linking users to teams. Records `affectation_date` so the system can reconstruct historical team compositions. A `UNIQUE(key_user, key_team)` constraint prevents a user from appearing twice in the same team.

### `signalements`
A citizen report about a container or zone (overflow, damage, contamination, etc.). Lifecycle managed through `status`: `ouvert` → `en_traitement` → `resolu` / `ferme`. Key columns:
- `container_id` — the reported container (nullable, a report may concern an area rather than a specific container).
- `user_id` — the citizen who filed the report; used to award +10 points via trigger.
- `zone_id` — direct zone reference, enables zone-level filtering without joining through the container.
- `created_at` / `resolved_at` — power the incident timeline chart (A7) and resolution-time KPIs.

RLS is enabled: citizens can only read and create their own reports; workers, managers, and admins can read and update all.

### `routes`
A planned or executed collection route assigned to a team. The `path GEOMETRY(LineString, 4326)` stores the GPS trajectory, enabling distance calculations (`ST_Length`) and GeoJSON export for agents' mobile devices. Lifecycle via `status`: `planifiee` → `en_cours` → `terminee` / `annulee`. `distance_m` is computed and stored when the route is optimised.

### `route_steps`
The ordered sequence of containers to visit within a route. Each step has a `step_order` position, a reference to the target `container_id`, and collection tracking fields (`collected`, `collected_at`, `volume_collected_l`). A `UNIQUE(route_id, step_order)` constraint guarantees the sequence has no gaps or duplicates.

### `collections`
Records a physical collection event — the moment an agent empties a container. Distinct from `route_steps` because collections can happen ad hoc, outside of a planned route. Stores `fill_rate_before` and `fill_rate_after` for each event, enabling precise volume-collected calculations and before/after comparisons used in cost and ROI reports.

### `notifications`
System-generated alerts delivered to users. Covers threshold breaches (container critical), badge awards, route assignments, and general info messages. `user_id` is nullable: a `NULL` value means the notification is a broadcast visible to all managers. RLS ensures users only see their own notifications or broadcasts.

Supported types: `threshold_breach`, `maintenance`, `route_assigned`, `badge_earned`, `defi_completed`, `info`.

### `users_history`
Append-only audit log of every change to a `users` row. Populated automatically by a trigger after each `INSERT` or `UPDATE` on `users`. Each snapshot records the full row state at that moment (`email`, `name`, `first_name`, `password`) with a `valid_from` timestamp. `valid_to` and `is_current` support bi-temporal queries ("what did this user's profile look like on date X?"). A GIN trigram index on `email`, `name`, and `first_name` enables fast fuzzy-search across the audit log.

### `dashboard_config`
Persists each manager's personalised dashboard layout. The `layout_config jsonb` column stores the selected charts, grid positions, and saved filter preferences as a flexible JSON document. A `UNIQUE(user_id)` constraint ensures one configuration per user, which is upserted on each save. A GIN index enables efficient JSON path queries if specific config keys need to be queried server-side.

### `reports`
Tracks the lifecycle of generated PDF and Excel reports. When the API receives a generation request, a row is inserted with `status = 'pending'`. The backend worker updates it to `processing`, then `ready` once the file is written, storing the `file_path` for download. Supports five report types (`monthly`, `weekly`, `custom`, `zone`, `route`) and two formats (`pdf`, `excel`).

---

## OLAP Tables

### `fill_history`
The central IoT time-series table. Every measurement sent by a sensor in the field lands here. Key columns:

| Column         | Description                                                                                                                           |
|----------------|---------------------------------------------------------------------------------------------------------------------------------------|
| `container_id` | The container that was measured                                                                                                       |
| `device_id`    | The specific sensor that sent the reading (nullable, for hardware traceability)                                                       |
| `fill_rate`    | Measured fill level, 0–100 %, constrained by a CHECK                                                                                  |
| `temperature`  | Ambient temperature reported by the sensor                                                                                            |
| `battery_pct`  | Sensor battery level — used to detect devices that need maintenance                                                                   |
| `is_outlier`   | Flag set by the ETL pipeline when the value is statistically aberrant. Flagged rows are kept for audit but excluded from aggregations |
| `measured_at`  | Timestamp of the measurement — the partition key                                                                                      |

**Partitioning:** The table is range-partitioned by `measured_at`, one partition per calendar month. At ~500,000 rows/day this yields ~15M rows/month. Partitioning allows the query planner to skip irrelevant months entirely (partition pruning), which is what makes sub-100ms time-range queries possible at this volume. It also makes archiving straightforward: detaching and dropping a monthly partition is instantaneous, with no expensive DELETE scan.

Monthly partitions are pre-created for 2024, 2025, and 2026. A `_default` catch-all partition handles any data that falls outside these ranges.

**Composite PK:** PostgreSQL requires the partition key to be included in any unique constraint, so the primary key is `(key_history, measured_at)` rather than just `key_history`.

### `aggregated_hourly_stats`
Pre-computed hourly rollup of fill history data, one row per container per hour. Stores `avg_fill_rate`, `min_fill_rate`, `max_fill_rate`, and `measurement_count` for each bucket. Populated by the `aggregate_hourly` stored procedure, intended to be called every hour by the ETL scheduler.

Serving analytics queries from this table instead of aggregating raw `fill_history` on the fly is what allows the API to meet the <50ms response target — computing averages over millions of rows on every request would be too slow.

### `aggregated_daily_stats`
Pre-computed daily rollup, one row per container per calendar day. Extends the hourly rollup with two additional counters:
- `overflow_count` — the number of measurements in that day where `fill_rate` exceeded the container's threshold. Used to calculate overflow rates for KPI cards and ROI reports.
- `collection_count` — the number of times the container was emptied that day.

Populated by the `aggregate_daily` stored procedure.

### `ml_predictions`
Stores the output of the fill-rate prediction model. Each row represents a forecast for one container at a given point in time, for a given horizon (default 24 hours). Key columns:

| Column                | Description                                                                                                                |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------|
| `container_id`        | The container being predicted                                                                                              |
| `predicted_at`        | When the prediction was made                                                                                               |
| `horizon_hours`       | How far ahead the model is forecasting (default 24)                                                                        |
| `predicted_fill_rate` | The model's output                                                                                                         |
| `actual_fill_rate`    | Filled in ex-post once the real measurement arrives, enabling ongoing accuracy tracking (RMSE, MAE, R²) without retraining |
| `model_version`       | Identifies which model version produced the prediction — allows comparing accuracy across versions                         |

---

## Gamification Tables

### `user_points`
Designed as an **append-only ledger** rather than a single counter. Each action creates a new row. This:
- Preserves a complete audit trail of how points were earned.
- Enables time-filtered leaderboards (weekly, monthly — GAM4) by summing over `earned_at`.
- Allows point reversal for fraudulent actions without rewriting history.

### `badges`
Seeded with 30 badges across 6 categories (signalement, collecte, streak, zone, defi, special). The `condition_sql` column stores an optional SQL expression that a badge-award batch job can evaluate to auto-assign badges (GAM6), making badge logic data-driven and extensible without code changes.

### `user_badges`
`UNIQUE(user_id, badge_id)` ensures each badge is awarded at most once per user. An `AFTER INSERT` trigger fires automatically to credit the badge's point value and push a notification.

### `defis` / `defi_participations`
`defis` defines challenges with a `target_value` and an optional reward badge. `defi_participations` tracks each user's `progress` and sets `completed = true` with a timestamp when the goal is reached. `UNIQUE(defi_id, user_id)` prevents double registration.

---

## Indexes

### GIST spatial indexes
```sql
CREATE INDEX containers_location_gist_idx ON public.containers USING gist (location);
CREATE INDEX zones_polygon_gist_idx       ON public.zones      USING gist (polygon);
CREATE INDEX routes_path_gist_idx         ON public.routes     USING gist (path);
```
GIST is the only index type that supports spatial operators (`&&`, `~`, `ST_Within`, `ST_DWithin`, etc.). Without these, every spatial query performs a full table scan — the <200ms target at 2,000 containers (G9) would be unreachable.

### B-tree temporal indexes
All timestamp and date columns used in range queries have descending B-tree indexes. The most important composite index is:
```sql
CREATE INDEX fill_history_container_time_idx
    ON public.fill_history (container_id, measured_at DESC);
```
This covers the most frequent query pattern: "give me the fill history for container X over the last N days" (C10, H5). Putting `container_id` first means the index also serves plain `WHERE container_id = ?` lookups.

### Partial indexes
```sql
CREATE INDEX containers_status_active_idx
    ON public.containers (status) WHERE is_active = true;

CREATE INDEX notifications_user_unread_idx
    ON public.notifications (user_id, created_at DESC) WHERE is_read = false;
```
Partial indexes only cover rows matching the predicate, making them smaller and faster. Soft-deleted containers and read notifications are rarely queried — filtering them out at index build time is a significant win.

### GIN trigram index
```sql
CREATE INDEX users_history_gin_idx
    ON public.users_history USING gin (email gin_trgm_ops, name gin_trgm_ops, first_name gin_trgm_ops);
```
Enables `ILIKE '%search%'` queries on user history without full table scans, used for admin search and audit log lookups.

---

## Functions

### Spatial helpers

| Function                                  | Requirement | How                                                           |
|-------------------------------------------|-------------|---------------------------------------------------------------|
| `get_containers_in_zone(zone_id)`         | G6, Z2      | `ST_Within(location, polygon)`                                |
| `get_containers_near(lat, lng, radius_m)` | G7          | `ST_DWithin(location::geography, point::geography, radius_m)` |
| `get_zone_density(zone_id)`.              | Z5, C19     | `COUNT(*) / ST_Area(polygon::geography) / 1e6`                |

The `::geography` cast in `get_containers_near` is intentional: without it, `ST_DWithin` on `GEOMETRY(SRID 4326)` measures distances in degrees, not metres. Casting to `geography` forces metre-accurate great-circle distance calculation.

### `compute_container_status(fill_rate)`
A pure `IMMUTABLE` SQL function encoding the four status thresholds. `IMMUTABLE` means PostgreSQL can inline calls and, if needed, use the result in functional indexes.

### `is_duplicate_measurement(container_id, measured_at)`
Returns `true` if a measurement for the same container already exists within the same clock-minute. Used by the ETL pipeline before inserting (C14). It is a helper function — the deduplication decision lives in the application/ETL layer rather than a hard-blocking trigger, to avoid silent data loss on legitimate edge cases.

### `aggregate_hourly(hour)` / `aggregate_daily(day)`
`INSERT ... ON CONFLICT DO UPDATE` (upsert) procedures. They are **idempotent**: running them multiple times on the same bucket produces the same result. This is important for Airflow re-runs after failures.

### `get_heatmap_data(from, to)`
Returns `(day_of_week, hour_of_day, count)` tuples for the heatmap chart (A8, H7). Uses `EXTRACT(isodow ...)` (ISO day-of-week, 1=Monday) so the frontend can render a standard Mon–Sun grid.

### `get_choropleth_data()`
Returns per-zone geometry, container density (containers/km²) and average fill rate for the choropleth map (A9). Encapsulating this in a function gives the API a single stable interface while letting the DBA tune the query independently.

### `get_leaderboard(limit, from, to)`
Returns ranked users by total points for a given time window (GAM3, GAM4). The `from` / `to` parameters default to `NULL` (all time), enabling the same function to serve both the global leaderboard and the weekly/monthly variants.

---

## Triggers

| Trigger                         | Table           | Event                            | Purpose                                         | Req. |
|---------------------------------|-----------------|----------------------------------|-------------------------------------------------|------|
| `history_set_valid`             | `users_history` | BEFORE INSERT                    | Stamps `valid_from = NOW()`                     | —    |
| `users_archive_trigger`         | `users`         | AFTER INSERT/UPDATE              | Snapshots row to `users_history`                | —    |
| `containers_assign_zone`        | `containers`    | BEFORE INSERT/UPDATE OF location | Resolves `zone_id` via `ST_Within`              | Z4   |
| `fill_history_update_container` | `fill_history`  | AFTER INSERT                     | Syncs `fill_rate` and `status` on the container | C16  |
| `fill_history_alert`            | `fill_history`  | AFTER INSERT                     | Creates a notification if threshold exceeded    | C17  |
| `signalement_award_points`      | `signalements`  | AFTER INSERT                     | Credits +10 pts to the reporting user           | GAM2 |
| `user_badges_award_points`      | `user_badges`   | AFTER INSERT                     | Credits badge point value + pushes notification | GAM6 |

The two `fill_history` triggers fire on the parent partitioned table. PostgreSQL 13+ automatically propagates triggers to all child partitions — no per-partition setup is needed.

`containers_assign_zone` uses `ORDER BY ST_Area(polygon)` when multiple zones overlap a point, picking the **smallest enclosing zone** for the most precise assignment.

---

## RLS Policies

| Table           | Enabled     | Policy summary                                                                         |
|-----------------|-------------|----------------------------------------------------------------------------------------|
| `users`         | Yes (FORCE) | Admin: full. Manager: SELECT all. Worker/User: own row only for SELECT/UPDATE.         |
| `user_role`     | Yes         | SELECT own role mappings only.                                                         |
| `signalements`  | Yes         | Worker/Manager/Admin: all. Citizen: own rows only. INSERT restricted to own `user_id`. |
| `notifications` | Yes         | Own notifications + broadcasts (`user_id IS NULL`). Admin sees all.                    |

All policies use `current_setting('app.user_id', true)`. The application sets this session variable before executing any query. The `true` argument makes the function return `NULL` instead of raising an error when the variable is not set (e.g. during schema migrations run as superuser).

---

## What is intentionally outside the SQL script

The following requirements are handled at the application or ETL layer, not in SQL:

| Requirement                                 | Where it belongs         | Why                                                                        |
|---------------------------------------------|--------------------------|----------------------------------------------------------------------------|
| Outlier detection (C15)                     | Python ETL               | Statistical checks (z-score, IQR) are better expressed in Pandas           |
| MQTT IoT ingestion (H2)                     | FastAPI / message broker | Protocol-level concern, not a DB concern                                   |
| Aggregation scheduling (H3, H4)             | Airflow DAGs             | Calls `CALL aggregate_hourly(...)` / `CALL aggregate_daily(...)` on a cron |
| ML feature engineering & training (ML1–ML4) | Jupyter + Scikit-learn   | Out of scope for the DB layer                                              |
| PDF/Excel generation (R1, R2)               | reportlab / openpyxl     | File I/O happens in the backend                                            |
| Monthly partition creation beyond 2026      | Maintenance script       | Can be a simple Airflow task running `CREATE TABLE IF NOT EXISTS ...`      |
| Redis cache invalidation (C20)              | Backend caching layer    | Cache TTL and invalidation on new measurement handled in the API           |
