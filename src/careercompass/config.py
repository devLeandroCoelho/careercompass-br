"""Configuração centralizada com defaults seguros e envs via dotenv."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
REPORTS_DIR = PROJECT_ROOT / "src" / "careercompass" / "reports"

RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Fontes ─────────────────────────────────────────────────────────────
# Gupy: API pública migrou para SSR público (pagina /job-search/{query} com __NEXT_DATA__)
# Sem auth; paginação limitada à primeira página (12 vagas/query) sem token.
GUPY_BASE_URL: str = os.getenv("GUPY_BASE_URL", "https://portal.gupy.io/job-search")
GEEKHUNTER_URL: str = os.getenv("GEEKHUNTER_URL", "https://www.geekhunter.com.br/vagas")
PROGRAMATHOR_URL: str = os.getenv("PROGRAMATHOR_URL", "https://programathor.com.br/jobs")

# ── Pipeline ───────────────────────────────────────────────────────────
MAX_PAGES: int = int(os.getenv("MAX_PAGES", "3"))
REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.5"))
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "CareerCompassBot/0.1 (portfolio; +https://github.com/devLeandroCoelho/careercompass-br)",
)

# ── DuckDB ─────────────────────────────────────────────────────────────
DUCKDB_PATH: Path = PROJECT_ROOT / os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
