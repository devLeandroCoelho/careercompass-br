"""Coletor da Programathor — parsing HTML de cards (div.cell-list).

Estrutura atual (2026): cada vaga é um <div class="cell-list"> com link
<a href="/jobs/{id}-{slug}">, título em h3, empresa/local/contrato/senioridade
em spans com ícones, e tags de stack em .tag-list.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from careercompass import config
from careercompass.ingestion.base import Collector, RawJob, _as_url

# Regex para salário free-text: "R$ 3.000", "R$ 4.000 - R$ 6.000", "até R$2.000"
_SALARIO_RE = re.compile(
    r"R\$\s*([\d.]+(?:,\d{2})?)"  # valor base
    r"(?:\s*[-a]\s*R\$\s*([\d.]+(?:,\d{2})?))?"  # faixa: " - R$ max" / " a R$ max"
)

_MODALIDADE_VALUES = {"remoto", "híbrido", "hibrido", "presencial"}


def _parse_salario(text: str) -> tuple[float | None, float | None, str | None]:
    """Extrai salário de texto livre. Retorna (min, max, moeda)."""
    match = _SALARIO_RE.search(text)
    if not match:
        return None, None, None

    def to_float(v: str | None) -> float | None:
        if not v:
            return None
        return float(v.replace(".", "").replace(",", "."))

    return to_float(match.group(1)), to_float(match.group(2)), "BRL"


class ProgramathorCollector(Collector):
    """Coleta vagas da Programathor via parsing HTML da listagem."""

    nome = "programathor"

    def collect(self, max_pages: int = config.MAX_PAGES) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(1, max_pages + 1):
            url = f"{config.PROGRAMATHOR_URL}?page={page}"
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

        cards = soup.select("div.cell-list")
        if not cards:
            cards = soup.select("a[href*='/jobs/']")

        for card in cards:
            parsed = self._parse_card(card)
            if parsed:
                jobs.append(parsed)

        return jobs

    def _parse_card(self, card: Tag) -> RawJob | None:
        # Título
        title_el = card.select_one("h3, h2")
        if not title_el:
            return None
        titulo = title_el.get_text(strip=True)
        if not titulo:
            return None

        # Link
        link_el = card.select_one("a[href*='/jobs/']") if card.name != "a" else card
        link = _as_url(link_el.get("href")) if link_el else None
        if link and not link.startswith("http"):
            link = f"https://programathor.com.br{link}"

        # Empresa (span com ícone briefcase)
        empresa = None
        brief = card.select_one("i.fa-briefcase")
        if brief and brief.parent:
            empresa = brief.parent.get_text(strip=True)

        # Localização / modalidade (span com ícone map-marker)
        cidade = None
        modalidade = None
        marker = card.select_one("i.fa-map-marker-alt, i.fa-map-marker")
        if marker and marker.parent:
            texto = marker.parent.get_text(strip=True)
            if texto.lower() in _MODALIDADE_VALUES:
                modalidade = texto.lower()
            else:
                cidade = texto

        # Tags de stack → usadas pelo normalizador como "descrição" leve
        tags = [t.get_text(strip=True) for t in card.select(".tag-list")]
        descricao = " ".join(tags)

        # Salário (free-text quando presente)
        full_text = card.get_text()
        salario_min, salario_max, moeda = _parse_salario(full_text)

        return RawJob(
            fonte=self.nome,
            id=str(link or titulo),
            titulo=titulo,
            empresa=empresa,
            cidade=cidade,
            url=link,
            modalidade=modalidade,
            salario_min=salario_min,
            salario_max=salario_max,
            salario_moeda=moeda,
            descricao=descricao or None,
        )
