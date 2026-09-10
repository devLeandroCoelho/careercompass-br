"""Interface abstrata para coletores de vagas."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import requests

from careercompass import config


@dataclass
class RawJob:
    """Representação bruta de uma vaga antes da normalização."""

    fonte: str
    id: str
    titulo: str
    empresa: str | None = None
    empresa_id: str | None = None
    cidade: str | None = None
    estado: str | None = None
    url: str | None = None
    modalidade: str | None = None  # remoto / hibrido / presencial
    publicado_em: str | None = None
    salario_raw: str | None = None
    salario_min: float | None = None
    salario_max: float | None = None
    salario_moeda: str | None = None
    descricao: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def _as_url(value: Any) -> str | None:
    """Normaliza valor de atributo HTML (href) para str, se aplicável."""
    return value if isinstance(value, str) else None


class Collector(ABC):
    """Classe base para coletores. Subclasses implementam collect()."""

    nome: str

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self._last_request: float = 0.0

    def _throttle(self) -> None:
        """Aguarda REQUEST_DELAY entre requests."""
        elapsed = time.time() - self._last_request
        if elapsed < config.REQUEST_DELAY:
            time.sleep(config.REQUEST_DELAY - elapsed)
        self._last_request = time.time()

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        self._throttle()
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT)
        return self.session.get(url, **kwargs)

    @abstractmethod
    def collect(self, max_pages: int = config.MAX_PAGES) -> list[RawJob]:
        """Coleta vagas e retorna lista de RawJob."""
        ...

    def save_raw(self, jobs: list[RawJob], output_dir: Path | None = None) -> Path:
        """Salva vagas brutas em JSONL em data/raw/<fonte>-<data>.jsonl."""
        out = output_dir or config.RAW_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{self.nome}-{date.today():%Y%m%d}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for job in jobs:
                f.write(json.dumps(job.__dict__, ensure_ascii=False, default=str) + "\n")
        return path
