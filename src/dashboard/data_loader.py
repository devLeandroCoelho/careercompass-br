"""
Carregador de dados: tenta DuckDB local, fallback para dados de demonstração.

Expõe uma única função `carregar_dados()` que retorna um dict de DataFrames
prontos para uso no dashboard.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

_DUCKDB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse.duckdb"


def _try_duckdb() -> dict[str, pd.DataFrame] | None:
    """Tenta ler o DuckDB. Retorna None se não existir ou se faltar tabela."""
    try:
        import duckdb

        if not _DUCKDB_PATH.exists():
            return None

        con = duckdb.connect(str(_DUCKDB_PATH), read_only=True)

        # Lista de tabelas esperadas
        required = ["fact_job", "dim_company", "dim_location", "dim_skill",
                     "fact_job_skill", "fact_salary"]
        existing = {row[0] for row in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()}

        missing = [t for t in required if t not in existing]
        if missing:
            con.close()
            return None

        tables: dict[str, pd.DataFrame] = {}
        for t in required:
            tables[t] = con.execute(f"SELECT * FROM {t}").fetchdf()

        con.close()
        return tables
    except Exception:
        return None


def _carregar_mock() -> dict[str, pd.DataFrame]:
    """Gera dados de demonstração."""
    from .mock_data import gerar_mock_jobs
    return gerar_mock_jobs()


def carregar_dados() -> tuple[dict[str, pd.DataFrame], bool]:
    """
    Retorna (dados, eh_mock).

    - dados: dict com DataFrames (fact_job, dim_company, etc.)
    - eh_mock: True se estiver usando dados de demonstração
    """
    duckdb_data = _try_duckdb()
    if duckdb_data is not None:
        return duckdb_data, False

    return _carregar_mock(), True


def join_completo(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Faz o join de fact_job com dim_company, dim_location e fact_salary
    para gerar um DataFrame pronto para análise no dashboard.

    Retorna DataFrame com colunas amigáveis em pt-BR.
    """
    fj = dados["fact_job"].copy()

    # Normalizar colunas do fact_job (DuckDB pode ter nomes diferentes)
    # Garantir que temos as colunas esperadas
    if "categoria" not in fj.columns and "categoria_principal" in fj.columns:
        fj = fj.rename(columns={"categoria_principal": "categoria"})

    dc = dados["dim_company"][["empresa_id", "nome"]].copy()
    dc = dc.rename(columns={"nome": "empresa"})

    dl = dados["dim_location"][["local_id", "cidade", "estado"]].copy()

    fs = dados["fact_salary"][["job_id", "salario_min", "salario_max", "moeda"]].copy() \
        if "fact_salary" in dados and not dados["fact_salary"].empty \
        else pd.DataFrame(columns=["job_id", "salario_min", "salario_max", "moeda"])

    # Join company
    fj = fj.merge(dc, on="empresa_id", how="left")
    # Join location
    fj = fj.merge(dl, on="local_id", how="left")
    # Join salary
    fj = fj.merge(fs, on="job_id", how="left")

    # Colunas amigáveis
    result = pd.DataFrame({
        "id": fj["job_id"],
        "fonte": fj["fonte"],
        "titulo": fj["titulo"],
        "categoria": fj["categoria"],
        "senioridade": fj["senioridade"],
        "modalidade": fj["modalidade"],
        "publicado_em": pd.to_datetime(fj["publicado_em"], errors="coerce"),
        "empresa": fj["empresa"],
        "cidade": fj["cidade"],
        "estado": fj["estado"],
        "salario_min": fj["salario_min"],
        "salario_max": fj["salario_max"],
        "moeda": fj["moeda"].fillna("BRL"),
        "url": fj["url_original"],
    })

    return result
