"""Testes de warehouse DuckDB — upsert e idempotência em :memory:."""

from __future__ import annotations

from pathlib import Path

import pytest

from careercompass.warehouse.duckdb import Warehouse


@pytest.fixture
def tmp_warehouse(tmp_path: Path) -> Warehouse:
    """Cria warehouse temporário para testes."""
    db_path = tmp_path / "test.duckdb"
    return Warehouse(db_path=str(db_path))


class TestWarehouse:
    """Testes de persistência DuckDB."""

    def test_schema_creation(self, tmp_warehouse: Warehouse) -> None:
        """Schema DDL executa sem erros."""
        tables = tmp_warehouse.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "staging_jobs" in table_names
        assert "dim_company" in table_names
        assert "dim_location" in table_names
        assert "dim_skill" in table_names
        assert "fact_job" in table_names
        assert "fact_job_skill" in table_names
        assert "fact_salary" in table_names

    def test_upsert_company(self, tmp_warehouse: Warehouse) -> None:
        cid = tmp_warehouse.upsert_company("TechCorp", "501")
        assert cid > 0

        # Idempotente
        cid2 = tmp_warehouse.upsert_company("TechCorp", "501")
        assert cid == cid2

    def test_upsert_location(self, tmp_warehouse: Warehouse) -> None:
        lid = tmp_warehouse.upsert_location("São Paulo", "SP")
        assert lid > 0

        lid2 = tmp_warehouse.upsert_location("São Paulo", "SP")
        assert lid == lid2

    def test_upsert_skill(self, tmp_warehouse: Warehouse) -> None:
        sid = tmp_warehouse.upsert_skill("python", "dados")
        assert sid > 0

        sid2 = tmp_warehouse.upsert_skill("python", "dados")
        assert sid == sid2

    def test_upsert_job_full(self, tmp_warehouse: Warehouse) -> None:
        job = {
            "fonte": "gupy",
            "id": "1",
            "titulo": "Analista de Dados",
            "empresa": "TestCo",
            "empresa_id": "99",
            "cidade": "São Paulo",
            "estado": "SP",
            "url": "https://example.com/job/1",
            "modalidade": "remoto",
            "publicado_em": "2026-09-01",
            "salario_min": 3000.0,
            "salario_max": 5000.0,
            "salario_moeda": "BRL",
            "salario_raw": None,
            "stack_matches": ["dados"],
            "stack_skills": ["python", "sql"],
            "senioridade": "junior",
            "descricao": "Vaga de dados",
        }
        fid = tmp_warehouse.upsert_job(job)
        assert fid > 0

        # Idempotente — mesma URL
        fid2 = tmp_warehouse.upsert_job(job)
        assert fid == fid2

    def test_upsert_job_idempotent(self, tmp_warehouse: Warehouse) -> None:
        job = {
            "fonte": "geekhunter",
            "id": "gh-1",
            "titulo": "Dev Python",
            "empresa": None,
            "empresa_id": None,
            "cidade": None,
            "estado": None,
            "url": "https://geekhunter.com/vaga/1",
            "modalidade": None,
            "publicado_em": None,
            "salario_min": None,
            "salario_max": None,
            "salario_moeda": None,
            "salario_raw": None,
            "stack_matches": ["backend"],
            "stack_skills": ["python"],
            "senioridade": "pleno",
            "descricao": None,
        }
        tmp_warehouse.upsert_job(job)
        tmp_warehouse.upsert_job(job)

        count = tmp_warehouse.conn.execute("SELECT COUNT(*) FROM fact_job").fetchone()[0]
        assert count == 1

    def test_summary(self, tmp_warehouse: Warehouse) -> None:
        job = {
            "fonte": "gupy",
            "id": "s1",
            "titulo": "Analista",
            "empresa": "Co",
            "empresa_id": "1",
            "cidade": "SP",
            "estado": "SP",
            "url": "https://x.com/1",
            "modalidade": "remoto",
            "publicado_em": "2026-09-01",
            "salario_min": 3000.0,
            "salario_max": 5000.0,
            "salario_moeda": "BRL",
            "salario_raw": None,
            "stack_matches": ["dados"],
            "stack_skills": ["python"],
            "senioridade": "junior",
            "descricao": None,
        }
        tmp_warehouse.upsert_job(job)
        summary = tmp_warehouse.summary()
        assert summary["total_empresas"] >= 1
        assert summary["cobertura_salarial"]["com_salario"] >= 1

    def test_count_by_fonte(self, tmp_warehouse: Warehouse) -> None:
        for i in range(3):
            tmp_warehouse.upsert_job(
                {
                    "fonte": "gupy",
                    "id": f"g{i}",
                    "titulo": f"Job {i}",
                    "empresa": None,
                    "empresa_id": None,
                    "cidade": None,
                    "estado": None,
                    "url": f"https://x.com/{i}",
                    "modalidade": None,
                    "publicado_em": None,
                    "salario_min": None,
                    "salario_max": None,
                    "salario_moeda": None,
                    "salario_raw": None,
                    "stack_matches": [],
                    "stack_skills": [],
                    "senioridade": "sem-info",
                    "descricao": None,
                }
            )
        counts = tmp_warehouse.count_by_fonte()
        assert any(c["fonte"] == "gupy" and c["total"] == 3 for c in counts)

    def test_context_manager(self, tmp_path: Path) -> None:
        with Warehouse(db_path=str(tmp_path / "ctx.duckdb")) as wh:
            assert wh.conn.execute("SELECT 1").fetchone()[0] == 1
