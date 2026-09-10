"""Coletor da GeekHunter — JSON-LD ItemList da listagem pública.

A listagem (https://www.geekhunter.com.br/vagas) expõe ItemList com
name + url por vaga (25/página, paginação ?page=N).
Observação honesta: baseSalary (JobPosting) só existe na página individual
da vaga; o parser aceita JobPosting quando presente (coleta v1 = listagem).
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from careercompass import config
from careercompass.ingestion.base import Collector, RawJob

_EMPRESA_RE = re.compile(r"/pt/([^/]+)/jobs/", re.IGNORECASE)


class GeekHunterCollector(Collector):
    """Coleta vagas da GeekHunter via JSON-LD (ItemList) da listagem."""

    nome = "geekhunter"

    def collect(self, max_pages: int = config.MAX_PAGES) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(1, max_pages + 1):
            url = f"{config.GEEKHUNTER_URL}?page={page}"
            resp = self._get(url)
            if resp.status_code != 200:
                break
            page_jobs = self._parse_page(resp.text)
            if not page_jobs:
                break
            jobs.extend(page_jobs)
        return jobs

    def _parse_page(self, html: str) -> list[RawJob]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[RawJob] = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            jobs.extend(self._extract_from_jsonld(data))

        return jobs

    def _extract_from_jsonld(self, data: Any) -> list[RawJob]:
        """Extrai vagas de JSON-LD (ItemList → ListItem ou JobPosting direto)."""
        jobs: list[RawJob] = []

        if isinstance(data, list):
            for item in data:
                jobs.extend(self._extract_from_jsonld(item))
            return jobs

        if not isinstance(data, dict):
            return jobs

        if data.get("@type") == "ItemList":
            for item in data.get("itemListElement", []):
                if isinstance(item, dict):
                    parsed = self._parse_list_item(item)
                    if parsed:
                        jobs.append(parsed)

        if data.get("@type") == "JobPosting":
            parsed = self._parse_job_posting(data)
            if parsed:
                jobs.append(parsed)

        for item in data.get("@graph", []):
            jobs.extend(self._extract_from_jsonld(item))

        return jobs

    def _parse_list_item(self, item: dict[str, Any]) -> RawJob | None:
        """ItemList → ListItem com name (título) + url."""
        title = item.get("name")
        url = item.get("url")
        if not title:
            return None

        empresa = None
        if url:
            m = _EMPRESA_RE.search(url)
            if m:
                empresa = m.group(1).replace("-", " ").strip().title()

        return RawJob(
            fonte=self.nome,
            id=str(url or title),
            titulo=title,
            empresa=empresa,
            url=url,
        )

    def _parse_job_posting(self, item: dict[str, Any]) -> RawJob | None:
        """JobPosting com baseSalary estruturado (página individual da vaga)."""
        title = item.get("name")
        if not title:
            return None

        company = item.get("hiringOrganization", {})
        if isinstance(company, dict):
            company_name = company.get("name")
        else:
            company_name = None

        location = item.get("jobLocation", {})
        if isinstance(location, dict):
            address = location.get("address", {})
        elif isinstance(location, list) and location and isinstance(location[0], dict):
            address = location[0].get("address", {})
        else:
            address = {}

        salary = item.get("baseSalary", {})
        salary_min, salary_max, moeda = None, None, None
        if isinstance(salary, dict):
            val = salary.get("value", {})
            if isinstance(val, dict):
                salary_min = val.get("minValue")
                salary_max = val.get("maxValue")
                moeda = salary.get("currency")
        elif isinstance(salary, list) and salary and isinstance(salary[0], dict):
            val = salary[0].get("value", {})
            if isinstance(val, dict):
                salary_min = val.get("minValue")
                salary_max = val.get("maxValue")
                moeda = salary[0].get("currency")

        # Modalidade a partir da descrição
        desc = (item.get("description") or "").lower()
        modalidade = None
        if "remot" in desc:
            modalidade = "remoto"
        elif "híbrid" in desc or "hibrid" in desc or "hybrid" in desc:
            modalidade = "hibrido"
        elif "presencial" in desc or "on-site" in desc:
            modalidade = "presencial"

        url = item.get("url")

        return RawJob(
            fonte=self.nome,
            id=str(url or title),
            titulo=title,
            empresa=company_name,
            cidade=address.get("addressLocality") if isinstance(address, dict) else None,
            estado=address.get("addressRegion") if isinstance(address, dict) else None,
            url=url,
            modalidade=modalidade,
            publicado_em=item.get("datePosted"),
            salario_min=salary_min,
            salario_max=salary_max,
            salario_moeda=moeda,
            descricao=item.get("description"),
        )
