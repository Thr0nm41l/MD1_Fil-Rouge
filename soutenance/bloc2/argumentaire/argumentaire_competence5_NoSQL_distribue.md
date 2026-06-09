# Argumentaire oral — Compétence #5
## Installer et paramétrer des solutions de stockage de données massives (NoSQL, distribué)

---

## Question jury probable

> *"Vous utilisez PostgreSQL, qui est une base relationnelle classique. Comment justifiez-vous la compétence #5 qui demande explicitement des bases NoSQL et des systèmes de fichiers distribués ?"*

---

## Réponse structurée (≈ 3 minutes)

### 1. Les composants NoSQL et distribués présents dans le stack (45 s)

Le stack ECOTRACK contient trois composants qui relèvent directement des technologies NoSQL et du stockage distribué.

**Redis** est déployé dans le namespace `airflow` comme broker de tâches Celery. C'est une base NoSQL clé-valeur en mémoire : sans schéma, accès en < 1 ms, persistance optionnelle. Son rôle est critique — si Redis tombe, les deux workers Celery s'arrêtent et le pipeline IoT s'interrompt. Sa configuration dans le Helm chart `apache/airflow` inclut le paramétrage du pool de connexions, de la persistance et du mode de réplication.

**Apache Parquet** est le format de stockage du Feature Store ML (`ml/data/training_features.parquet`, 2,265 M lignes). C'est le format columnar distribué de référence — Delta Lake, Apache Iceberg, AWS Glue utilisent tous Parquet comme format physique. Il organise les données par colonnes, applique une compression par type, et est nativement partitionnable sur HDFS ou S3 sans modification du code applicatif. Il a été paramétré avec `pyarrow` pour le contrôle du schéma et de la compression.

**PostgreSQL partitionné** — les 36 partitions `PARTITION BY RANGE (measured_at)` de `fill_history` implémentent une logique de distribution des données proche de Cassandra ou TimescaleDB pour les séries temporelles : isolation physique par période, partition pruning automatique, agrégations parallèles. Sur un cluster Citus ou CloudNativePG, ces partitions se distribueraient sur des shards physiques distincts sans modification du schéma.

---

### 2. Les alternatives évaluées et les raisons du rejet (60 s)

Quatre technologies ont été évaluées avant de confirmer les choix retenus.

**TimescaleDB** — rejeté car le volume de 18 M lignes/an ne génère pas la contention de compression qui justifie son déploiement. La tâche BDD5 du CDC spécifie PostgreSQL 15 sans extension additionnelle obligatoire.

**Delta Lake / Apache Iceberg** — rejeté car le runtime Spark minimum (4 Go RAM, 3 nœuds) est disproportionné pour 2 Go de données actives. Le Feature Store Parquet simple remplit le même rôle de versionnement via le champ `trained_at` dans `metadata.json`.

**MinIO (stockage objet S3-compatible)** — rejeté car il aurait créé une deuxième source de vérité sans résoudre le problème d'idempotence des DAGs. PostgreSQL avec `ON CONFLICT DO NOTHING` garantit l'unicité nativement ; MinIO ne propose pas de primitive équivalente sur les objets.

**MongoDB** — rejeté car PostgreSQL JSONB couvre exactement le cas d'usage des données semi-structurées (configurations de dashboard, signalements) avec des opérateurs de requêtage (`@>`, `?`) comparables, sans déployer un second moteur de stockage.

---

### 3. Ce que j'aurais fait avec un volume ×10 (30 s)

Sur 180 M lignes/an (~20 Go), trois changements architecturaux seraient justifiés :

- **TimescaleDB** en remplacement du partitionnement manuel — compression automatique des chunks anciens (ratio 10:1), fonctions de fenêtrage temporel optimisées, pas de changement de code applicatif.
- **MinIO + Delta Lake** pour la couche Bronze — découplage de l'ingestion et du traitement, time travel pour les audits, gestion des schémas évolutifs entre re-entraînements.
- **Redis Cluster** en mode haute disponibilité — partitionnement des files de tâches entre plusieurs nœuds pour absorber les pics d'ingestion.

Ces choix ne sont pas retenus sur le périmètre actuel précisément parce qu'ils n'apportent pas de valeur fonctionnelle sur 18 M lignes/an — la compétence de maîtrise est démontrée par la connaissance des seuils de déclenchement, pas seulement par le déploiement systématique.

---

## Points de détail à maîtriser

| Sujet | Ce qu'il faut savoir dire |
|---|---|
| Redis vs RabbitMQ | Redis = KV en mémoire, latence < 1 ms, moins de garanties durabilité. RabbitMQ = message broker AMQP, garanties de livraison plus strictes, plus adapté aux queues persistantes longue durée. Airflow recommande Redis pour Celery car les tâches sont idempotentes (pas besoin de AMQP). |
| Parquet vs CSV | Parquet : columnar, compression par type, schéma embarqué, pushdown filtering. CSV : row-based, pas de compression, pas de schéma. Pour 2,265 M lignes × 14 features, Parquet est ~5× plus compact et ~10× plus rapide à lire en pandas. |
| Partition pruning PostgreSQL | Le planificateur PostgreSQL élimine les partitions dont la plage `measured_at` n'intersecte pas le filtre `WHERE`. Sur 36 partitions, une requête ciblant un mois ne lit qu'1/36 des données — équivalent d'un sharding temporel distribué. |
| Citus vs CloudNativePG | Citus = extension PostgreSQL qui ajoute le sharding horizontal (distribution des lignes sur plusieurs nœuds). CloudNativePG = opérateur Kubernetes pour PostgreSQL HA (réplication streaming). Pour ECOTRACK, CloudNativePG est l'évolution naturelle de Minikube vers un cluster cloud. |
| JSONB PostgreSQL vs MongoDB | JSONB = JSON binaire indexable dans PostgreSQL. Supporte `@>` (contains), `?` (key exists), index GIN. MongoDB = document store dédié, meilleur pour des structures profondément imbriquées ou des agrégations pipeline complexes. Pour des configs de dashboard à 1–2 niveaux d'imbrication, JSONB est suffisant. |

---

## Ancrage dans le dossier

La démonstration écrite de cette compétence se trouve dans le dossier professionnel à la section **§2.3 — Positionnement vis-à-vis des technologies NoSQL et du stockage distribué**, qui détaille :
- Le rôle de Redis comme broker NoSQL KV dans le namespace `airflow`
- Apache Parquet comme format columnar distribué du Feature Store ML
- Le partitionnement PostgreSQL comme équivalent fonctionnel d'un stockage distribué temporel
- Le tableau comparatif des 4 alternatives évaluées et rejetées (TimescaleDB, Delta Lake, MinIO, MongoDB)
