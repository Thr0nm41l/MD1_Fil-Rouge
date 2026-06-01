# BLOC 2 — Introduction : Contexte et présentation du dossier

> Section Introduction du template — 300 à 500 mots en prose académique.
> Ce fichier rassemble les éléments narratifs du projet ECOTRACK pour la rédaction de l'introduction.

---

## Éléments de contexte

### Contexte professionnel

ECOTRACK est une plateforme de gestion intelligente des déchets urbains conçue dans le cadre du projet fil rouge M1 Data & Analytics. Le projet répond à une problématique opérationnelle réelle : optimiser les tournées de collecte pour une ville de 500 000 habitants (5 arrondissements lyonnais) en exploitant les données IoT de 2 000 capteurs de remplissage installés sur les conteneurs de collecte.

La plateforme s'inscrit dans le cadre réglementaire de la transition écologique (directive européenne sur les déchets 2018/851, objectif 55 % de recyclage en 2025) et de la smart city (programme « French Tech Verte »). Les coûts d'une collecte non-optimisée sont estimés à 30–40 % d'énergie et de kilométrage superflus.

### Enjeux data du projet

Le projet ECOTRACK soulève quatre enjeux data structurants :

1. **Ingestion continue** : collecter et stocker les mesures de remplissage toutes les 10 minutes pour 2 000 capteurs, soit ~288 000 mesures par jour
2. **Qualité et fiabilité** : garantir l'intégrité des données malgré les pannes capteurs (flag `is_outlier`), les doublons (idempotence `ON CONFLICT`) et les valeurs aberrantes
3. **Analytique en temps réel** : calculer les KPIs opérationnels (taux de remplissage moyen, volume collecté, dépassements de seuil) avec une fraîcheur < 10 minutes
4. **Prédiction ML** : anticiper le niveau de remplissage à horizon 24 heures pour planifier les tournées avant saturation

### Problématique centrale

> **Comment concevoir un pipeline data-driven capable d'ingérer, de transformer et d'exposer en temps quasi-réel les données IoT de 2 000 capteurs de collecte urbaine, tout en fournissant une prédiction ML fiable du niveau de remplissage à 24 heures ?**

### Plan du dossier

Le dossier est structuré en cinq chapitres techniques :

- **Chapitre 2** — Contexte et problématique : présentation de l'organisation, inventaire des données, choix du paradigme data
- **Chapitre 3** — Architecture data : architecture 3 couches (Bronze/Silver/Gold) sur PostgreSQL, Feature Store
- **Chapitre 4** — Pipelines ETL/ELT : 4 DAGs Airflow, idempotence, qualité des données
- **Chapitre 5** — Machine Learning (CRISP-DM) : EDA, feature engineering, modélisation comparative, éthique
- **Chapitre 6** — Exposition des résultats : API FastAPI 40+ endpoints, dashboards Grafana
- **Chapitre 7** — Conclusion et perspectives : bilan, limites, axes d'amélioration

### Compétences transversales démontrées

**Anglais technique :** Sources anglophones intégrées — scikit-learn documentation, CRISP-DM framework (IBM), Kubernetes Helm chart documentation (Traefik v3, kube-prometheus-stack), PostgreSQL 15 partitioning release notes. Termes techniques en anglais maintenus dans le code (`fill_rate`, `is_outlier`, `bucket_hour`, `density_km2`).

**Numérique responsable :** Infrastructure locale Minikube (0 € de cloud, empreinte carbone nulle pour les tests), CO₂ calculé dans l'endpoint `/analytics/costs-roi` (0,27 kg CO₂/km économisé par optimisation des tournées), collecte optimisée réduisant le kilométrage de ~20 % (`_SAVINGS_RATE = 0.20` dans `apiservice/routers/analytics.py`).

---

*Sources : `context/master1_data_tasks.md`, `context/master1_data_epics.md`, `apiservice/routers/analytics.py`*
