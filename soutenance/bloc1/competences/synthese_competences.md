# Synthèse des compétences Bloc 1 — BESNIARD Thomas

> Rapport analysé : `Besniard_Thomas_Bloc1_DATA_2026.docx`
> Date d'analyse : 2026-06-05

---

## Tableau de synthèse

| # | Compétence | Statut | Section(s) du rapport | Ce qui est couvert | Ce qui manque |
|---|---|:---:|---|---|---|
| 1 | Analyser le fonctionnement d'une organisation et ses flux de données à partir d'une **cartographie des données** et d'une étude préalable afin d'identifier l'opportunité de développement d'un projet d'architecture | ⚠️ Partielle | I.1, III.2, IV.2 | Périmètre du projet décrit (I.1), pipeline de bout en bout (III.2), MCD complet OLTP/OLAP (IV.2) | Pas de cartographie **pré-projet** des flux organisationnels existants. Le rapport décrit ce qui a été construit, pas l'analyse de l'existant qui a motivé les choix |
| 2 | Décrire, en les formalisant, des **cas d'usages** du domaine de la Data en exploitant des **méthodes d'idéation** et en prenant en compte les spécificités de l'écosystème pour déterminer les besoins d'une architecture de gestion de données | ⚠️ Partielle | V.2 | 8 user stories formalisées (V.2) avec critères de validation mesurables | Les "méthodes d'idéation" ne sont pas nommées (pas de référence à Design Thinking, Event Storming, etc.). L'écosystème urbain/collectivités n'est pas analysé comme contexte métier |
| 3 | Elaborer un **système de veille technologique et réglementaire** propre au secteur du numérique (cloud, décisionnel, Big Data) en sélectionnant des sources vérifiées, collectant et analysant les informations afin d'adapter les choix technologiques | ✅ Présente | II.1 à II.5, I.6 | Veille sur 4 axes (batch, streaming, dashboarding, ML) avec comparatifs argumentés (II.1-II.4). Récapitulatif justifié (II.5). Veille réglementaire RGPD en I.6 | Aucune source n'est citée (pas de références bibliographiques, publications officielles ou articles). Les thèmes cloud et décisionnel sont effleurés (mention Scaleway/OVH) mais non développés en tant que tendances observées |
| 4 | Identifier les **sources critiques relatives au cadre juridique** et à la RSE en suivant les publications des organismes officiels afin d'améliorer la conformité du projet | ⚠️ Partielle | I.6 | Bases légales RGPD (art. 6), obligations CNIL (registre, DPO, AIPD), politique de rétention, Privacy by Design (art. 25) bien développés | Aucune publication officielle citée (pas de lien vers CNIL.fr, EDPB, etc.). **RSE complètement absente**. **Green IT / sobriété énergétique absents** |
| 5 | **Partager les résultats de la veille** en les synthétisant en interne via un **outil de partage documentaire professionnel** afin de diffuser les bonnes pratiques | ⚠️ Partielle | VI (Quick Wins) | MkDocs déployé sur `http://docs.localhost` mentionné comme livrable (Quick Win #6) | Le rapport ne montre pas comment les résultats de la veille ont été synthétisés et diffusés à l'équipe via MkDocs. Aucune structure de la documentation MkDocs n'est décrite. L'outil existe mais son usage comme vecteur de partage de veille n'est pas démontré |
| 6 | Initier une **étude de faisabilité** de l'architecture data en **collaboration avec un Data Scientist ou Data Analyst**, en sélectionnant et catégorisant les données selon leur disponibilité, valeur ajoutée et adéquation | ✅ Présente | I.1 à I.6 | Étude de faisabilité complète : périmètre, stockage, pipeline, visualisation, faisabilité économique (TCO, ROI), contraintes légales. Catégorisation des données : couches Bronze/Silver/Gold | La **collaboration** avec un Data Scientist ou Data Analyst n'est pas mentionnée explicitement. Le rapport est signé d'un seul auteur sans décrire la dimension collaborative de la faisabilité |
| 7 | Elaborer un **prototype de l'architecture data** en utilisant la technologie retenue sur un périmètre fonctionnel réduit afin d'évaluer son opérationnalité et sa pertinence | ✅ Présente | III.1 à III.6 | Cluster Kubernetes déployé (6 Helm Releases), 2 DAGs opérationnels, API 40+ endpoints, performances mesurées (III.6) : latence < 2 s, qualité 99 %, réponse API < 200 ms | RAS — compétence bien couverte |
| 8 | Rédiger un **cahier des charges** formalisant besoins, objectifs, risques, contraintes, sources de données, enjeux réglementaires (**RGAA, RGPD**) et éthiques (**RSE, Green IT**) | ⚠️ Partielle | I.6, VI.2 | RGPD traité en détail (I.6), risques projet documentés et suivis (VI.2), objectifs et contraintes techniques présents dans les sections III-V | Le CDC du projet est un document institutionnel fourni par l'école (`context/ECOTRACK_CDC_COMMUN_V2.pdf`) — il n'a pas été **rédigé** par l'étudiant, donc il ne valide pas la compétence. Ce qui manque concrètement dans le rapport : **RGAA** (accessibilité numérique) entièrement absent, **RSE** absente, **Green IT / sobriété énergétique** absents. Ces trois points pourraient tenir en 2-3 paragraphes à intégrer en I.6 |
| 9 | Rédiger les **spécifications techniques et fonctionnelles générales** de l'architecture d'analyse de données massives en analysant les besoins et retours d'expérience du prototype | ✅ Présente | III, IV, V, VI.1, VI.5 | Architecture détaillée (III), MCD/MLD MERISE (IV), user stories et KPIs (V), SWOT et recommandations priorisées (VI.1, VI.5) | RAS — compétence bien couverte |

---

## Résumé exécutif

| Statut | Nombre | Compétences |
|:---:|:---:|---|
| ✅ Présente | 3 | #3 Veille techno, #7 Prototype, #9 Spécifications |
| ⚠️ Partielle | 6 | #1 Cartographie, #2 Cas d'usages, #4 Cadre juridique, #5 Partage veille, #6 Faisabilité, #8 CDC |
| ❌ Absente | 0 | — |

> **Note CDC (#8) :** Le CDC institutionnel fourni par l'école (`context/ECOTRACK_CDC_COMMUN_V2.pdf`) ne peut pas valider cette compétence car il n'a pas été rédigé par l'étudiant. Le rapport couvre partiellement les éléments du CDC (RGPD, risques, contraintes techniques), mais RGAA, RSE et Green IT sont absents.

---

## Points d'attention prioritaires avant soutenance

1. **RGAA, RSE, Green IT** — complètement absents du rapport. Ces trois éléments apparaissent dans les compétences #4 et #8. Même un paragraphe court par thème suffirait à couvrir la lacune.
2. **Sources bibliographiques** — la veille (compétence #3) et le cadre juridique (compétence #4) ne citent aucune source. Ajouter une section Références/Bibliographie renforcerait fortement ces deux compétences.
3. **Méthodes d'idéation** (compétence #2) — nommer explicitement la méthode utilisée pour formaliser les user stories (Scrum backlog, Event Storming, etc.) comblerait le gap.
4. **Collaboration Data Scientist** (compétence #6) — mentionner explicitement qui a collaboré et comment (pair programming, revues de notebooks, etc.) pour valider la dimension collaborative.
5. **MkDocs comme vecteur de veille** (compétence #5) — décrire quelle partie de la documentation MkDocs porte les résultats de la veille et à qui elle est destinée.
