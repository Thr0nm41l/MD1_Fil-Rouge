# Synthèse des compétences Bloc 1 — BESNIARD Thomas

> Rapport analysé : `Besniard_Thomas_Bloc1_DATA_2026.docx`
> Date d'analyse : 2026-06-05

---

## Tableau de synthèse

| # | Compétence | Statut | Section(s) du rapport | Ce qui est couvert | Ce qui manque |
|---|---|:---:|---|---|---|
| 1 | Analyser le fonctionnement d'une organisation et ses flux de données à partir d'une **cartographie des données** et d'une étude préalable afin d'identifier l'opportunité de développement d'un projet d'architecture | ⚠️ Partielle | I.1, III.2, IV.2 | Périmètre du projet décrit (I.1), pipeline de bout en bout (III.2), MCD complet OLTP/OLAP (IV.2) | Pas de cartographie **pré-projet** des flux organisationnels existants. Le rapport décrit ce qui a été construit, pas l'analyse de l'existant qui a motivé les choix |
| 2 | Décrire, en les formalisant, des **cas d'usages** du domaine de la Data en exploitant des **méthodes d'idéation** et en prenant en compte les spécificités de l'écosystème pour déterminer les besoins d'une architecture de gestion de données | ✅ Présente | V.1, V.2 | Méthodes d'idéation nommées (§5.1.2) : analyse CDC, Epic Mapping (Patton 2014), priorisation MoSCoW, formalization Scrum. Contexte métier smart city / Métropole de Lyon documenté (§5.1.1). 8 user stories formalisées (V.2) avec critères de validation mesurables | RAS — compétence couverte |
| 3 | Elaborer un **système de veille technologique et réglementaire** propre au secteur du numérique (cloud, décisionnel, Big Data) en sélectionnant des sources vérifiées, collectant et analysant les informations afin d'adapter les choix technologiques | ✅ Présente | II.1 à II.5, I.6, VII | Veille sur 4 axes (batch, streaming, dashboarding, ML) avec comparatifs argumentés (II.1-II.4). Récapitulatif justifié (II.5). Veille réglementaire RGPD en I.6. Section VII : 20 références bibliographiques (Spark/Zaharia et al., Kafka/Kreps et al., scikit-learn/Pedregosa et al., CNIL, EDPB) | Les thèmes cloud et décisionnel sont effleurés (mention Scaleway/OVH) mais non développés en tant que tendances observées du marché |
| 4 | Identifier les **sources critiques relatives au cadre juridique** et à la RSE en suivant les publications des organismes officiels afin d'améliorer la conformité du projet | ✅ Présente | I.6, I.7, I.8, VII.1 | Bases légales RGPD (art. 6), obligations CNIL (registre, DPO, AIPD), Privacy by Design (art. 25). RGAA 4.1 (§1.6.6). RSE / ISO 26000 (§1.7). Green IT / sobriété numérique ADEME + ratio CO₂ (§1.8). Section VII.1 : RGPD JO UE, 3 guides CNIL, délibération AIPD 2018, guidelines EDPB art. 25 | RAS — compétence couverte |
| 5 | **Partager les résultats de la veille** en les synthétisant en interne via un **outil de partage documentaire professionnel** afin de diffuser les bonnes pratiques | ⚠️ Partielle | VI (Quick Wins) | MkDocs déployé sur `http://docs.localhost` mentionné comme livrable (Quick Win #6) | Le rapport ne montre pas comment les résultats de la veille ont été synthétisés et diffusés à l'équipe via MkDocs. Aucune structure de la documentation MkDocs n'est décrite. L'outil existe mais son usage comme vecteur de partage de veille n'est pas démontré |
| 6 | Initier une **étude de faisabilité** de l'architecture data en **collaboration avec un Data Scientist ou Data Analyst**, en sélectionnant et catégorisant les données selon leur disponibilité, valeur ajoutée et adéquation | ✅ Présente | I.1 à I.6 | Étude de faisabilité complète : périmètre, stockage, pipeline, visualisation, faisabilité économique (TCO, ROI), contraintes légales. Catégorisation des données : couches Bronze/Silver/Gold | La **collaboration** avec un Data Scientist ou Data Analyst n'est pas mentionnée explicitement. Le rapport est signé d'un seul auteur sans décrire la dimension collaborative de la faisabilité |
| 7 | Elaborer un **prototype de l'architecture data** en utilisant la technologie retenue sur un périmètre fonctionnel réduit afin d'évaluer son opérationnalité et sa pertinence | ✅ Présente | III.1 à III.6 | Cluster Kubernetes déployé (6 Helm Releases), 2 DAGs opérationnels, API 40+ endpoints, performances mesurées (III.6) : latence < 2 s, qualité 99 %, réponse API < 200 ms | RAS — compétence bien couverte |
| 8 | Rédiger un **cahier des charges** formalisant besoins, objectifs, risques, contraintes, sources de données, enjeux réglementaires (**RGAA, RGPD**) et éthiques (**RSE, Green IT**) | ⚠️ Partielle | I.6, I.7, I.8, VI.2 | RGPD (I.6), risques documentés (VI.2), objectifs et contraintes techniques (III-V). RGAA ajouté (§1.6.6 — audit non réalisé, périmètre et points de vigilance documentés). RSE / ISO 26000 ajouté (§1.7). Green IT / sobriété numérique ajouté avec ratio CO₂ (§1.8) | Le CDC institutionnel fourni par l'école n'a pas été **rédigé** par l'étudiant — la compétence reste partielle sur cet aspect de forme. Le fond (tous les enjeux réglementaires et éthiques) est maintenant couvert |
| 9 | Rédiger les **spécifications techniques et fonctionnelles générales** de l'architecture d'analyse de données massives en analysant les besoins et retours d'expérience du prototype | ✅ Présente | III, IV, V, VI.1, VI.5 | Architecture détaillée (III), MCD/MLD MERISE (IV), user stories et KPIs (V), SWOT et recommandations priorisées (VI.1, VI.5) | RAS — compétence bien couverte |

---

## Résumé exécutif

| Statut | Nombre | Compétences |
|:---:|:---:|---|
| ✅ Présente | 6 | #2 Cas d'usages, #3 Veille techno, #4 Cadre juridique+RSE, #6 Faisabilité, #7 Prototype, #9 Spécifications |
| ⚠️ Partielle | 3 | #1 Cartographie, #5 Partage veille, #8 CDC |
| ❌ Absente | 0 | — |

> **Note CDC (#8) :** Le CDC institutionnel fourni par l'école (`context/ECOTRACK_CDC_COMMUN_V2.pdf`) ne peut pas valider cette compétence car il n'a pas été rédigé par l'étudiant. Le fond (RGPD, RGAA, RSE, Green IT, risques) est maintenant couvert dans les sections I.6–I.8 et VI.2 ; la compétence reste partielle sur l'aspect de forme (absence d'un document CDC rédigé par l'étudiant).

---

## Points d'attention prioritaires avant soutenance

1. ~~**RGAA, RSE, Green IT**~~ — ✅ **Traité** : RGAA 4.1 ajouté en §1.6.6, RSE / ISO 26000 en §1.7, Green IT / sobriété numérique ADEME + ratio CO₂ 160:1 en §1.8.
2. ~~**Sources bibliographiques**~~ — ✅ **Traité** : section VII ajoutée (20 références : RGPD, CNIL, EDPB, Spark, Kafka, scikit-learn, LightGBM, PostgreSQL, Grafana, FastAPI, Traefik).
3. ~~**Méthodes d'idéation**~~ — ✅ **Traité** : §5.1.1 (contexte smart city / Métropole de Lyon), §5.1.2 (Epic Mapping / Patton 2014, MoSCoW, formalization Scrum), §7.5 (Patton, Schwaber/Sutherland, Cohn).
4. **Collaboration Data Scientist** (compétence #6) — mentionner explicitement qui a collaboré et comment (pair programming, revues de notebooks, etc.) pour valider la dimension collaborative.
5. **MkDocs comme vecteur de veille** (compétence #5) — décrire quelle partie de la documentation MkDocs porte les résultats de la veille et à qui elle est destinée.
