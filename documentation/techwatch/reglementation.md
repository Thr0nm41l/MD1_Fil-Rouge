# Regulatory & CSR Watch

**Themes:** Data protection · Accessibility · Corporate social responsibility · Digital sobriety
**Sources tracked:** CNIL, EDPB, EUR-Lex / EU Official Journal, DINUM (RGAA), ADEME / Green IT
**Method:** see [System & Method](index.md)

---

## Data protection (GDPR)

The project handles limited personal data (users, agent location, gamification behavioural data). The watch tracks the GDPR (EUR-Lex primary source) and its interpretation by the CNIL and the EDPB.

### Legal bases used

| Processing | Legal basis (GDPR art. 6) |
|---|---|
| Agent data (routes, authentication) | Performance of a contract (6.1.b) |
| Operational collection data | Public-interest task (6.1.e) |
| Citizen gamification (points, reports) | Explicit, revocable consent (6.1.a) |

### CNIL obligations tracked

- **Record of processing activities** (art. 30) — mandatory; 5 main processings identified (authentication, collection, analytics, gamification, monitoring).
- **DPO** (art. 37.1.a) — mandatory appointment for a public body; can be pooled across authorities.
- **DPIA / PIA** — recommended for agent geolocation and gamification profiling (processings listed by the CNIL as high-risk).
- **Information of data subjects** (art. 13–14) — privacy notice at sign-up.

### Privacy by Design (art. 25) — implemented measures

| Measure | Implementation |
|---|---|
| Pseudonymisation | No personal data in `fill_history`; agent link isolable via `collections.agent_id` |
| Secret encryption | bcrypt (cost 12) for passwords; credentials in Kubernetes Secrets |
| Access control | PostgreSQL Row-Level Security (`SET LOCAL app.user_id`) |
| Encrypted transport | HTTPS via Traefik v3 + cert-manager |
| Actionable rights | Erasure via `ON DELETE CASCADE`; right of access via JSON export |

!!! note "Active watch"
    The EDPB guidelines on Privacy by Design (art. 25) and the CNIL register templates are the two reference documents consulted first whenever the data scope changes.

---

## Digital accessibility (RGAA)

**RGAA 4.1** (stemming from the 2005 act, made mandatory for public services by decree no. 2019-768) requires **WCAG 2.1 level AA** conformance. ECOTRACK, deployed for a public authority, falls within its scope.

- **Audit surface**: the React frontend and Grafana dashboards (the REST API, having no UI, is out of scope).
- **Watch points**: tabular alternatives for GeoJSON choropleth/heatmap maps; full keyboard navigation; contrast ≥ 4.5:1 (WCAG criterion 1.4.3).
- **Estimated effort**: 3–5 person-days of audit and fixes on the frontend alone.

---

## Corporate social responsibility (CSR / ISO 26000)

Framed by the Grenelle II act and the **ISO 26000** standard, CSR is assessed on three axes:

- **Social**: fewer overflows and public-health risks in public space; gamification engaging citizens as actors.
- **Economic**: operational savings reallocatable to other public services (budget sobriety).
- **Governance**: a 100% open-source architecture securing the authority's technological sovereignty.

---

## Digital sobriety (Green IT / ADEME)

Digital sobriety (ADEME, Green IT collective) is a structuring criterion of the architecture.

| Lever | Effect |
|---|---|
| Avoiding the Big Data stack (Kafka + Spark + MinIO) | CPU/RAM consumption divided by ~4–6 for an identical functional result |
| Temporal partitioning of `fill_history` | Partition pruning: only useful blocks are read |
| Compute-data colocation (stored procedures) | No network transfer between worker and database |
| Grafana over direct SQL | No superfluous permanent cache/aggregation layer |

!!! tip "Impact ratio"
    On an FR datacentre (~40 gCO₂eq/kWh, PUE ≤ 1.3), the infrastructure weighs ~0.1–0.15 tCO₂eq/year, while route optimisation avoids ~24 tCO₂eq/year — a **positive impact ratio of roughly 160:1**.

---

## Reference sources

- **GDPR** — Regulation (EU) 2016/679, EUR-Lex / EU Official Journal
- **Waste Directive** — 2018/851 (55% recycling target by 2025)
- **CNIL** — register/DPIA guides, decisions, templates (cnil.fr)
- **EDPB** — guidelines, notably Privacy by Design art. 25 (edpb.europa.eu)
- **RGAA 4.1** — decree no. 2019-768, DINUM reference, WCAG 2.1 AA
- **ISO 26000** — CSR guidance; Grenelle II act
- **ADEME / Green IT** — digital sobriety approach
