"""Testes do export_snapshot — round-trip parquet + meta.yaml."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from careercompass import config


class TestExportSnapshot:
    """Testes de geração e leitura do snapshot."""

    def _make_duckdb(self, tmp_path: Path) -> Path:
        """Cria um DuckDB mínimo para testes."""
        import duckdb

        db_path = tmp_path / "warehouse.duckdb"
        con = duckdb.connect(str(db_path))
        con.execute("""
            CREATE TABLE IF NOT EXISTS dim_company (
                company_id INTEGER PRIMARY KEY,
                empresa VARCHAR NOT NULL,
                empresa_orig VARCHAR
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS dim_location (
                location_id INTEGER PRIMARY KEY,
                cidade VARCHAR NOT NULL,
                estado VARCHAR,
                uf VARCHAR
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS fact_job (
                job_id INTEGER PRIMARY KEY,
                fonte VARCHAR NOT NULL,
                url_original VARCHAR,
                titulo VARCHAR NOT NULL,
                senioridade VARCHAR,
                modalidade VARCHAR,
                publicado_em VARCHAR,
                empresa_id INTEGER,
                location_id INTEGER,
                categoria_principal VARCHAR,
                salario_min DOUBLE,
                salario_max DOUBLE,
                salario_moeda VARCHAR,
                salario_raw VARCHAR,
                loaded_at TIMESTAMP DEFAULT now()
            )
        """)
        # Seed dims
        con.execute(
            "INSERT INTO dim_company VALUES "
            "(1, 'TechCorp', 'tc1'), (2, 'DataInc', 'di1')"
        )
        con.execute(
            "INSERT INTO dim_location VALUES "
            "(1, 'São Paulo', 'SP', 'SP'), "
            "(2, 'Curitiba', 'PR', 'PR')"
        )

        # Jobs
        con.execute(
            """INSERT INTO fact_job
               (job_id, fonte, url_original, titulo, senioridade,
                modalidade, publicado_em, empresa_id, location_id,
                categoria_principal, salario_min, salario_max,
                salario_moeda, salario_raw)
               VALUES
               (1, 'gupy', 'https://gupy.io/1', 'Analista Dados Jr',
                'junior', 'remoto', '2026-09-10', 1, 1, 'dados',
                5000, 8000, 'BRL', NULL),
               (2, 'gupy', 'https://gupy.io/2', 'Dev Backend Pleno',
                'pleno', 'presencial', '2026-09-10', 1, 2, 'backend',
                10000, 15000, 'BRL', NULL),
               (3, 'geekhunter', 'https://gh.io/1', 'Eng Dados',
                'senior', 'hibrido', '2026-09-10', 2, 1, 'dados',
                NULL, NULL, NULL, NULL),
               (4, 'programathor', 'https://pt.io/1', 'Full Stack',
                NULL, NULL, '2026-09-09', NULL, NULL, NULL,
                NULL, NULL, NULL, NULL)"""
        )
        con.close()
        return db_path

    def test_export_snapshot_round_trip(self, tmp_path: Path) -> None:
        """Gera snapshot, lê de volta, valida schema e contagens."""
        db_path = self._make_duckdb(tmp_path)
        original_duckdb = config.DUCKDB_PATH

        # Redirect config to tmp
        config.DUCKDB_PATH = db_path
        import careercompass.export_snapshot as mod

        original_sn_dir = mod.SNAPSHOT_DIR
        mod.SNAPSHOT_DIR = tmp_path / "snapshot"

        try:
            from careercompass.export_snapshot import export_snapshot

            result = export_snapshot(max_rows=100, seed=42)

            # Arquivos existem
            jobs_path = Path(result["jobs_path"])
            salarios_path = Path(result["salarios_path"])
            meta_path = Path(result["meta_path"])
            assert jobs_path.exists()
            assert salarios_path.exists()
            assert meta_path.exists()

            # Round-trip jobs
            df_jobs = pd.read_parquet(jobs_path)
            assert len(df_jobs) == 4  # all 4 jobs
            expected_cols = {
                "fonte", "titulo", "categoria_principal",
                "senioridade", "modalidade", "cidade",
                "estado", "empresa", "publicado_em", "url",
            }
            assert set(df_jobs.columns) == expected_cols
            fontes = set(df_jobs["fonte"].unique())
            assert fontes == {"gupy", "geekhunter", "programathor"}

            # Round-trip salarios
            df_sal = pd.read_parquet(salarios_path)
            assert len(df_sal) == 2  # jobs 1 and 2 have salary
            expected_sal_cols = {
                "url", "job_id", "salario_min",
                "salario_max", "moeda",
            }
            assert set(df_sal.columns) == expected_sal_cols
            assert df_sal["moeda"].unique().tolist() == ["BRL"]

            # Meta.yaml
            meta_text = meta_path.read_text(encoding="utf-8")
            assert "data_geracao:" in meta_text
            assert "GERADO POR export_snapshot" in meta_text
            assert "fontes:" in meta_text

            # Tamanho total < 500 KB
            total_bytes = sum(
                p.stat().st_size
                for p in [jobs_path, salarios_path, meta_path]
            )
            assert total_bytes < 500 * 1024, (
                f"Snapshot muito grande: {total_bytes / 1024:.0f} KB"
            )

        finally:
            config.DUCKDB_PATH = original_duckdb
            mod.SNAPSHOT_DIR = original_sn_dir

    def test_export_snapshot_sample_respects_max_rows(
        self, tmp_path: Path
    ) -> None:
        """Quando max_rows < total, gera amostra com seed reprodutível."""
        db_path = self._make_duckdb(tmp_path)
        original_duckdb = config.DUCKDB_PATH
        config.DUCKDB_PATH = db_path

        import careercompass.export_snapshot as mod

        original_sn_dir = mod.SNAPSHOT_DIR
        mod.SNAPSHOT_DIR = tmp_path / "snapshot"

        try:
            from careercompass.export_snapshot import export_snapshot

            result = export_snapshot(max_rows=2, seed=42)
            df_jobs = pd.read_parquet(result["jobs_path"])
            assert len(df_jobs) == 2

            # Mesmo seed → mesmas linhas
            mod.SNAPSHOT_DIR = tmp_path / "snapshot2"
            result2 = export_snapshot(max_rows=2, seed=42)
            df_jobs2 = pd.read_parquet(result2["jobs_path"])
            assert (
                df_jobs["titulo"].tolist()
                == df_jobs2["titulo"].tolist()
            )

        finally:
            config.DUCKDB_PATH = original_duckdb
            mod.SNAPSHOT_DIR = original_sn_dir

    def test_export_snapshot_fails_without_duckdb(
        self, tmp_path: Path
    ) -> None:
        """Levanta FileNotFoundError se o DuckDB não existe."""
        original_duckdb = config.DUCKDB_PATH
        config.DUCKDB_PATH = tmp_path / "nonexistent.duckdb"

        try:
            from careercompass.export_snapshot import export_snapshot

            with pytest.raises(
                FileNotFoundError, match="Execute o pipeline antes"
            ):
                export_snapshot()
        finally:
            config.DUCKDB_PATH = original_duckdb
