"""Exporta snapshot versionável do DuckDB para Parquet commitável.

Gera:
  - data/snapshot/jobs_snapshot.parquet   (~500 linhas, amostra reprodutível)
  - data/snapshot/salarios_snapshot.parquet (todas as vagas com salário)
  - data/snapshot/meta.yaml               (metadados da geração)

Uso:
  python -m careercompass.export_snapshot
  python -m careercompass.export_snapshot --max-rows 200 --seed 42
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TypedDict

import duckdb

from careercompass import config

SNAPSHOT_DIR = config.DATA_DIR / "snapshot"
DEFAULT_MAX_ROWS = 500
DEFAULT_SEED = 42


class FonteCount(TypedDict):
    fonte: str
    total: int


class SnapshotResult(TypedDict):
    snapshot_dir: str
    jobs_path: str
    salarios_path: str
    meta_path: str
    jobs_rows: int
    salarios_rows: int
    jobs_columns: list[str]
    salarios_columns: list[str]
    jobs_kb: float
    salarios_kb: float
    meta_kb: float
    total_kb: float
    total_vagas: int
    com_salario: int
    cobertura_pct: float
    por_fonte: list[FonteCount]


# ── SQL ───────────────────────────────────────────────────────────────────

_JOBS_SQL = """
SELECT
    f.fonte,
    f.titulo,
    f.categoria_principal,
    f.senioridade,
    f.modalidade,
    l.cidade,
    l.estado,
    c.empresa,
    f.publicado_em,
    f.url_original   AS url
FROM fact_job f
LEFT JOIN dim_company c ON f.empresa_id  = c.company_id
LEFT JOIN dim_location l ON f.location_id = l.location_id
ORDER BY f.fonte, f.job_id
"""

_SALARIOS_SQL = """
SELECT
    f.url_original   AS url,
    f.job_id,
    f.salario_min,
    f.salario_max,
    f.salario_moeda  AS moeda
FROM fact_job f
WHERE f.salario_min IS NOT NULL
   OR f.salario_max IS NOT NULL
ORDER BY f.fonte, f.job_id
"""

_COUNT_BY_FONTE_SQL = """
SELECT fonte, COUNT(*) AS total
FROM fact_job
GROUP BY fonte
ORDER BY total DESC
"""

_SALARY_COVERAGE_SQL = """
SELECT
    COUNT(*)                                                     AS total,
    SUM(CASE WHEN salario_min IS NOT NULL OR salario_max IS NOT NULL
             THEN 1 ELSE 0 END)                                  AS com_salario
FROM fact_job
"""


# ── Helpers ───────────────────────────────────────────────────────────────


def _duckdb_path() -> Path:
    """Retorna o path do DuckDB; levanta FileNotFoundError se não existir."""
    path = config.DUCKDB_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB não encontrado em {path}. "
            "Execute o pipeline antes: python -m careercompass.pipeline "
            "--max-pages 2"
        )
    return path


def _write_meta(
    *,
    snapshot_dir: Path,
    jobs_count: int,
    salarios_count: int,
    fontes: list[FonteCount],
    total_vagas: int,
    com_salario: int,
    seed: int,
    max_rows: int,
) -> Path:
    """Escreve meta.yaml como texto simples (sem dependência pyyaml)."""
    cobertura = round(com_salario / total_vagas * 100, 1) if total_vagas > 0 else 0.0
    today = date.today().isoformat()

    lines = [
        "# CareerCompass BR — Snapshot metadata",
        "# GERADO POR export_snapshot — dados reais do DuckDB",
        "# NÃO editar manualmente (regenerar com: python -m careercompass.export_snapshot)",
        "",
        f'data_geracao: "{today}"',
        f"seed: {seed}",
        f"max_rows: {max_rows}",
        f"jobs_snapshot_linhas: {jobs_count}",
        f"salarios_snapshot_linhas: {salarios_count}",
        "",
        "# Contagens por fonte (total no DuckDB)",
        "fontes:",
    ]
    for f in fontes:
        lines.append(f"  {f['fonte']}: {f['total']}")

    lines.extend(
        [
            "",
            "# Cobertura salarial",
            f"total_vagas: {total_vagas}",
            f"com_salario: {com_salario}",
            f"cobertura_salarial_pct: {cobertura}",
            "",
            "# Colunas jobs_snapshot.parquet",
            "#   fonte, titulo, categoria_principal, senioridade, modalidade,",
            "#   cidade, estado, empresa, publicado_em, url",
            "",
            "# Colunas salarios_snapshot.parquet",
            "#   url, job_id, salario_min, salario_max, moeda",
        ]
    )

    meta_path = snapshot_dir / "meta.yaml"
    meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return meta_path


# ── Core ──────────────────────────────────────────────────────────────────


def export_snapshot(
    *,
    max_rows: int = DEFAULT_MAX_ROWS,
    seed: int = DEFAULT_SEED,
) -> SnapshotResult:
    """Gera os arquivos de snapshot e retorna um resumo.

    Raises:
        FileNotFoundError: se o DuckDB não existir.
    """
    db_path = _duckdb_path()

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        # ── Contagens ──────────────────────────────────────────────────────
        fontes: list[FonteCount] = [
            {"fonte": r[0], "total": r[1]} for r in con.execute(_COUNT_BY_FONTE_SQL).fetchall()
        ]
        cov = con.execute(_SALARY_COVERAGE_SQL).fetchone()
        total_vagas: int = int(cov[0]) if cov else 0
        com_salario: int = int(cov[1]) if cov else 0

        # ── Jobs snapshot (amostra reprodutível) ──────────────────────────
        all_jobs_df = con.execute(_JOBS_SQL).fetchdf()
        total_available = len(all_jobs_df)

        if total_available > max_rows:
            jobs_df = all_jobs_df.sample(n=max_rows, random_state=seed).reset_index(drop=True)
        else:
            jobs_df = all_jobs_df

        # ── Salários snapshot (todas as linhas — geralmente poucas) ───────
        salarios_df = con.execute(_SALARIOS_SQL).fetchdf()
    finally:
        con.close()

    # ── Escrever arquivos ──────────────────────────────────────────────────
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    jobs_path = SNAPSHOT_DIR / "jobs_snapshot.parquet"
    salarios_path = SNAPSHOT_DIR / "salarios_snapshot.parquet"

    jobs_df.to_parquet(jobs_path, index=False, engine="pyarrow")
    salarios_df.to_parquet(salarios_path, index=False, engine="pyarrow")

    meta_path = _write_meta(
        snapshot_dir=SNAPSHOT_DIR,
        jobs_count=len(jobs_df),
        salarios_count=len(salarios_df),
        fontes=fontes,
        total_vagas=total_vagas,
        com_salario=com_salario,
        seed=seed,
        max_rows=max_rows,
    )

    # ── Tamanhos ──────────────────────────────────────────────────────────
    jobs_kb = jobs_path.stat().st_size / 1024
    salarios_kb = salarios_path.stat().st_size / 1024
    meta_kb = meta_path.stat().st_size / 1024
    total_kb = jobs_kb + salarios_kb + meta_kb

    return SnapshotResult(
        snapshot_dir=str(SNAPSHOT_DIR),
        jobs_path=str(jobs_path),
        salarios_path=str(salarios_path),
        meta_path=str(meta_path),
        jobs_rows=len(jobs_df),
        salarios_rows=len(salarios_df),
        jobs_columns=list(jobs_df.columns),
        salarios_columns=list(salarios_df.columns),
        jobs_kb=round(jobs_kb, 1),
        salarios_kb=round(salarios_kb, 1),
        meta_kb=round(meta_kb, 1),
        total_kb=round(total_kb, 1),
        total_vagas=total_vagas,
        com_salario=com_salario,
        cobertura_pct=(round(com_salario / total_vagas * 100, 1) if total_vagas > 0 else 0),
        por_fonte=fontes,
    )


# ── CLI ───────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point para `python -m careercompass.export_snapshot`."""
    parser = argparse.ArgumentParser(
        description="Gera snapshot versionável do DuckDB para Parquet."
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=DEFAULT_MAX_ROWS,
        help=f"Máximo de linhas em jobs_snapshot (default: {DEFAULT_MAX_ROWS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Seed para amostra reprodutível (default: {DEFAULT_SEED})",
    )
    args = parser.parse_args()

    try:
        result = export_snapshot(max_rows=args.max_rows, seed=args.seed)
    except FileNotFoundError as exc:
        print(f"[export_snapshot] ERRO: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[export_snapshot] Snapshot gerado em: {result['snapshot_dir']}")
    print(f"  jobs_snapshot.parquet:     {result['jobs_rows']} linhas, {result['jobs_kb']} KB")
    print(
        f"  salarios_snapshot.parquet: {result['salarios_rows']} linhas, {result['salarios_kb']} KB"
    )
    print(f"  meta.yaml:                {result['meta_kb']} KB")
    print(f"  Total:                    {result['total_kb']} KB")
    print(
        f"  Cobertura salarial:       "
        f"{result['cobertura_pct']}% "
        f"({result['com_salario']}/{result['total_vagas']})"
    )
    for fc in result["por_fonte"]:
        print(f"  Fonte {fc['fonte']}: {fc['total']} vagas no DW")


if __name__ == "__main__":
    main()
