"""Testes do pipeline — integração ponta a ponta com mocks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from careercompass.pipeline import _generate_report, _run_collectors


class TestPipelineReport:
    """Testes de geração de relatório."""

    def test_generate_report(self, tmp_path: Path) -> None:
        from careercompass import config

        original = config.REPORTS_DIR
        config.REPORTS_DIR = tmp_path

        try:
            jobs = [
                {"fonte": "gupy", "titulo": "Analista", "senioridade": "junior"},
                {"fonte": "geekhunter", "titulo": "Dev", "senioridade": "pleno"},
            ]
            dedup_info = {"total_antes": 10, "total_depois": 8, "duplicatas_removidas": 2}
            warehouse_summary = {
                "por_fonte": [{"fonte": "gupy", "total": 5}],
                "cobertura_salarial": {"total_vagas": 8, "com_salario": 3, "cobertura_pct": 37.5},
                "total_empresas": 5,
                "total_locations": 3,
                "total_skills": 10,
            }
            report = _generate_report(jobs, [], dedup_info, warehouse_summary)
            assert "gupy" in report
            assert "Deduplicação" in report
            assert "Disclaimer" in report
        finally:
            config.REPORTS_DIR = original


class TestPipelineCollectors:
    """Teste de integração dos coletores via _run_collectors."""

    def test_run_collectors_with_mocks(self, tmp_path: Path) -> None:
        from careercompass import config

        original_raw = config.RAW_DIR
        config.RAW_DIR = tmp_path

        try:
            with (
                patch("careercompass.pipeline.GupyCollector") as MockGupy,
                patch("careercompass.pipeline.GeekHunterCollector") as MockGH,
                patch("careercompass.pipeline.ProgramathorCollector") as MockPT,
            ):
                # Gupy retorna 1 vaga
                gupy_instance = MockGupy.return_value
                gupy_instance.collect.return_value = [
                    MagicMock(
                        fonte="gupy",
                        id="1",
                        titulo="Analista",
                        empresa="Co",
                        empresa_id="1",
                        cidade="SP",
                        estado="SP",
                        url="https://a.com/1",
                        modalidade="remoto",
                        publicado_em="2026-09-01",
                        salario_raw=None,
                        salario_min=None,
                        salario_max=None,
                        salario_moeda=None,
                        descricao="Python SQL",
                    )
                ]
                gupy_instance.save_raw.return_value = tmp_path / "gupy.jsonl"

                # GeekHunter retorna 1 vaga
                gh_instance = MockGH.return_value
                gh_instance.collect.return_value = [
                    MagicMock(
                        fonte="geekhunter",
                        id="gh1",
                        titulo="Dev",
                        empresa=None,
                        empresa_id=None,
                        cidade=None,
                        estado=None,
                        url="https://b.com/1",
                        modalidade=None,
                        publicado_em=None,
                        salario_raw=None,
                        salario_min=5000.0,
                        salario_max=8000.0,
                        salario_moeda="BRL",
                        descricao=None,
                    )
                ]
                gh_instance.save_raw.return_value = tmp_path / "gh.jsonl"

                # Programathor retorna 0 vagas
                pt_instance = MockPT.return_value
                pt_instance.collect.return_value = []
                pt_instance.save_raw.return_value = tmp_path / "pt.jsonl"

                jobs, errors = _run_collectors(max_pages=1)
                assert len(jobs) == 2
                assert len(errors) == 0
        finally:
            config.RAW_DIR = original_raw
