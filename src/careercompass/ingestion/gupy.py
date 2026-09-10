"""Coletor da Gupy — página pública de vagas (SSR com __NEXT_DATA__).

A antiga API pública (portal.api.gupy.io) foi descontinuada (404).
O portal expõe hoje /job-search/{query} com dados iniciais embutidos em
`__NEXT_DATA__.props.pageProps.initialJobList` (sem auth).
Limitação documentada: sem token, apenas a primeira página (12 vagas/query).
"""

from __future__ import annotations

import json
import re
from typing import Any

from careercompass import config
from careercompass.ingestion.base import Collector, RawJob

_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)

_MODALIDADE_MAP = {
    "remote": "remoto",
    "on-site": "presencial",
    "on_site": "presencial",
    "hybrid": "hibrido",
    "presential": "presencial",
}


class GupyCollector(Collector):
    """Coleta vagas do portal público da Gupy."""

    nome = "gupy"

    # Queries amplas para maximizar cobertura (12 vagas cada, sem auth)
    QUERIES: list[str] = ["analista", "desenvolvedor", "dados"]

    def collect(self, max_pages: int = config.MAX_PAGES) -> list[RawJob]:
        jobs: list[RawJob] = []

        for query in self.QUERIES[:max_pages]:
            url = f"{config.GUPY_BASE_URL}/{query}"
            resp = self._get(url)

            if resp.status_code != 200:
                continue

            page_jobs = self._parse_page(resp.text)
            jobs.extend(page_jobs)

        return jobs

    def _parse_page(self, html: str) -> list[RawJob]:
        """Extrai vagas do HTML SSR (__NEXT_DATA__ → initialJobList)."""
        m = _NEXT_DATA_RE.search(html)
        if not m:
            return []

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return []

        page_props = data.get("props", {}).get("pageProps", {})
        job_list = page_props.get("initialJobList", {})
        items = job_list.get("data", [])

        return [self._parse_job(item) for item in items if isinstance(item, dict)]

    def _parse_job(self, item: dict[str, Any]) -> RawJob:
        return RawJob(
            fonte=self.nome,
            id=str(item.get("id", "")),
            titulo=item.get("name", ""),
            empresa=item.get("careerPageName"),
            empresa_id=str(item.get("careerPageUrl", "")) if item.get("careerPageUrl") else None,
            cidade=item.get("city"),
            estado=item.get("state"),
            url=item.get("jobUrl"),
            modalidade=_MODALIDADE_MAP.get((item.get("workplaceType") or "").lower()),
            publicado_em=item.get("publishedDate"),
            descricao=item.get("description"),
        )
