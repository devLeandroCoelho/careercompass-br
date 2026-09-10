"""Testes dos parsers de cada fonte de dados."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from careercompass.ingestion.base import RawJob
from careercompass.ingestion.geekhunter import GeekHunterCollector
from careercompass.ingestion.gupy import GupyCollector
from careercompass.ingestion.programathor import ProgramathorCollector

FIXTURES = Path(__file__).parent / "fixtures"


# ── Gupy ───────────────────────────────────────────────────────────────


class TestGupyCollector:
    """Testes do parser da Gupy (SSR __NEXT_DATA__ → initialJobList)."""

    def test_parse_job_basic(self) -> None:
        collector = GupyCollector()
        item = {
            "id": 10001,
            "name": "Analista de Dados Jr",
            "jobUrl": "https://empresa.gupy.io/job/abc",
            "publishedDate": "2026-09-01T14:00:00.000Z",
            "workplaceType": "remote",
            "description": "Vaga para analista de dados com Python e SQL",
            "city": "São Paulo",
            "state": "São Paulo",
            "careerPageName": "TechCorp",
            "careerPageUrl": "https://techcorp.gupy.io",
        }
        job = collector._parse_job(item)

        assert isinstance(job, RawJob)
        assert job.fonte == "gupy"
        assert job.id == "10001"
        assert job.titulo == "Analista de Dados Jr"
        assert job.empresa == "TechCorp"
        assert job.cidade == "São Paulo"
        assert job.estado == "São Paulo"
        assert job.modalidade == "remoto"
        assert job.url == "https://empresa.gupy.io/job/abc"

    def test_parse_job_no_company(self) -> None:
        collector = GupyCollector()
        item = {"id": 2, "name": "Dev", "workplaceType": "on-site"}
        job = collector._parse_job(item)
        assert job.empresa is None
        assert job.modalidade == "presencial"

    def test_map_modalidade(self) -> None:
        item = {"id": 3, "name": "X", "workplaceType": "hybrid"}
        assert GupyCollector()._parse_job(item).modalidade == "hibrido"

    def test_parse_page_from_ssr(self) -> None:
        """Extrai vagas do HTML SSR com __NEXT_DATA__."""
        html = FIXTURES / "gupy_ssr_page.html"
        if not html.exists():
            # Fallback: monta HTML mínimo em memória
            import json

            payload = {
                "props": {
                    "pageProps": {
                        "initialJobList": {
                            "data": [
                                {
                                    "id": 1,
                                    "name": "Analista de Dados",
                                    "workplaceType": "remote",
                                    "city": "São Paulo",
                                    "state": "São Paulo",
                                    "careerPageName": "Co",
                                }
                            ],
                            "pagination": {"total": 1, "limit": 12, "offset": 0},
                        }
                    }
                }
            }
            json_payload = json.dumps(payload)
            html_str = (
                '<html><body><script id="__NEXT_DATA__" type="application/json">'
                f"{json_payload}</script></body></html>"
            )
        else:
            html_str = html.read_text(encoding="utf-8")

        collector = GupyCollector()
        jobs = collector._parse_page(html_str)
        assert len(jobs) == 1
        assert jobs[0].titulo == "Analista de Dados"


# ── GeekHunter ─────────────────────────────────────────────────────────


class TestGeekHunterCollector:
    """Testes do parser da GeekHunter (ItemList + JobPosting)."""

    def test_parse_jsonld_itemlist(self) -> None:
        html = FIXTURES / "geekhunter_page.html"
        content = html.read_text(encoding="utf-8")
        collector = GeekHunterCollector()
        jobs = collector._parse_page(content)

        # 2 itens do ItemList + 1 JobPosting
        assert len(jobs) == 3

        # ItemList → título + url + empresa (slug da url)
        assert jobs[0].titulo == "Analista de Dados Senior"
        assert jobs[0].empresa == "Startupbr"
        assert (
            jobs[0].url
            == "https://www.geekhunter.com.br/pt/startupbr/jobs/analista-de-dados-senior"
        )

    def test_parse_jobposting_salary(self) -> None:
        html = FIXTURES / "geekhunter_page.html"
        content = html.read_text(encoding="utf-8")
        collector = GeekHunterCollector()
        jobs = collector._parse_page(content)

        # JobPosting com baseSalary estruturado
        posting = next(j for j in jobs if j.titulo == "Cientista de Dados Remoto")
        assert posting.empresa == "DataFlow"
        assert posting.cidade == "Curitiba"
        assert posting.estado == "PR"
        assert posting.salario_min == 9000.0
        assert posting.salario_max == 14000.0
        assert posting.salario_moeda == "BRL"
        assert posting.modalidade == "remoto"

    def test_parse_empty_html(self) -> None:
        collector = GeekHunterCollector()
        jobs = collector._parse_page("<html><body></body></html>")
        assert jobs == []

    def test_parse_cards_fallback_removed(self) -> None:
        """Sem JSON-LD, não retorna vagas (listagem sem dados)."""
        collector = GeekHunterCollector()
        jobs = collector._parse_page("<html><body><div class='job-card'>x</div></body></html>")
        assert jobs == []


# ── Programathor ───────────────────────────────────────────────────────


class TestProgramathorCollector:
    """Testes do parser da Programathor (div.cell-list)."""

    def test_parse_cards(self) -> None:
        html = FIXTURES / "programathor_page.html"
        content = html.read_text(encoding="utf-8")
        collector = ProgramathorCollector()
        jobs = collector._parse_page(content)

        assert len(jobs) == 3

    def test_parse_first_card(self) -> None:
        html = FIXTURES / "programathor_page.html"
        content = html.read_text(encoding="utf-8")
        collector = ProgramathorCollector()
        jobs = collector._parse_page(content)

        j = jobs[0]
        assert j.titulo == "Desenvolvedor Back-End Senior (AI Engineer)"
        assert j.empresa == "LOLDESIGN Soluções Digitais LTDA"
        assert j.modalidade == "remoto"
        # tags viram descricao para o normalizador
        assert "python" in (j.descricao or "").lower()
        assert j.salario_min is None

    def test_parse_card_with_salary(self) -> None:
        html = FIXTURES / "programathor_page.html"
        content = html.read_text(encoding="utf-8")
        collector = ProgramathorCollector()
        jobs = collector._parse_page(content)

        j = jobs[1]
        assert j.titulo == "Analista de Dados Pleno"
        assert j.cidade == "Campinas, SP"
        assert j.salario_min == 5000.0
        assert j.salario_max == 7000.0
        assert j.salario_moeda == "BRL"

    def test_parse_card_salary_ate(self) -> None:
        html = FIXTURES / "programathor_page.html"
        content = html.read_text(encoding="utf-8")
        collector = ProgramathorCollector()
        jobs = collector._parse_page(content)

        j = jobs[2]
        assert j.titulo == "Estagiário de Dados"
        assert j.salario_min == 2000.0
        assert j.salario_max is None

    def test_parse_salary_extraction(self) -> None:
        from careercompass.ingestion.programathor import _parse_salario

        # Range
        min_val, max_val, moeda = _parse_salario("R$ 4.000 - R$ 6.000")
        assert min_val == 4000.0
        assert max_val == 6000.0
        assert moeda == "BRL"

        # Até
        min_val, max_val, moeda = _parse_salario("até R$2.000")
        assert min_val == 2000.0
        assert max_val is None

        # Sem salário
        min_val, max_val, moeda = _parse_salario("A combinar")
        assert min_val is None
        assert max_val is None
        assert moeda is None

    def test_collect_with_mock(self) -> None:
        collector = ProgramathorCollector()
        with patch.object(collector, "_get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = (FIXTURES / "programathor_page.html").read_text(encoding="utf-8")
            mock_get.return_value = mock_resp
            jobs = collector.collect(max_pages=1)
            assert isinstance(jobs, list)
