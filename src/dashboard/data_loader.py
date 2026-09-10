"""
Carregador de dados com hierarquia de fontes.

Hierarquia (mais real primeiro):
  1. DuckDB local (`data/warehouse.duckdb`) → dados completos
  2. Snapshot real (`data/snapshot/*.parquet`) → amostra versionável
  3. Mock (gerado em memória) → demonstração

Expõe `carregar_dados()` que retorna (dados, fonte) e `join_completo()`
que normaliza todos os formatos em um DataFrame pronto para o dashboard.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from src.dashboard.utils.normalizacao import preencher_missing

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
_DUCKDB_PATH = _ROOT / "data" / "warehouse.duckdb"
_SNAPSHOT_DIR = _ROOT / "data" / "snapshot"


# ── Fonte de dados (enum para testabilidade) ──────────────────────────
class FonteDados(str, Enum):
    DUCKDB = "duckdb"
    SNAPSHOT = "snapshot"
    MOCK = "mock"


# ── Meta do snapshot (lida do meta.yaml) ─────────────────────────────
def _read_snapshot_meta() -> dict[str, Any]:
    """Lê meta.yaml do snapshot com parse simples (sem dependência pyyaml).

    Returns dict com chaves como strings. Se o arquivo não existir ou
    houver erro, retorna dict vazio.
    """
    meta_path = _SNAPSHOT_DIR / "meta.yaml"
    if not meta_path.exists():
        return {}

    meta: dict[str, Any] = {}
    try:
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                value = value.strip().strip('"').strip("'")
                # Tenta converter para número
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                meta[key.strip()] = value
    except Exception as exc:
        logger.warning("Erro ao ler meta.yaml: %s", exc)
    return meta


# ── Identificação de fonte (função pura, testável) ───────────────────
def identify_source() -> FonteDados:
    """Determina qual fonte de dados usar.

    Hierarquia: DuckDB > Snapshot > Mock.
    """
    if _DUCKDB_PATH.exists():
        return FonteDados.DUCKDB
    if (_SNAPSHOT_DIR / "jobs_snapshot.parquet").exists():
        return FonteDados.SNAPSHOT
    return FonteDados.MOCK


# ── Carregamento por fonte ────────────────────────────────────────────
def _try_duckdb() -> dict[str, pd.DataFrame] | None:
    """Tenta ler o DuckDB. Retorna None se não existir ou faltar tabela."""
    try:
        import duckdb

        if not _DUCKDB_PATH.exists():
            return None

        con = duckdb.connect(str(_DUCKDB_PATH), read_only=True)

        required = [
            "fact_job", "dim_company", "dim_location",
            "dim_skill", "fact_job_skill", "fact_salary",
        ]
        existing = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }

        missing = [t for t in required if t not in existing]
        if missing:
            con.close()
            return None

        tables: dict[str, pd.DataFrame] = {}
        for t in required:
            tables[t] = con.execute(f"SELECT * FROM {t}").fetchdf()

        con.close()
        return tables
    except Exception as exc:
        logger.debug("DuckDB não disponível: %s", exc)
        return None


def _try_snapshot() -> dict[str, pd.DataFrame] | None:
    """Carrega snapshot real de parquets e transforma em schema estrela.

    O snapshot é flat (tudo em jobs_snapshot + salarios_snapshot).
    Esta função cria dim_company, dim_location, dim_skill, fact_job_skill
    artificiais para manter compatibilidade com join_completo().

    Retorna None se os arquivos não existirem.
    """
    jobs_path = _SNAPSHOT_DIR / "jobs_snapshot.parquet"
    salarios_path = _SNAPSHOT_DIR / "salarios_snapshot.parquet"

    if not jobs_path.exists():
        return None

    try:
        jobs = pd.read_parquet(jobs_path)

        # ── Normalizar categorias do snapshot para o padrão do dashboard ──
        _CAT_MAP = {
            "full stack": "fullstack",
            "full-stack": "fullstack",
            "fullstack": "fullstack",
            "back-end": "backend",
            "backend": "backend",
            "front-end": "frontend",
            "frontend": "frontend",
            "dados": "dados",
            "data": "dados",
            "qa": "qa",
            "devops": "devops",
            "mobile": "mobile",
        }
        if "categoria_principal" in jobs.columns:
            jobs["categoria_principal"] = (
                jobs["categoria_principal"]
                .fillna("sem-info")
                .str.lower()
                .str.strip()
                .map(lambda c: _CAT_MAP.get(c, c))
            )

        # ── Normalizar modalidade ─────────────────────────────────────
        _MOD_MAP = {
            "remoto": "remoto",
            "remote": "remoto",
            "hibrido": "hibrido",
            "híbrido": "hibrido",
            "hybrid": "hibrido",
            "presencial": "presencial",
            "nao-informado": "hibrido",
            "não informado": "hibrido",
        }
        if "modalidade" in jobs.columns:
            jobs["modalidade"] = (
                jobs["modalidade"]
                .fillna("hibrido")
                .str.lower()
                .str.strip()
                .map(lambda m: _MOD_MAP.get(m, "hibrido"))
            )

        # ── Normalizar senioridade ────────────────────────────────────
        _SEN_MAP = {
            "estagio": "estagio",
            "estágio": "estagio",
            "intern": "estagio",
            "junior": "junior",
            "júnior": "junior",
            "pleno": "pleno",
            "mid-level": "pleno",
            "senior": "senior",
            "sênior": "senior",
            "lead": "lead",
            "lideranca": "lead",
            "liderança": "lead",
            "head": "lead",
            "gerente": "lead",
            "diretor": "lead",
            "c-level": "lead",
            "sem-info": "pleno",
        }
        if "senioridade" in jobs.columns:
            jobs["senioridade"] = (
                jobs["senioridade"]
                .fillna("pleno")
                .str.lower()
                .str.strip()
                .map(lambda s: _SEN_MAP.get(s, "pleno"))
            )

        # ── Criar job_id sequencial (snapshot não tem) ────────────────
        jobs["job_id"] = range(1, len(jobs) + 1)

        # ── dim_company ───────────────────────────────────────────────
        empresas = jobs[["empresa"]].drop_duplicates().reset_index(drop=True)
        empresas["empresa_id"] = range(1, len(empresas) + 1)
        company_map = dict(zip(empresas["empresa"], empresas["empresa_id"]))
        jobs["empresa_id"] = jobs["empresa"].map(company_map)
        dim_company = empresas.rename(columns={"empresa": "nome"})[
            ["empresa_id", "nome"]
        ]

        # ── dim_location ──────────────────────────────────────────────
        locs = jobs[["cidade", "estado"]].drop_duplicates().reset_index(drop=True)
        locs["local_id"] = range(1, len(locs) + 1)
        # Preencher cidade/estado ausentes com placeholder
        locs["cidade"] = locs["cidade"].fillna("Não informado")
        locs["estado"] = locs["estado"].fillna("NI")
        loc_map = {
            (row["cidade"], row["estado"]): row["local_id"]
            for _, row in locs.iterrows()
        }
        jobs["local_id"] = jobs.apply(
            lambda r: loc_map.get(
                (r.get("cidade") or "Não informado", r.get("estado") or "NI"), 0
            ),
            axis=1,
        )
        dim_location = locs[["local_id", "cidade", "estado"]]

        # ── dim_skill (vazio — snapshot não tem skills) ───────────────
        dim_skill = pd.DataFrame(columns=["skill_id", "nome"])
        fact_job_skill = pd.DataFrame(columns=["job_id", "skill_id"])

        # ── fact_salary (join por URL) ────────────────────────────────
        salary_df = pd.DataFrame(
            columns=["job_id", "salario_min", "salario_max", "moeda"]
        )
        if salarios_path.exists():
            salarios = pd.read_parquet(salarios_path)
            # Drop job_id do snapshot de salários para evitar conflito no merge
            cols_sal = [c for c in ["url", "salario_min", "salario_max", "moeda"]
                        if c in salarios.columns]
            salarios = salarios[cols_sal].copy()
            # Merge por URL
            salarios_merged = salarios.merge(
                jobs[["job_id", "url"]], on="url", how="left"
            )
            if not salarios_merged.empty and "job_id" in salarios_merged.columns:
                salary_df = salarios_merged[
                    ["job_id", "salario_min", "salario_max", "moeda"]
                ].copy()
                # Preencher moeda ausente
                salary_df["moeda"] = salary_df["moeda"].fillna("BRL")
                # Converter para float
                salary_df["salario_min"] = pd.to_numeric(
                    salary_df["salario_min"], errors="coerce"
                )
                salary_df["salario_max"] = pd.to_numeric(
                    salary_df["salario_max"], errors="coerce"
                )
                # Drop salários sem job_id (URL não encontrada)
                salary_df = salary_df.dropna(subset=["job_id"])

        # ── fact_job ──────────────────────────────────────────────────
        fact_job = pd.DataFrame({
            "job_id": jobs["job_id"],
            "fonte": jobs["fonte"],
            "url_original": jobs["url"],
            "titulo": jobs["titulo"],
            "senioridade": jobs["senioridade"],
            "modalidade": jobs["modalidade"],
            "publicado_em": pd.to_datetime(jobs["publicado_em"], errors="coerce"),
            "empresa_id": jobs["empresa_id"],
            "local_id": jobs["local_id"],
            "categoria_principal": jobs["categoria_principal"],
        })

        return {
            "fact_job": fact_job,
            "dim_company": dim_company,
            "dim_location": dim_location,
            "dim_skill": dim_skill,
            "fact_job_skill": fact_job_skill,
            "fact_salary": salary_df,
        }
    except Exception as exc:
        logger.warning("Erro ao carregar snapshot: %s", exc)
        return None


def _carregar_mock() -> dict[str, pd.DataFrame]:
    """Gera dados de demonstração."""
    from .mock_data import gerar_mock_jobs

    return gerar_mock_jobs()


# ── API pública ───────────────────────────────────────────────────────
def carregar_dados() -> tuple[dict[str, pd.DataFrame], FonteDados]:
    """
    Carrega dados com hierarquia de fontes.

    Retorna:
        (dados, fonte) onde:
        - dados: dict de DataFrames no formato star schema
        - fonte: enum indicando a origem dos dados
    """
    fonte = identify_source()

    if fonte == FonteDados.DUCKDB:
        duckdb_data = _try_duckdb()
        if duckdb_data is not None:
            return duckdb_data, FonteDados.DUCKDB
        # DuckDB existe mas está quebrado — cair para mock
        logger.warning("DuckDB existe mas está inacessível; usando mock")
        return _carregar_mock(), FonteDados.MOCK

    if fonte == FonteDados.SNAPSHOT:
        snapshot_data = _try_snapshot()
        if snapshot_data is not None:
            return snapshot_data, FonteDados.SNAPSHOT
        # Snapshot existe mas falhou — cair para mock
        logger.warning("Snapshot existe mas falhou ao carregar; usando mock")
        return _carregar_mock(), FonteDados.MOCK

    return _carregar_mock(), FonteDados.MOCK


def get_snapshot_meta() -> dict[str, Any]:
    """Retorna metadata do snapshot (se disponível)."""
    return _read_snapshot_meta()


# ── Normalização ──────────────────────────────────────────────────────
def join_completo(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Faz o join de fact_job com dim_company, dim_location e fact_salary
    para gerar um DataFrame pronto para análise no dashboard.

    Retorna DataFrame com colunas amigáveis em pt-BR.
    """
    fj = dados["fact_job"].copy()

    # Normalizar nome da coluna de categoria
    if "categoria" not in fj.columns and "categoria_principal" in fj.columns:
        fj = fj.rename(columns={"categoria_principal": "categoria"})

    dc = dados["dim_company"][["empresa_id", "nome"]].copy()
    dc = dc.rename(columns={"nome": "empresa"})

    dl = dados["dim_location"][["local_id", "cidade", "estado"]].copy()

    fs = (
        dados["fact_salary"][["job_id", "salario_min", "salario_max", "moeda"]].copy()
        if "fact_salary" in dados and not dados["fact_salary"].empty
        else pd.DataFrame(columns=["job_id", "salario_min", "salario_max", "moeda"])
    )

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
        "cidade": fj.get("cidade", pd.Series(dtype=str)),
        "estado": fj.get("estado", pd.Series(dtype=str)),
        "salario_min": fj["salario_min"],
        "salario_max": fj["salario_max"],
        "moeda": fj["moeda"].fillna("BRL"),
        "url": fj["url_original"],
    })

    # ── Normalização central de valores ausentes (defensivo) ──────────
    # Causa raiz do crash de produção (TypeError em sorted() com NaN misturado
    # com str). Preenchemos ANTES de expor o DataFrame ao dashboard para que
    # filtros e agrupamentos (groupby/pivot) sejam sempre consistentes.
    # Escolha documentada em normalizacao.py: exibir "não informado" em vez de
    # descartar — único caso excluído é o mapa geo (sem coordenadas).
    result["cidade"] = preencher_missing(result["cidade"])
    result["estado"] = preencher_missing(result["estado"])
    result["categoria"] = preencher_missing(result["categoria"], label="sem-info")
    # Modalidade/senioridade seguem o mapeamento padrão do snapshot
    # (ausente → valor mais comum) para não adulterar o comportamento atual.
    result["modalidade"] = preencher_missing(result["modalidade"], label="hibrido")
    result["senioridade"] = preencher_missing(result["senioridade"], label="pleno")
    result["fonte"] = preencher_missing(result["fonte"], label="desconhecida")

    return result
