"""
Gerador de dados de demonstração para o CareerCompass BR.

Gera ~300 vagas plausíveis do mercado brasileiro de TI/Dados
com salários, skills, modalidades e localizações realistas.

Bandeira: todos os dados têm campo `fonte = 'demo'`.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ── Configurações do dataset de demonstração ──────────────────────────
_SEED = 42
_N_VAGAS = 300

# Categorias (em pt-BR, como definido no contrato de dados)
_CATEGORIAS = [
    "backend",
    "frontend",
    "dados",
    "qa",
    "devops",
    "mobile",
    "fullstack",
]

# Senioridades
_SENIORIDADES = ["estagio", "junior", "pleno", "senior", "lead"]

# Modalidades
_MODALIDADES = ["remoto", "hibrido", "presencial"]

# Fontes (para simular distribuição real)
_FONTES = ["gupy", "geekhunter", "programathor"]

# ── Skills por categoria (realistas 2025-2026 BR) ──────────────────────
_SKILLS_POR_CATEGORIA: dict[str, list[str]] = {
    "backend": [
        "Python", "Java", "Node.js", "TypeScript", "Go", "C#",
        "PostgreSQL", "MySQL", "Redis", "Docker", "REST API", "GraphQL",
        "Spring Boot", "FastAPI", "Django", "Express", "Microservices",
    ],
    "frontend": [
        "React", "TypeScript", "JavaScript", "HTML", "CSS",
        "Next.js", "Vue.js", "Angular", "Tailwind CSS", "Sass",
        "Storybook", "Webpack", "Vite", "Figma", "Responsive Design",
    ],
    "dados": [
        "Python", "SQL", "pandas", "Spark", "dbt", "Airflow",
        "DuckDB", "PostgreSQL", "BigQuery", "Snowflake", "Power BI",
        "Tableau", "Jupyter", "ETL", "Machine Learning", "Statistical Analysis",
        "Docker", "Git", "A/B Testing", "Excel Avançado",
    ],
    "qa": [
        "Selenium", "Cypress", "Playwright", "Pytest", "Jest",
        "Postman", "Jira", "Test Automation", "API Testing",
        "SQL", "Git", "CI/CD", "Performance Testing", "Manual Testing",
    ],
    "devops": [
        "AWS", "Docker", "Kubernetes", "Terraform", "CI/CD",
        "GitHub Actions", "Jenkins", "Linux", "Ansible", "Prometheus",
        "Grafana", "Python", "Bash", "Nginx", "PostgreSQL",
    ],
    "mobile": [
        "Flutter", "React Native", "Dart", "Kotlin", "Swift",
        "iOS", "Android", "Firebase", "REST API", "Git",
        "CI/CD", "SQLite", "Figma", "UI/UX",
    ],
    "fullstack": [
        "React", "TypeScript", "Node.js", "Python", "PostgreSQL",
        "Docker", "REST API", "Git", "AWS", "Next.js",
        "Tailwind CSS", "Prisma", "GraphQL", "Redis", "CI/CD",
    ],
}

# ── Empresas brasileiras plausíveis ──────────────────────────────────
_EMPRESAS = [
    "Nubank", "iFood", "Mercado Libre", "Stone", "PagSeguro",
    "TOTVS", "CI&T", "Thoughtworks", "Stefanini", "Dextra",
    "Vivo", "Claro", "Banco Inter", "BTG Pactual", "XP Investimentos",
    "Rappi BR", "Loggi", "99", "Buscapé", "OLX",
    "Magazine Luiza", "Americanas", "Saraiva Digital", "RD Station",
    "Hotmart", "Geru", "Creditas", "QuintoAndar", "Loft",
    "C6 Bank", "Original Bank", "Next (Banco)", "PicPay",
    "Ambev Tech", "Petrobras Digital", "B3 Tech", "BR Distribuidora",
    "Accenture BR", "Capgemini BR", "Deloitte Digital",
    "Turing", "Beetroot", "BairesDev", "Globant BR",
    "Selic", "Ame Digital", "Cora", "Zup", "Neoway",
    "Sympla", "Catho", "Gupy", "Vagas.com",
    "Rocketseat", "Alura", "Digital House",
]

# ── Cidades e estados BR ──────────────────────────────────────────────
_CIDADES_UF: list[tuple[str, str]] = [
    ("São Paulo", "SP"),
    ("São Paulo", "SP"),  # peso
    ("São Paulo", "SP"),
    ("Campinas", "SP"),
    ("São José dos Campos", "SP"),
    ("Sorocaba", "SP"),
    ("Ribeirão Preto", "SP"),
    ("Rio de Janeiro", "RJ"),
    ("Rio de Janeiro", "RJ"),  # peso
    ("Niterói", "RJ"),
    ("Belo Horizonte", "MG"),
    ("Belo Horizonte", "MG"),
    ("Uberlândia", "MG"),
    ("Curitiba", "PR"),
    ("Curitiba", "PR"),
    ("Londrina", "PR"),
    ("Porto Alegre", "RS"),
    ("Porto Alegre", "RS"),
    ("Florianópolis", "SC"),
    ("Florianópolis", "SC"),
    ("Joinville", "SC"),
    ("Brasília", "DF"),
    ("Brasília", "DF"),
    ("Goiânia", "GO"),
    ("Salvador", "BA"),
    ("Recife", "PE"),
    ("Fortaleza", "CE"),
    ("Manaus", "AM"),
    ("Belém", "PA"),
    ("Vitória", "ES"),
    ("Maceió", "AL"),
    ("Campo Grande", "MS"),
    ("Cuiabá", "MT"),
    ("Aracaju", "SE"),
    ("João Pessoa", "PB"),
    ("Natal", "RN"),
    ("Teresina", "PI"),
    ("São Luís", "MA"),
    ("Palmas", "TO"),
    ("Macapá", "AP"),
    ("Rio Branco", "AC"),
    ("Boa Vista", "RR"),
]

# ── Faixas salariais por senioridade (R$/mês) ─────────────────────────
# (min_base, max_base) — salários realistas BR 2025-2026
_SALARIO_POR_SENIORIDADE: dict[str, tuple[float, float]] = {
    "estagio": (1200, 2500),
    "junior": (2500, 5500),
    "pleno": (5500, 10000),
    "senior": (10000, 20000),
    "lead": (15000, 30000),
}

# Peso por senioridade (distribuição realista)
_PESO_SENIORIDADE = [0.10, 0.30, 0.35, 0.20, 0.05]

# Peso por modalidade
_PESO_MODALIDADE = [0.35, 0.40, 0.25]  # remoto, híbrido, presencial


def _random_date(start: datetime, end: datetime) -> datetime:
    """Gera data aleatória entre start e end."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def gerar_mock_jobs(n: int = _N_VAGAS, seed: int = _SEED) -> dict[str, pd.DataFrame]:
    """
    Gera dataset de demonstração plausível.

    Retorna dict com DataFrames que espelham o schema DuckDB:
    - fact_job
    - dim_company
    - dim_location
    - dim_skill
    - fact_job_skill
    - fact_salary
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    jobs = []
    all_skills: set[str] = set()
    job_skills_rows: list[dict] = []
    salary_rows: list[dict] = []
    company_set: set[str] = set()
    location_map: dict[tuple[str, str], int] = {}
    skill_map: dict[str, int] = {}
    skill_counter = 1
    company_counter = 1
    location_counter = 1

    now = datetime.now()
    start_date = now - timedelta(days=90)

    senioridades = _SENIORIDADES
    modalidades = _MODALIDADES
    categorias = _CATEGORIAS
    empresas = _EMPRESAS

    for job_id in range(1, n + 1):
        cat = random.choices(categorias, weights=[18, 16, 14, 8, 10, 8, 16])[0]
        senioridade = random.choices(senioridades, weights=_PESO_SENIORIDADE)[0]
        modalidade = random.choices(modalidades, weights=_PESO_MODALIDADE)[0]
        fonte = random.choices(_FONTES, weights=[45, 35, 20])[0]

        # Empresa
        empresa = random.choice(empresas)
        company_set.add(empresa)

        # Localização
        cidade, uf = random.choice(_CIDADES_UF)
        loc_key = (cidade, uf)
        if loc_key not in location_map:
            location_map[loc_key] = location_counter
            location_counter += 1
        local_id = location_map[loc_key]

        # Skills (2–5 por vaga)
        pool = _SKILLS_POR_CATEGORIA[cat]
        n_skills = random.randint(2, min(5, len(pool)))
        picked = random.sample(pool, n_skills)
        for sk in picked:
            all_skills.add(sk)

        # Salário: ~40% das vagas divulgam faixa
        tem_salario = random.random() < 0.40

        # Título
        titulo = _gerar_titulo(cat, senioridade)

        # Data de publicação
        pub = _random_date(start_date, now)

        jobs.append({
            "job_id": job_id,
            "fonte": "demo",
            "url_original": f"https://demo.careercompass.br/vaga/{job_id}",
            "titulo": titulo,
            "categoria_principal": cat,
            "senioridade": senioridade,
            "modalidade": modalidade,
            "publicado_em": pub.strftime("%Y-%m-%d"),
            "empresa": empresa,
            "cidade": cidade,
            "estado": uf,
            "tem_salario": tem_salario,
        })

        # Skills mapping
        for sk in picked:
            if sk not in skill_map:
                skill_map[sk] = skill_counter
                skill_counter += 1
            job_skills_rows.append({"job_id": job_id, "skill_id": skill_map[sk]})

        # Salário
        if tem_salario:
            smin_base, smax_base = _SALARIO_POR_SENIORIDADE[senioridade]
            # Variação por categoria
            cat_mult = {
                "dados": 1.10,
                "devops": 1.15,
                "backend": 1.05,
                "frontend": 1.00,
                "fullstack": 1.02,
                "mobile": 1.03,
                "qa": 0.90,
            }
            mult = cat_mult.get(cat, 1.0)
            smin = round(smin_base * mult * rng.uniform(0.85, 1.15), 0)
            smax = round(smax_base * mult * rng.uniform(0.90, 1.20), 0)
            if smax <= smin:
                smax = smin + 1000
            salary_rows.append({
                "job_id": job_id,
                "salario_min": smin,
                "salario_max": smax,
                "moeda": "BRL",
            })

    # ── Montar DataFrames ──────────────────────────────────────────────
    df_jobs = pd.DataFrame(jobs)

    # dim_company
    df_companies = pd.DataFrame([
        {"empresa_id": i + 1, "nome": c}
        for i, c in enumerate(sorted(company_set))
    ])
    company_id_map = {row["nome"]: row["empresa_id"] for _, row in df_companies.iterrows()}
    df_jobs["empresa_id"] = df_jobs["empresa"].map(company_id_map)

    # dim_location
    df_locations = pd.DataFrame([
        {"local_id": lid, "cidade": c, "estado": u}
        for (c, u), lid in location_map.items()
    ])
    df_jobs["local_id"] = df_jobs.apply(
        lambda r: location_map[(r["cidade"], r["estado"])], axis=1
    )

    # dim_skill
    df_skills = pd.DataFrame([
        {"skill_id": sid, "nome": s}
        for s, sid in sorted(skill_map.items(), key=lambda x: x[1])
    ])

    # fact_job_skill
    df_job_skills = pd.DataFrame(job_skills_rows)

    # fact_salary
    df_salary = pd.DataFrame(salary_rows)

    # fact_job (apenas colunas do contrato)
    fact_job = df_jobs[[
        "job_id", "fonte", "url_original", "titulo", "senioridade",
        "modalidade", "publicado_em", "empresa_id", "local_id",
        "categoria_principal",
    ]].copy()

    return {
        "fact_job": fact_job,
        "dim_company": df_companies,
        "dim_location": df_locations,
        "dim_skill": df_skills,
        "fact_job_skill": df_job_skills,
        "fact_salary": df_salary,
        # Extra para o dashboard (join pré-feito)
        "_jobs_full": df_jobs,
    }


def _gerar_titulo(categoria: str, senioridade: str) -> str:
    """Gera título de vaga plausível."""
    titulos = {
        "backend": {
            "estagio": "Estagiário(a) de Desenvolvimento Backend",
            "junior": "Desenvolvedor(a) Backend Júnior",
            "pleno": "Desenvolvedor(a) Backend Pleno",
            "senior": "Desenvolvedor(a) Backend Sênior",
            "lead": "Tech Lead Backend",
        },
        "frontend": {
            "estagio": "Estagiário(a) de Desenvolvimento Frontend",
            "junior": "Desenvolvedor(a) Frontend Júnior",
            "pleno": "Desenvolvedor(a) Frontend Pleno",
            "senior": "Desenvolvedor(a) Frontend Sênior",
            "lead": "Tech Lead Frontend",
        },
        "dados": {
            "estagio": "Estagiário(a) de Análise de Dados",
            "junior": "Analista de Dados Júnior",
            "pleno": "Analista de Dados Pleno",
            "senior": "Analista de Dados Sênior",
            "lead": "Head de Dados",
        },
        "qa": {
            "estagio": "Estagiário(a) de QA",
            "junior": "Analista de QA Júnior",
            "pleno": "Analista de QA Pleno",
            "senior": "Analista de QA Sênior",
            "lead": "Lead de Qualidade",
        },
        "devops": {
            "estagio": "Estagiário(a) de DevOps",
            "junior": "Engenheiro(a) DevOps Júnior",
            "pleno": "Engenheiro(a) DevOps Pleno",
            "senior": "Engenheiro(a) DevOps Sênior",
            "lead": "Platform Engineer Lead",
        },
        "mobile": {
            "estagio": "Estagiário(a) de Desenvolvimento Mobile",
            "junior": "Desenvolvedor(a) Mobile Júnior",
            "pleno": "Desenvolvedor(a) Mobile Pleno",
            "senior": "Desenvolvedor(a) Mobile Sênior",
            "lead": "Tech Lead Mobile",
        },
        "fullstack": {
            "estagio": "Estagiário(a) de Desenvolvimento Full Stack",
            "junior": "Desenvolvedor(a) Full Stack Júnior",
            "pleno": "Desenvolvedor(a) Full Stack Pleno",
            "senior": "Desenvolvedor(a) Full Stack Sênior",
            "lead": "Tech Lead Full Stack",
        },
    }
    return titulos.get(categoria, {}).get(senioridade, f"Desenvolvedor(a) {categoria.title()}")
