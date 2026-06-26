# Technology Watch

**Themes:** Cloud · Decision support (BI) · Big Data · Machine Learning
**Method:** see [System & Method](index.md)
**Principle:** every choice is driven by the project's real constraints, not by conformity to a generic stack

---

## Sizing context

ECOTRACK produces **~18 M rows/year** (2,000 containers × 144 ticks/day), an **intermediate** volume. This figure is the referee: it places the project **below** the thresholds where distributed Big Data frameworks become cost-effective. The watch consists precisely in confronting every reference technology with this real volume.

---

## Big Data — Batch processing

| Market reference | Strength | Limit in the ECOTRACK context |
|---|---|---|
| Apache Spark | Massively parallel batch | Break-even ~50 M rows; below that, worker coordination cost (≥ 3 nodes) outweighs the gain |
| Dask / Ray | In-process Python parallelism | Pointless for a sequential pipeline aggregating one bounded interval per run |

**Decision: PostgreSQL stored procedures.** They colocate compute and data (no network serialisation), guarantee idempotency via `INSERT … ON CONFLICT DO UPDATE`, and integrate natively into the Airflow task graph. The `aggregate_hourly()` / `aggregate_daily()` calls keep the analytics target < 100 ms thanks to the composite index `(container_id, measured_at DESC)` and partition pruning.

!!! info "Documented switch threshold"
    At ×10 volume (~180 M rows/year), the watch plans a switch to **TimescaleDB** (chunk compression) or distributed partitioning with **Citus**, without application rewrite.

---

## Big Data — Streaming / Ingestion

| Market reference | Strength | Limit in the ECOTRACK context |
|---|---|---|
| Kafka / Pulsar | Producer-consumer decoupling, durability, burst absorption | No concurrent producer: the source is a **centralised simulation** at fixed cadence |
| RabbitMQ | Message queue | Same finding; no replay need |

**Decision: scheduled Airflow DAG `*/10 * * * *`.** Single source, controlled pace, bulk insert via `execute_values`, immediate state propagation through SQL triggers. Kafka would remain the right choice for **real physical sensors** emitting concurrent MQTT — that is the retained switch criterion.

---

## Decision support — Reporting & Dashboarding

The project has two distinct restitution needs: **business analytics** (KPIs, heatmap, choropleth) and **infrastructure observability** (pods, Redis queue, Airflow metrics).

| Market reference | Business | Infra | Verdict |
|---|---|---|---|
| Superset / Metabase | ✅ self-service SQL | ❌ no Prometheus integration | Would require a 2nd monitoring tool |
| **Grafana** | ✅ native PostgreSQL datasource | ✅ native Prometheus datasource | **Retained**: unifies both dimensions |

**Decision: Grafana** for operational BI and observability, within a single alerting system. The decision layer relies on an **OLTP/OLAP separation** assumed from the design stage: the aggregate tables `aggregated_hourly_stats` / `aggregated_daily_stats` form a mini data warehouse that brings response times from several seconds (full scan) down to < 100 ms. The frontend itself consumes the FastAPI REST API (`/analytics/*` endpoints), fully decoupled from Grafana.

---

## Machine Learning — Model choice

CDC objective: predict fill rate 24 h ahead with **R² ≥ 0.65**. Three families evaluated on the feature set built from `fill_history`:

| Model | CV R² | Reading |
|---|---|---|
| Linear Regression | 0.094 | Unsuitable: non-linear cumulative dynamics |
| Random Forest | 0.522 | Does not exploit the sequential structure of the lags |
| **HistGradientBoosting** | **0.673** | **Retained**: iterative boosting on residuals captures temporal trends |

**Decision: HistGradientBoosting (`hgb_v1.0`).** After fixing the data generation (train/test alignment + hour/day modulation reactivating the temporal features), the model reaches **test R² = 0.753** (RMSE 9.95 / MAE 5.47), above all three CDC targets. Details on the [ML page](../ml/index.md).

!!! tip "Watch takeaway"
    Data quality beats model sophistication: a simulator without temporal modulation produces *apparently* relevant but statistically inert features. ML watch must therefore include a **feature/target correlation check before training**.

---

## Cloud — Hosting & sovereignty

| Criterion | Hyperscalers (AWS/GCP/Azure) | Sovereign cloud (Scaleway / OVHcloud) |
|---|---|---|
| Sovereignty of public data | Possible extra-EU exposure | FR/EU hosting, fits the public-authority context |
| Cost (cluster + managed PG + Redis) | Variable, often higher | ~€650–900 excl. tax/month estimated |
| Carbon footprint | Variable | FR datacentres with low emission factor (~40 gCO₂eq/kWh, PUE ≤ 1.3) |

**Decision: French sovereign cloud target.** For a public service, sovereignty and traceability come first; the fully open-source stack (PostgreSQL, Airflow, Grafana, FastAPI) avoids any proprietary lock-in and vendor price increases. In development, the cluster runs locally (Minikube, €0 cloud).

---

## Infrastructure components

| Need | Reference | Decision | Rationale |
|---|---|---|---|
| Ingress / routing | Nginx | **Traefik v3** | Native hostname-based routing + automatic TLS (cert-manager) without manual config |
| Airflow executor | LocalExecutor | **CeleryExecutor** | Worker isolation in a dedicated namespace + horizontal scalability |
| Task broker | — | **Redis** | In-memory KV < 1 ms, suited to the ephemeral messages of the Celery queue |
