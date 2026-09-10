"""Normalização de vagas: stack, senioridade, salário, localização, modalidade."""

from __future__ import annotations

import re
from typing import Any

from careercompass.ingestion.base import RawJob

# ── Keywords de stack (categorizadas por natureza) ─────────────────────
_STACK_KEYWORDS: dict[str, list[str]] = {
    "dados": [
        "python",
        "sql",
        "pandas",
        "polars",
        "numpy",
        "scipy",
        "jupyter",
        "notebook",
        "power bi",
        "tableau",
        "looker",
        "duckdb",
        "spark",
        "airflow",
        "dbt",
        "metabase",
        "grafana",
        "machine learning",
        "ml",
        "ia",
        "inteligência artificial",
        "análise de dados",
        "data analyst",
        "data science",
        "data engineering",
        "bigquery",
        "redshift",
        "snowflake",
        "etl",
        "elt",
        "superset",
        "data lake",
        "data warehouse",
    ],
    "backend": [
        "node",
        "nodejs",
        "express",
        "fastapi",
        "django",
        "flask",
        "spring",
        "java",
        "c#",
        ".net",
        "golang",
        "rust",
        "ruby",
        "php",
        "laravel",
        "nestjs",
    ],
    "frontend": [
        "react",
        "vue",
        "angular",
        "svelte",
        "next",
        "nuxt",
        "html",
        "css",
        "javascript",
        "typescript",
        "tailwind",
    ],
    "devops": [
        "docker",
        "kubernetes",
        "k8s",
        "aws",
        "azure",
        "gcp",
        "terraform",
        "ansible",
        "jenkins",
        "ci/cd",
        "github actions",
        "linux",
        "bash",
    ],
    "qa": [
        "test",
        "qa",
        "qualidade",
        "selenium",
        "cypress",
        "jest",
        "pytest",
        "junit",
        "automação de testes",
    ],
    "mobile": [
        "react native",
        "flutter",
        "swift",
        "kotlin",
        "android",
        "ios",
    ],
    "fullstack": [
        "full stack",
        "fullstack",
        "full-stack",
    ],
}

# ── Regex de senioridade ───────────────────────────────────────────────
_SENIORITY_MAP: dict[str, re.Pattern[str]] = {
    "junior": re.compile(r"júnior|junior|j[úu]nior|pleno\s*1|entry", re.IGNORECASE),
    "pleno": re.compile(r"pleno|mid[\s-]*level|intermediate", re.IGNORECASE),
    "senior": re.compile(r"sênior|senior|s[êe]nior|lead|staff|principal", re.IGNORECASE),
}

# ── UFs do Brasil ──────────────────────────────────────────────────────
_UF_MAP: dict[str, str] = {
    "acre": "AC",
    "alagoas": "AL",
    "amapá": "AP",
    "amazonas": "AM",
    "bahia": "BA",
    "ceará": "CE",
    "distrito federal": "DF",
    "espírito santo": "ES",
    "goiás": "GO",
    "maranhão": "MA",
    "mato grosso": "MT",
    "mato grosso do sul": "MS",
    "minas gerais": "MG",
    "pará": "PA",
    "paraíba": "PB",
    "paraná": "PR",
    "pernambuco": "PE",
    "piauí": "PI",
    "rio de janeiro": "RJ",
    "rio grande do norte": "RN",
    "rio grande do sul": "RS",
    "rondônia": "RO",
    "roraima": "RR",
    "santa catarina": "SC",
    "são paulo": "SP",
    "sergipe": "SE",
    "tocantins": "TO",
}

_UF_SIGLAS = set(_UF_MAP.values())

# ── Cidades grandes com nomes que precisam de normalização ─────────────
_CIDADE_FIXES: dict[str, str] = {
    "sao paulo": "São Paulo",
    "rio de janeiro": "Rio de Janeiro",
    "belo horizonte": "Belo Horizonte",
    "brasilia": "Brasília",
    "curitiba": "Curitiba",
    "porto alegre": "Porto Alegre",
    "salvador": "Salvador",
    "recife": "Recife",
    "fortaleza": "Fortaleza",
    "manaus": "Manaus",
    "goiânia": "Goiânia",
    "belém": "Belém",
    "campinas": "Campinas",
}


def normalize_stack(titulo: str, descricao: str | None = None) -> dict[str, list[str]]:
    """Detecta skills de stack a partir do título + descrição.

    Returns:
        dict com keys 'matches' (lista de categorias) e 'skills' (lista de keywords encontradas).
    """
    texto = f"{titulo} {descricao or ''}".lower()
    found_categories: list[str] = []
    found_skills: list[str] = []

    for categoria, keywords in _STACK_KEYWORDS.items():
        for kw in keywords:
            if kw in texto:
                if categoria not in found_categories:
                    found_categories.append(categoria)
                if kw not in found_skills:
                    found_skills.append(kw)

    return {"matches": found_categories, "skills": found_skills}


def normalize_senioridade(titulo: str, descricao: str | None = None) -> str:
    """Detecta senioridade do título + descrição. Retorna 'sem-info' se não encontrar."""
    texto = f"{titulo} {descricao or ''}".lower()

    # Leaderhip check (mais alto antes de pleno)
    if re.search(r"lead|líder|gerente|manager|coordenador|head|diretor", texto):
        return "lideranca"

    for nivel, pattern in _SENIORITY_MAP.items():
        if pattern.search(texto):
            return nivel

    return "sem-info"


def normalize_salario(
    salario_min: float | None = None,
    salario_max: float | None = None,
    salario_moeda: str | None = None,
    salario_raw: str | None = None,
) -> tuple[float | None, float | None, str | None]:
    """Normaliza salário. Se vier raw, tenta extrair. Se 'a combinar', retorna None."""
    if salario_raw:
        raw_lower = salario_raw.lower().strip()
        if "combinar" in raw_lower or "a combinar" in raw_lower:
            return None, None, None

    # Se já tem valores estruturados, retorna
    if salario_min is not None or salario_max is not None:
        return salario_min, salario_max, salario_moeda or "BRL"

    return None, None, None


def normalize_modalidade(
    modalidade: str | None = None,
    titulo: str | None = None,
    descricao: str | None = None,
) -> str:
    """Normaliza modalidade para valores canônicos."""
    texto = f"{modalidade or ''} {titulo or ''} {descricao or ''}".lower()

    if "remot" in texto:
        return "remoto"
    if "híbrid" in texto or "hibrid" in texto or "hybrid" in texto:
        return "hibrido"
    if "presencial" in texto or "on-site" in texto or "on site" in texto or "presential" in texto:
        return "presencial"

    return "nao-informado"


def normalize_cidade_estado(
    cidade: str | None = None, estado: str | None = None
) -> tuple[str | None, str | None]:
    """Normaliza cidade e estado (UF sigla)."""
    cidade_norm = cidade
    if cidade:
        # Capitalizar e aplicar fixes
        cidade_lower = cidade.lower().strip()
        cidade_norm = _CIDADE_FIXES.get(cidade_lower, cidade.strip().title())

    # Normalizar estado
    estado_norm = None
    if estado:
        estado_upper = estado.strip().upper()
        if estado_upper in _UF_SIGLAS:
            estado_norm = estado_upper
        else:
            # Tentar converter nome completo → UF
            estado_lower = estado.strip().lower()
            estado_norm = _UF_MAP.get(estado_lower)

    return cidade_norm, estado_norm


def normalize_job(job: RawJob) -> dict[str, Any]:
    """Aplica todas as normalizações em um RawJob e retorna dict enriquecido."""
    stack = normalize_stack(job.titulo, job.descricao)
    senioridade = normalize_senioridade(job.titulo, job.descricao)
    sal_min, sal_max, sal_moeda = normalize_salario(
        job.salario_min, job.salario_max, job.salario_moeda, job.salario_raw
    )
    modalidade = normalize_modalidade(job.modalidade, job.titulo, job.descricao)
    cidade, estado = normalize_cidade_estado(job.cidade, job.estado)

    return {
        "fonte": job.fonte,
        "id": job.id,
        "titulo": job.titulo,
        "empresa": job.empresa,
        "empresa_id": job.empresa_id,
        "cidade": cidade,
        "estado": estado,
        "url": job.url,
        "modalidade": modalidade,
        "publicado_em": job.publicado_em,
        "salario_min": sal_min,
        "salario_max": sal_max,
        "salario_moeda": sal_moeda,
        "salario_raw": job.salario_raw,
        "stack_matches": stack["matches"],
        "stack_skills": stack["skills"],
        "senioridade": senioridade,
        "descricao": job.descricao,
    }
