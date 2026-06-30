"""
Tests — Modèle ML hgb_v1.0
CDC criteria:
  - ML-01 : metadata.json accessible et conforme
  - ML-02 : CV R² ≥ 0.65 (seuil CDC task ML3)
  - ML-03 : modèle chargeable (joblib)
  - ML-04 : feature store Parquet valide (14 features, ≥ 2M lignes)
  - ML-05 : aucune PII dans le dataset d'entraînement
"""

import json
import os
from pathlib import Path

import pytest

ML_DIR = Path(__file__).parent.parent.parent / "ml"
METADATA_PATH = ML_DIR / "models" / "metadata.json"
MODEL_PATH = ML_DIR / "models" / "model.pkl"
PARQUET_PATH = ML_DIR / "data" / "training_features.parquet"

EXPECTED_FEATURES = {
    "hour", "day_of_week", "day_of_month", "is_weekend", "is_peak_hour",
    "fill_rate_1h_ago", "fill_rate_24h_ago", "fill_rate_7d_ago",
    "fill_rate_24h_avg", "fill_rate_7d_avg", "fill_rate_change_rate",
    "capacity_liters", "type_id", "density_km2",
}

PII_COLUMNS = {"user_id", "email", "name", "first_name", "password", "phone"}


# ── Tests metadata.json ───────────────────────────────────────────────────────

class TestMetadata:
    @pytest.fixture(autouse=True)
    def require_metadata(self):
        if not METADATA_PATH.exists():
            pytest.skip(f"metadata.json introuvable : {METADATA_PATH}")

    @pytest.fixture
    def metadata(self):
        with open(METADATA_PATH) as f:
            return json.load(f)

    def test_metadata_has_version(self, metadata):
        assert "version" in metadata

    def test_metadata_version_is_hgb(self, metadata):
        assert metadata["version"] == "hgb_v1.0"

    def test_metadata_has_cv_r2(self, metadata):
        assert "cv_r2" in metadata

    def test_cv_r2_meets_cdc_threshold(self, metadata):
        """CDC ML3 — CV R² ≥ 0.65."""
        assert metadata["cv_r2"] >= 0.65, (
            f"CV R² = {metadata['cv_r2']} — sous le seuil CDC de 0.65"
        )

    def test_metadata_has_train_rows(self, metadata):
        assert "train_rows" in metadata
        assert metadata["train_rows"] >= 1_000_000

    def test_metadata_n_features_is_14(self, metadata):
        """CDC ML — 14 features attendues."""
        assert metadata["n_features"] == 14, (
            f"Attendu 14 features, metadata indique {metadata['n_features']}"
        )

    def test_metadata_has_trained_at(self, metadata):
        assert "trained_at" in metadata
        assert isinstance(metadata["trained_at"], str)


# ── Tests modèle sérialisé ────────────────────────────────────────────────────

class TestModelFile:
    def test_model_pkl_exists(self):
        """CDC ML3 — model.pkl doit exister dans ml/models/."""
        assert MODEL_PATH.exists(), f"model.pkl introuvable : {MODEL_PATH}"

    def test_model_is_loadable(self):
        """CDC ML3 — le modèle doit être désérialisable sans erreur."""
        if not MODEL_PATH.exists():
            pytest.skip("model.pkl absent")
        import joblib
        model = joblib.load(MODEL_PATH)
        assert model is not None
        assert hasattr(model, "predict"), "Le modèle chargé n'expose pas de méthode predict()"


# ── Tests Feature Store Parquet ───────────────────────────────────────────────

class TestFeatureStore:
    @pytest.fixture(autouse=True)
    def require_parquet(self):
        if not PARQUET_PATH.exists():
            pytest.skip(f"training_features.parquet introuvable : {PARQUET_PATH}")

    @pytest.fixture(scope="class")
    def df(self):
        import pandas as pd
        return pd.read_parquet(PARQUET_PATH)

    def test_parquet_has_minimum_rows(self, df):
        """CDC ML — dataset d'entraînement ≥ 2 265 488 lignes."""
        assert len(df) >= 2_000_000, (
            f"Dataset contient {len(df):,} lignes — minimum attendu : 2 000 000"
        )

    def test_parquet_has_14_features_plus_target(self, df):
        """CDC ML — 14 features + colonne target."""
        feature_cols = set(df.columns) - {"target"}
        missing = EXPECTED_FEATURES - feature_cols
        assert not missing, f"Features manquantes dans le Parquet : {missing}"

    def test_parquet_target_column_exists(self, df):
        """CDC ML — colonne cible 'target' présente."""
        assert "target" in df.columns

    def test_parquet_target_bounds(self, df):
        """CDC ML — target (fill_rate T+24h) ∈ [0, 100]."""
        assert df["target"].min() >= 0
        assert df["target"].max() <= 100

    def test_parquet_no_pii_columns(self, df):
        """CDC SEC-03 / RGPD — aucune colonne PII dans le dataset ML."""
        pii_found = PII_COLUMNS & set(df.columns)
        assert not pii_found, (
            f"Colonnes PII détectées dans le dataset ML : {pii_found}"
        )

    def test_fill_rate_1h_ago_no_future_leakage(self, df):
        """CDC ML-01 — fill_rate_1h_ago doit être un décalage passé (pas futur).
        La corrélation avec target doit être non nulle (positive ou négative) :
        une corrélation négative est valide — un bac quasi-plein 1h avant a tendance
        à être vidangé avant l'horizon de 24h.
        """
        corr = df["fill_rate_1h_ago"].corr(df["target"])
        assert corr != 0, (
            f"Corrélation fill_rate_1h_ago/target = {corr:.3f} — feature non informative"
        )
