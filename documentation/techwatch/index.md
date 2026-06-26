# Technology Watch — System & Method

**Scope:** technology and regulatory watch for the digital sector
**Priority themes:** Cloud · Decision support (BI) · Big Data · Legal & CSR
**Purpose:** continuously adapt technical choices and guarantee project compliance
**Distribution channel:** this MkDocs site, synced via `git-sync` and accessible to the whole team

---

## Purpose of the watch

The ECOTRACK watch pursues two inseparable goals:

1. **Adapt technology choices** to the real trends of the sector (Cloud, BI, Big Data) rather than to hype, by confronting every market option with the project's actual constraints (volume, source nature, measurable performance, cost).
2. **Guarantee regulatory and ethical compliance** continuously, by tracking the publications of official bodies (CNIL, EDPB, EU Official Journal, ADEME).

This page describes the **system**: sources, cadence, analysis method and sharing. The **results** are recorded in the two dedicated pages:

- [Technology watch](technologique.md) — Cloud, BI, Big Data, and stack decisions
- [Regulatory & CSR watch](reglementaire.md) — GDPR, CNIL, RGAA, ISO 26000, Green IT

---

## Source catalogue

Sources are selected on a single criterion: **verifiable reliability** (official vendor, public body, peer-reviewed academic publication). Secondary content (forums, unsourced blogs) is excluded.

| Source | Type | Theme | Review cadence |
|---|---|---|---|
| PostgreSQL, Airflow, FastAPI, Grafana, Traefik, Kubernetes docs | Official vendor | Big Data, BI, Cloud | On every version bump + changelogs |
| Foundational papers (Zaharia *et al.* / Spark; Kreps *et al.* / Kafka; Pedregosa *et al.* / scikit-learn; Ke *et al.* / LightGBM) | Academic | Big Data, ML | Reference (occasional) |
| **CNIL** — cnil.fr (guides, decisions, register templates) | National authority (FR data protection) | Legal | Monthly |
| **EDPB** — edpb.europa.eu (guidelines) | EU body | Legal | Quarterly |
| **EUR-Lex / EU Official Journal** (GDPR, Waste Directive 2018/851) | Primary legal source | Legal | Event-driven (new norm) |
| **DINUM / RGAA 4.1** — accessibilite.numerique.gouv.fr | Public body (FR accessibility) | Accessibility | On each reference revision |
| **ADEME** & **Green IT** collective | Public / professional body | CSR, sobriety | Quarterly |
| Sovereign cloud (Scaleway, OVHcloud — specs & pricing) | Vendor | Cloud | Half-yearly (TCO review) |

!!! note "Why these sources"
    For a data project serving a public authority, compliance relies on **primary legal sources** (EUR-Lex) and the **national supervisory authority** (CNIL); technical choices rely on **vendor documentation** and the **foundational papers** of the evaluated technologies, which provide the real relevance thresholds (e.g. Spark's break-even point).

---

## Analysis method

Every watch signal follows the same three-step circuit:

1. **Collect** — spot the novelty (release, guideline, regulatory change) at the official source.
2. **Analyse** — confront it with the project constraints: does it bring a *measurable functional* gain given the volume (~18 M rows/year), the source nature (centralised simulation) and the CDC performance targets?
3. **Decide & trace** — arbitrate (adopt / reject / monitor) and **record the decision and its rationale** on the matching watch page, which becomes the source of truth.

!!! tip "A constant decision rule"
    A component is retained only if it brings a functional benefit **at the project's real volume and context**. This rule led to ruling out Spark, Kafka and MinIO in favour of a PostgreSQL + Airflow + Grafana stack (see [Technology watch](technologique.md)).

---

## Governance & sharing

A watch only has value once shared. The distribution mechanism is:

- **Tool**: this **MkDocs** site (Material theme), which centralises all project documentation — the watch is a first-class section, on par with the API, database or ML sections.
- **Sync**: the site is updated automatically by a `git-sync` sidecar (every 60 s) from the repository, the same pattern used by Airflow for DAGs. Any watch update is therefore published without manual action.
- **Team access**: served in the cluster's `documentation` namespace (see [MkDocs how-to](../howto/mkdocs.md)), reachable via port-forward at `http://localhost:8080`.
- **Traceability**: Git history is authoritative — every change to the watch is dated and attributed.

---

## Summary of watch-driven decisions

| Domain | Market trend / reference | ECOTRACK decision | Page |
|---|---|---|---|
| Big Data processing | Spark / Dask / Ray | PostgreSQL stored procedures | [Tech](technologique.md) |
| IoT streaming | Kafka / Pulsar / RabbitMQ | Scheduled Airflow DAG | [Tech](technologique.md) |
| BI / Dashboarding | Superset / Metabase | Grafana (business + infra) | [Tech](technologique.md) |
| Predictive ML | LinearReg / RandomForest | HistGradientBoosting | [Tech](technologique.md) |
| Cloud | US hyperscalers | FR sovereign cloud (Scaleway/OVH) | [Tech](technologique.md) |
| Data protection | GDPR / CNIL-EDPB guidelines | Native Privacy by Design | [Regulatory](reglementaire.md) |
| Accessibility | RGAA 4.1 / WCAG 2.1 AA | Audit scoped to the frontend | [Regulatory](reglementaire.md) |
| Digital footprint | ADEME / Green IT sobriety | Big Data stack avoidance | [Regulatory](reglementaire.md) |
