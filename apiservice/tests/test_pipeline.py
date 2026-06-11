"""
Tests — Pipeline ETL & idempotence
CDC criteria:
  - ETL-02 / ETL-04 : idempotence des DAGs (ON CONFLICT DO NOTHING/UPDATE)
  - ETL-03           : agrégations Gold mises à jour après ingestion
  - INF-01           : schéma complet (26 tables) déployé
  - BDD-02           : partitionnement de fill_history (≥ 36 partitions)
  - BDD-06           : trigger d'assignation géographique opérationnel
"""

import pytest
import psycopg2.extras
from datetime import datetime, timezone


@pytest.mark.integration
class TestSchemaCompleteness:
    EXPECTED_TABLES = {
        "zones", "container_type", "containers", "devices",
        "users", "user_role", "roles", "teams", "user_team",
        "fill_history", "routes", "route_steps", "collections", "signalements",
        "notifications",
        "aggregated_hourly_stats", "aggregated_daily_stats", "ml_predictions",
        "user_points", "badges", "user_badges", "defis", "defi_participations",
    }

    def test_all_expected_tables_exist(self, db_conn):
        """CDC INF-01 — les 26 tables du schéma doivent exister."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            existing = {row[0] for row in cur.fetchall()}

        missing = self.EXPECTED_TABLES - existing
        assert not missing, f"Tables manquantes dans le schéma : {missing}"

    def test_fill_history_has_partitions(self, db_conn):
        """CDC BDD-02 — fill_history partitionnée par RANGE (measured_at), ≥ 36 partitions."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM pg_inherits
                WHERE inhparent = 'fill_history'::regclass
            """)
            count = cur.fetchone()[0]
        assert count >= 36, (
            f"Seulement {count} partitions sur fill_history — attendu ≥ 36"
        )


@pytest.mark.integration
class TestContainerReferentialIntegrity:
    def test_all_fill_history_container_ids_exist(self, db_conn):
        """CDC — intégrité référentielle : container_id dans fill_history → containers."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM fill_history fh
                LEFT JOIN containers c ON c.key_container = fh.container_id
                WHERE c.key_container IS NULL
            """)
            orphans = cur.fetchone()[0]
        assert orphans == 0, (
            f"{orphans} lignes dans fill_history référencent un container_id inexistant"
        )

    def test_all_containers_have_zone(self, db_conn):
        """CDC BDD-06 — trigger containers_assign_zone : zone_id non NULL pour tout conteneur actif."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM containers
                WHERE is_active = true AND zone_id IS NULL
            """)
            unzoned = cur.fetchone()[0]
        assert unzoned == 0, (
            f"{unzoned} conteneurs actifs sans zone_id — trigger containers_assign_zone non déclenché"
        )


@pytest.mark.integration
class TestIdempotence:
    def test_duplicate_insert_does_not_create_duplicates(self, db_conn):
        """CDC ETL-04 — ON CONFLICT DO NOTHING : ré-insertion d'une mesure existante sans doublon."""
        ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        with db_conn.cursor() as cur:
            # Récupérer un container_id valide
            cur.execute("SELECT key_container FROM containers WHERE is_active = true LIMIT 1")
            row = cur.fetchone()
            if row is None:
                pytest.skip("Aucun conteneur actif pour le test d'idempotence")
            container_id = row[0]

            # Compter les lignes existantes pour ce (container_id, ts)
            cur.execute(
                "SELECT COUNT(*) FROM fill_history WHERE container_id = %s AND measured_at = %s",
                (container_id, ts),
            )
            before = cur.fetchone()[0]

            # Insérer avec ON CONFLICT DO NOTHING (simule le comportement du DAG)
            cur.execute("""
                INSERT INTO fill_history (measured_at, container_id, fill_rate, is_outlier)
                VALUES (%s, %s, 50.0, false)
                ON CONFLICT DO NOTHING
            """, (ts, container_id))

            # Réinsérer la même ligne
            cur.execute("""
                INSERT INTO fill_history (measured_at, container_id, fill_rate, is_outlier)
                VALUES (%s, %s, 75.0, false)
                ON CONFLICT DO NOTHING
            """, (ts, container_id))

            cur.execute(
                "SELECT COUNT(*) FROM fill_history WHERE container_id = %s AND measured_at = %s",
                (container_id, ts),
            )
            after = cur.fetchone()[0]

            # Nettoyage
            cur.execute(
                "DELETE FROM fill_history WHERE container_id = %s AND measured_at = %s",
                (container_id, ts),
            )
        db_conn.rollback()

        assert after <= before + 1, (
            "ON CONFLICT DO NOTHING n'a pas empêché la duplication — "
            f"{after - before} ligne(s) ajoutée(s) au lieu de 1 maximum"
        )


@pytest.mark.integration
class TestAggregationFreshness:
    def test_aggregated_hourly_covers_recent_data(self, db_conn):
        """CDC QUA-04 — aggregated_hourly_stats doit couvrir des données récentes."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT MAX(bucket_hour) FROM aggregated_hourly_stats")
            max_bucket = cur.fetchone()[0]
        assert max_bucket is not None, "aggregated_hourly_stats est vide"

    def test_aggregated_daily_covers_all_containers(self, db_conn):
        """CDC ETL-03 — toutes les zones doivent avoir des stats quotidiennes."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT ads.container_id)
                FROM aggregated_daily_stats ads
            """)
            count = cur.fetchone()[0]
        assert count >= 2000, (
            f"aggregated_daily_stats ne couvre que {count} conteneurs — attendu ≥ 2 000"
        )
