"""Camada de persistência DuckDB — schema DDL, upsert, consultas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from careercompass import config

_SCHEMA_PATH = Path(__file__).parent / "tables.sql"


class Warehouse:
    """Gerencia conexão DuckDB e operações de load."""

    def __init__(self, db_path: Path | str | None = None, read_only: bool = False) -> None:
        self.db_path = str(db_path) if db_path else str(config.DUCKDB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(self.db_path, read_only=read_only)
        self._init_schema()

    def _init_schema(self) -> None:
        """Executa o DDL do schema."""
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn.execute(sql)

    # ── Upsert helpers ──────────────────────────────────────────────────

    def upsert_company(self, empresa: str, empresa_id: str | None = None) -> int:
        """Insere ou retorna company_id existente."""
        row = self.conn.execute(
            "SELECT company_id FROM dim_company WHERE empresa = ?", [empresa]
        ).fetchone()
        if row:
            return int(row[0])
        self.conn.execute(
            "INSERT INTO dim_company (empresa, empresa_orig) VALUES (?, ?)",
            [empresa, empresa_id],
        )
        row = self.conn.execute(
            "SELECT company_id FROM dim_company WHERE empresa = ?", [empresa]
        ).fetchone()
        return int(row[0]) if row else 0

    def upsert_location(self, cidade: str, estado: str | None = None) -> int:
        """Insere ou retorna location_id existente."""
        select_sql = (
            "SELECT location_id FROM dim_location "
            "WHERE cidade = ? AND COALESCE(estado, '') = COALESCE(?, '')"
        )
        row = self.conn.execute(select_sql, [cidade, estado]).fetchone()
        if row:
            return int(row[0])
        self.conn.execute(
            "INSERT INTO dim_location (cidade, estado, uf) VALUES (?, ?, ?)",
            [cidade, estado, estado],
        )
        row = self.conn.execute(select_sql, [cidade, estado]).fetchone()
        return int(row[0]) if row else 0

    def upsert_skill(self, skill_name: str, categoria: str | None = None) -> int:
        """Insere ou retorna skill_id existente."""
        row = self.conn.execute(
            "SELECT skill_id FROM dim_skill WHERE skill_name = ?", [skill_name]
        ).fetchone()
        if row:
            return int(row[0])
        self.conn.execute(
            "INSERT INTO dim_skill (skill_name, categoria) VALUES (?, ?)",
            [skill_name, categoria],
        )
        row = self.conn.execute(
            "SELECT skill_id FROM dim_skill WHERE skill_name = ?", [skill_name]
        ).fetchone()
        return int(row[0]) if row else 0

    def upsert_job(self, job: dict[str, Any]) -> int:
        """Insere job em staging + fact_job com upsert idempotente.

        Retorna job_id do fact_job.
        """
        fonte = job["fonte"]
        job_id_src = job["id"]

        # 1. Upsert staging
        self.conn.execute(
            """
            INSERT INTO staging_jobs
                (fonte, id, titulo, empresa, empresa_id, cidade, estado, url,
                 modalidade, publicado_em, salario_min, salario_max, salario_moeda,
                 salario_raw, stack_matches, stack_skills, senioridade, descricao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (fonte, id) DO UPDATE SET
                titulo = excluded.titulo,
                empresa = excluded.empresa,
                cidade = excluded.cidade,
                estado = excluded.estado,
                url = excluded.url,
                modalidade = excluded.modalidade,
                publicado_em = excluded.publicado_em,
                salario_min = excluded.salario_min,
                salario_max = excluded.salario_max,
                salario_moeda = excluded.salario_moeda,
                senioridade = excluded.senioridade,
                loaded_at = now()
            """,
            [
                fonte,
                job_id_src,
                job["titulo"],
                job.get("empresa"),
                job.get("empresa_id"),
                job.get("cidade"),
                job.get("estado"),
                job.get("url"),
                job.get("modalidade"),
                job.get("publicado_em"),
                job.get("salario_min"),
                job.get("salario_max"),
                job.get("salario_moeda"),
                job.get("salario_raw"),
                job.get("stack_matches", []),
                job.get("stack_skills", []),
                job.get("senioridade"),
                job.get("descricao"),
            ],
        )

        # 2. Upsert dim_company
        empresa_id: int | None = None
        if job.get("empresa"):
            empresa_id = self.upsert_company(job["empresa"], job.get("empresa_id"))

        # 3. Upsert dim_location
        location_id: int | None = None
        if job.get("cidade"):
            location_id = self.upsert_location(job["cidade"], job.get("estado"))

        # 4. Upsert fact_job
        url = job.get("url")
        existing = self.conn.execute(
            "SELECT job_id FROM fact_job WHERE fonte = ? AND url_original IS NOT DISTINCT FROM ?",
            [fonte, url],
        ).fetchone()

        if existing:
            fact_id = int(existing[0])
            # DuckDB não suporta UPDATE em tabela pai referenciada por FK:
            # removemos os filhos antes e reinserimos abaixo.
            self.conn.execute("DELETE FROM fact_job_skill WHERE job_id = ?", [fact_id])
            self.conn.execute("DELETE FROM fact_salary WHERE job_id = ?", [fact_id])
            self.conn.execute(
                """
                UPDATE fact_job SET
                    titulo = ?, senioridade = ?, modalidade = ?, publicado_em = ?,
                    empresa_id = ?, location_id = ?, categoria_principal = ?,
                    salario_min = ?, salario_max = ?, salario_moeda = ?, salario_raw = ?
                WHERE job_id = ?
                """,
                [
                    job["titulo"],
                    job.get("senioridade"),
                    job.get("modalidade"),
                    job.get("publicado_em"),
                    empresa_id,
                    location_id,
                    job.get("stack_matches", [None])[0] if job.get("stack_matches") else None,
                    job.get("salario_min"),
                    job.get("salario_max"),
                    job.get("salario_moeda"),
                    job.get("salario_raw"),
                    fact_id,
                ],
            )
        else:
            row = self.conn.execute(
                """
                INSERT INTO fact_job
                    (fonte, url_original, titulo, senioridade, modalidade, publicado_em,
                     empresa_id, location_id, categoria_principal, salario_min, salario_max,
                     salario_moeda, salario_raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING job_id
                """,
                [
                    fonte,
                    url,
                    job["titulo"],
                    job.get("senioridade"),
                    job.get("modalidade"),
                    job.get("publicado_em"),
                    empresa_id,
                    location_id,
                    job.get("stack_matches", [None])[0] if job.get("stack_matches") else None,
                    job.get("salario_min"),
                    job.get("salario_max"),
                    job.get("salario_moeda"),
                    job.get("salario_raw"),
                ],
            ).fetchone()
            fact_id = int(row[0]) if row else 0

        # 5. Upsert fact_job_skill
        for skill_name in job.get("stack_skills", []):
            # Descobrir categoria da skill
            categoria = None
            from careercompass.processing.normalizer import _STACK_KEYWORDS

            for cat, keywords in _STACK_KEYWORDS.items():
                if skill_name in keywords:
                    categoria = cat
                    break

            skill_id = self.upsert_skill(skill_name, categoria)
            self.conn.execute(
                """
                INSERT INTO fact_job_skill (job_id, skill_id)
                VALUES (?, ?)
                ON CONFLICT (job_id, skill_id) DO NOTHING
                """,
                [fact_id, skill_id],
            )

        # 6. Upsert fact_salary (só se tiver salário)
        if job.get("salario_min") is not None or job.get("salario_max") is not None:
            self.conn.execute(
                """
                INSERT INTO fact_salary (job_id, salario_min, salario_max, salario_moeda)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (job_id) DO UPDATE SET
                    salario_min = excluded.salario_min,
                    salario_max = excluded.salario_max,
                    salario_moeda = excluded.salario_moeda
                """,
                [fact_id, job.get("salario_min"), job.get("salario_max"), job.get("salario_moeda")],
            )

        return fact_id

    # ── Consultas de relatório ──────────────────────────────────────────

    def count_by_fonte(self) -> list[dict[str, Any]]:
        """Conta vagas por fonte na staging."""
        rows = self.conn.execute(
            "SELECT fonte, COUNT(*) as total FROM staging_jobs GROUP BY fonte ORDER BY total DESC"
        ).fetchall()
        return [{"fonte": r[0], "total": r[1]} for r in rows]

    def _scalar(self, sql: str, params: list[Any] | None = None) -> int:
        """Executa query de agregação e retorna valor inteiro."""
        row = self.conn.execute(sql, params or []).fetchone()
        return int(row[0]) if row else 0

    def salary_coverage(self) -> dict[str, Any]:
        """Cobertura salarial: quantas vagas têm salário vs total."""
        total = self._scalar("SELECT COUNT(*) FROM fact_job")
        with_salary = self._scalar(
            "SELECT COUNT(*) FROM fact_job WHERE salario_min IS NOT NULL OR salario_max IS NOT NULL"
        )
        return {
            "total_vagas": total,
            "com_salario": with_salary,
            "cobertura_pct": round(with_salary / total * 100, 1) if total > 0 else 0,
        }

    def summary(self) -> dict[str, Any]:
        """Resumo geral do warehouse."""
        return {
            "por_fonte": self.count_by_fonte(),
            "cobertura_salarial": self.salary_coverage(),
            "total_empresas": self._scalar("SELECT COUNT(*) FROM dim_company"),
            "total_locations": self._scalar("SELECT COUNT(*) FROM dim_location"),
            "total_skills": self._scalar("SELECT COUNT(*) FROM dim_skill"),
        }

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Warehouse:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
