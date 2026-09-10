"""Pipeline ETL orquestrador — coleta → normaliza → carrega → relatório."""

from __future__ import annotations

import sys
from datetime import date
from typing import Any

from careercompass import config
from careercompass.ingestion.base import Collector
from careercompass.ingestion.geekhunter import GeekHunterCollector
from careercompass.ingestion.gupy import GupyCollector
from careercompass.ingestion.programathor import ProgramathorCollector
from careercompass.processing.dedup import dedup_jobs, dedup_stats
from careercompass.processing.normalizer import normalize_job
from careercompass.warehouse.duckdb import Warehouse


def _run_collectors(max_pages: int) -> tuple[list[dict[str, Any]], list[str]]:
    """Roda todos os coletores e retorna lista de jobs normalizados."""
    collectors: list[Collector] = [
        GupyCollector(),
        GeekHunterCollector(),
        ProgramathorCollector(),
    ]

    all_jobs: list[dict[str, Any]] = []
    errors: list[str] = []

    for collector in collectors:
        try:
            raw_jobs = collector.collect(max_pages=max_pages)
            collector.save_raw(raw_jobs)
            normalized = [normalize_job(j) for j in raw_jobs]
            all_jobs.extend(normalized)
        except Exception as e:
            errors.append(f"{collector.nome}: {e}")

    return all_jobs, errors


def _generate_report(
    jobs: list[dict[str, Any]],
    errors: list[str],
    dedup_info: dict[str, int],
    warehouse_summary: dict[str, Any],
) -> str:
    """Gera relatório markdown do pipeline."""
    today = date.today().strftime("%Y-%m-%d")
    lines = [
        f"# Relatório do Pipeline — {today}\n",
        "## Coleta",
        "",
    ]

    # Contagens por fonte
    by_fonte: dict[str, int] = {}
    for j in jobs:
        by_fonte[j["fonte"]] = by_fonte.get(j["fonte"], 0) + 1

    for fonte, count in sorted(by_fonte.items()):
        lines.append(f"- **{fonte}**: {count} vagas")

    lines.extend(
        [
            f"\n**Total após normalização**: {len(jobs)} vagas",
            "",
            "## Deduplicação",
            "",
            f"- Antes: {dedup_info['total_antes']}",
            f"- Depois: {dedup_info['total_depois']}",
            f"- Duplicatas removidas: {dedup_info['duplicatas_removidas']}",
            "",
            "## Warehouse",
            "",
        ]
    )

    for key, val in warehouse_summary.items():
        lines.append(f"- **{key}**: {val}")

    # Cobertura salarial
    sal = warehouse_summary.get("cobertura_salarial", {})
    lines.extend(
        [
            "",
            "## Cobertura Salarial",
            "",
            f"- Total de vagas: {sal.get('total_vagas', 0)}",
            f"- Com salário: {sal.get('com_salario', 0)}",
            f"- Cobertura: {sal.get('cobertura_pct', 0)}%",
            "",
            "> **Disclaimer**: dados coletados de fontes públicas. "
            "A cobertura salarial é limitada (~20-40% das vagas expõem salário). "
            "Não substitui pesquisa salarial formal.",
            "",
        ]
    )

    # Erros
    if errors:
        lines.extend(["## Erros", ""])
        for err in errors:
            lines.append(f"- {err}")

    return "\n".join(lines)


def run(max_pages: int | None = None) -> dict[str, Any]:
    """Executa o pipeline completo.

    Returns:
        Dict com estatísticas para uso externo.
    """
    pages = max_pages or config.MAX_PAGES

    print(f"[Pipeline] Iniciando coleta (max_pages={pages})...")

    # 1. Coleta + normalização
    all_jobs, errors = _run_collectors(pages)
    print(f"[Pipeline] {len(all_jobs)} vagas coletadas, {len(errors)} erros")

    # 2. Deduplicação
    unique_jobs = dedup_jobs(all_jobs)
    dedup_info = dedup_stats(len(all_jobs), len(unique_jobs))
    print(f"[Pipeline] {dedup_info['duplicatas_removidas']} duplicatas removidas")

    # 3. Load no warehouse
    wh = Warehouse()
    try:
        for job in unique_jobs:
            try:
                wh.upsert_job(job)
            except Exception as e:
                errors.append(f"warehouse upsert {job['fonte']}:{job['id']}: {e}")

        summary = wh.summary()
    finally:
        wh.close()

    # 4. Relatório
    report = _generate_report(unique_jobs, errors, dedup_info, summary)
    report_path = config.REPORTS_DIR / f"pipeline-report-{date.today():%Y%m%d}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"[Pipeline] Relatório salvo em {report_path}")

    return {
        "vagas_total": len(all_jobs),
        "vagas_unicas": len(unique_jobs),
        "duplicatas": dedup_info["duplicatas_removidas"],
        "erros": errors,
        "por_fonte": dedup_info,
        "report_path": str(report_path),
    }


def main() -> None:
    """Entry point para execução via CLI."""
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else None
    result = run(max_pages)
    print(f"\n[Pipeline] Concluído: {result['vagas_unicas']} vagas únicas carregadas.")
    if result["erros"]:
        print(f"[Pipeline] {len(result['erros'])} erro(s) durante execução.")


if __name__ == "__main__":
    main()
