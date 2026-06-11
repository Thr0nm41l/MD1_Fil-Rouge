"""
Tests — Qualité des données (accès direct PostgreSQL)
CDC criteria:
  - QUA-01 : taux de mesures valides ≥ 95 %
  - QUA-02 : fill_rate ∈ [0, 100] dans fill_history
  - QUA-03 : aucun outlier dans les tables agrégées Gold
  - QUA-04 : fill_history non vide, volume ≥ 1 000 000 lignes (seed_data)
  - BDD5   : contraintes CHECK actives et respectées
  - SEC-03 : aucune PII dans fill_history
"""

import pytest
import psycopg2.extras


@pytest.mark.integration
class TestFillHistoryVolume:
    def test_fill_history_has_minimum_rows(self, db_conn):
        """CDC — lasc__seed_data génère ≥ 1 440 000 lignes sur 30 jours."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fill_history")
            count = cur.fetchone()[0]
        assert count >= 1_000_000, (
            f"fill_history contient {count:,} lignes — minimum attendu : 1 000 000"
        )

    def test_fill_history_covers_30_days(self, db_conn):
        """CDC — historique de 30 jours minimum requis pour les features de lag 7 jours."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(measured_at) - MIN(measured_at) FROM fill_history"
            )
            span = cur.fetchone()[0]
        assert span.days >= 30, (
            f"Historique de {span.days} jours — minimum requis : 30 jours"
        )

    def test_all_2000_containers_have_history(self, db_conn):
        """CDC H1 — chaque conteneur actif doit avoir des mesures dans fill_history."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT fh.container_id)
                FROM fill_history fh
                JOIN containers c ON c.key_container = fh.container_id
                WHERE c.is_active = true
            """)
            count = cur.fetchone()[0]
        assert count >= 2000, (
            f"Seulement {count} conteneurs ont un historique — attendu : 2 000"
        )


@pytest.mark.integration
class TestFillRateBounds:
    def test_fill_rate_min_is_non_negative(self, db_conn):
        """CDC BDD5 — contrainte CHECK fill_rate >= 0."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT MIN(fill_rate) FROM fill_history")
            min_val = cur.fetchone()[0]
        assert min_val >= 0, f"fill_rate minimum = {min_val} — valeur négative détectée"

    def test_fill_rate_max_is_100(self, db_conn):
        """CDC BDD5 — contrainte CHECK fill_rate <= 100."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT MAX(fill_rate) FROM fill_history")
            max_val = cur.fetchone()[0]
        assert max_val <= 100, f"fill_rate maximum = {max_val} — dépassement de 100 %"

    def test_no_null_fill_rate(self, db_conn):
        """CDC — fill_rate NOT NULL."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM fill_history WHERE fill_rate IS NULL"
            )
            null_count = cur.fetchone()[0]
        assert null_count == 0, f"{null_count} lignes avec fill_rate NULL"

    def test_no_null_container_id(self, db_conn):
        """CDC — container_id NOT NULL dans fill_history."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM fill_history WHERE container_id IS NULL"
            )
            null_count = cur.fetchone()[0]
        assert null_count == 0, f"{null_count} lignes avec container_id NULL"


@pytest.mark.integration
class TestOutlierRate:
    def test_outlier_rate_is_approximately_1_percent(self, db_conn):
        """CDC QUA-01 — taux d'outliers ≈ 1 %, données valides ≥ 95 %."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE is_outlier = true)::float / COUNT(*) AS outlier_rate
                FROM fill_history
            """)
            rate = cur.fetchone()[0]
        assert rate <= 0.05, (
            f"Taux d'outliers = {rate:.2%} — dépasse le seuil de 5 % (CDC ≥ 95 % de données valides)"
        )

    def test_valid_data_rate_above_95_percent(self, db_conn):
        """CDC QUA-01 — au moins 95 % de mesures valides."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE is_outlier = false)::float / COUNT(*) AS valid_rate
                FROM fill_history
            """)
            rate = cur.fetchone()[0]
        assert rate >= 0.95, (
            f"Taux de données valides = {rate:.2%} — sous le seuil CDC de 95 %"
        )


@pytest.mark.integration
class TestGoldLayerQuality:
    def test_aggregated_hourly_has_no_outlier_signal(self, db_conn):
        """CDC QUA-03 — les outliers ne doivent pas polluer les agrégats Gold.
        Vérification indirecte : avg_fill_rate dans aggregated_hourly_stats ∈ [0, 100].
        """
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM aggregated_hourly_stats
                WHERE avg_fill_rate < 0 OR avg_fill_rate > 100
            """)
            bad_rows = cur.fetchone()[0]
        assert bad_rows == 0, (
            f"{bad_rows} lignes avec avg_fill_rate hors [0, 100] dans aggregated_hourly_stats"
        )

    def test_aggregated_daily_is_populated(self, db_conn):
        """CDC QUA-04 — les tables Gold doivent être peuplées après seed_data."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM aggregated_daily_stats")
            count = cur.fetchone()[0]
        assert count > 0, "aggregated_daily_stats est vide — run lasc__seed_data d'abord"

    def test_aggregated_hourly_is_populated(self, db_conn):
        """CDC QUA-04 — aggregated_hourly_stats peuplée."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM aggregated_hourly_stats")
            count = cur.fetchone()[0]
        assert count > 0, "aggregated_hourly_stats est vide"


@pytest.mark.integration
class TestNoPIIInHistory:
    def test_fill_history_has_no_user_id_column(self, db_conn):
        """CDC SEC-03 / RGPD — fill_history ne doit pas contenir de colonne user_id."""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'fill_history'
                  AND column_name IN ('user_id', 'email', 'name', 'first_name')
            """)
            pii_cols = [row[0] for row in cur.fetchall()]
        assert len(pii_cols) == 0, (
            f"Colonnes PII détectées dans fill_history : {pii_cols}"
        )
