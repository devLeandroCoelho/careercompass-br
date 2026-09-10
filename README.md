# 🧭 CareerCompass BR

> **De infra/backend para Análise de Dados — portfólio de mercado de vagas BR**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/pytest-8.0-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![ruff](https://img.shields.io/badge/ruff-0.6-FCD21B?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Docker](https://img.shields.io/badge/Docker-24.0-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](#english-version) · **Português**

---

## Por que este projeto existe

**A história é simples**: há 18 anos atuo na TI — infra, suporte, backend, gestão de time. Em 2026, decidi migrar para Análise de Dados.

Mas migração de carreira não é só aprender Python ou SQL. É entender **o mercado que você quer entrar**.

Então criei o CareerCompass BR: um pipeline ETL que coleta vagas reais de TI/Dados no Brasil, normaliza os dados e responde, com números, perguntas que todo candidato faz:

- **Quanto paga cada stack?**
- **Onde estão as vagas?** (região, cidade, UF)
- **Remoto vs. presencial vs. híbrido?**

Não é ferramenta de decisão salarial — é análise exploratória. Um portfólio que mostra que sei coletar, transformar, armazenar e visualizar dados. E que transferi skills de backend (SQL, Docker, testes, automação) para o novo campo.

---

## Perguntas de negócio

O dashboard responde três perguntas centrais:

| # | Pergunta | Onde no dashboard |
|---|----------|-------------------|
| 1 | Quanto paga cada stack? | 💰 Salários |
| 2 | Onde estão as vagas? | 🗺️ Regiões |
| 3 | Remoto vs. presencial vs. híbrido? | 📊 Visão Geral |

---

## Arquitetura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Coleta        │     │   Processamento   │     │   Armazenamento │
│                 │     │                   │     │                 │
│  Gupy (API)     │────▶│  Normalização     │────▶│  DuckDB         │
│  GeekHunter     │     │  (stack/senior/   │     │  (star schema)  │
│  Programathor   │     │   salário/UF)     │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │   Deduplicação   │     │   Dashboard     │
                        │                  │     │   Streamlit     │
                        └──────────────────┘     └─────────────────┘
```

### Fluxo do pipeline

1. **Coleta** — Gupy (portal SSR), GeekHunter (JSON-LD), Programathor (HTML) — com throttle e respeitando termos
2. **Normalização** — stack, senioridade, salário BRL, cidade/UF, modalidade
3. **Deduplicação** — por `(fonte, url)` / `(fonte, id)`
4. **Warehouse** — DuckDB com schema star: `fact_job`, `dim_company`, `dim_location`, `dim_skill`, `fact_job_skill`, `fact_salary`
5. **Relatório** — markdown com contagens por fonte, erros e cobertura salarial

### Primeiro run real (10/09/2026)

| Métrica | Valor |
|---------|-------|
| Vagas brutas | 156 |
| Vagas únicas | 84 |
| Duplicatas removidas | 72 |

---

## Como rodar

### Setup local

```bash
git clone https://github.com/devLeandroCoelho/careercompass-br.git
cd careercompass-br

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

# Opcional: copie e ajuste as variáveis
cp .env.example .env
```

### Pipeline ETL

```bash
# Dry-run com limite de páginas (default: MAX_PAGES=3)
MAX_PAGES=3 python -m careercompass

# Ou com mais páginas por fonte
MAX_PAGES=5 REQUEST_DELAY=2.0 python -m careercompass
```

O pipeline gera:
- Dados brutos em `data/raw/*.jsonl` (não versionados)
- Warehouse em `data/warehouse.duckdb` (gitignored)
- Relatório em `src/careercompass/reports/pipeline-report-<data>.md`

### Dashboard

```bash
streamlit run src/dashboard/app.py
```

**5 páginas**: Visão Geral · Salários · Regiões · Stacks · Sobre o projeto

Se não houver dados reais, o dashboard entra em **modo demonstração** com ~300 vagas simuladas e banner "Dados de Demonstração".

### Testes, lint e tipos

```bash
python -m pytest          # 56 testes
ruff check .              # lint (E, F, I, UP, B)
ruff format --check .     # formatação
mypy src/                 # type check estrito
```

### Docker

```bash
docker build -t careercompass .
docker run careercompass
```

---

## Exemplo de SQL real

O warehouse usa schema star. Aqui está uma query real do projeto — mediana salarial por stack:

```sql
-- Qual a mediana salarial por stack?
SELECT
    s.skill_name AS stack,
    COUNT(*) AS total_vagas,
    ROUND(AVG(fj.salario_min), 0) AS salario_min_medio,
    ROUND(AVG(fj.salario_max), 0) AS salario_max_medio
FROM fact_job fj
JOIN fact_job_skill fjs ON fj.job_id = fjs.job_id
JOIN dim_skill s ON fjs.skill_id = s.skill_id
WHERE fj.salario_min IS NOT NULL
GROUP BY s.skill_name
ORDER BY total_vagas DESC
LIMIT 10;
```

> Fonte: `src/careercompass/warehouse/tables.sql` — schema completo com 7 tabelas (staging + 3 dimensões + 3 fatos).

---

## Limitações honestas

Este projeto tem limitações reais que documento com transparência:

- **Cobertura salarial**: apenas ~8% das vagas na listagem têm salário disponível. Isso é uma limitação das fontes, não do pipeline.
- **Fontes permitidas**: Gupy (portal SSR), GeekHunter (JSON-LD), Programathor (HTML). Proibido: LinkedIn, Indeed, Catho.
- **Throttle e respeito**: coleta com delay entre requests e respeito aos termos de uso das fontes.
- **Dados exploratórios**: análise descritiva, não ferramenta de decisão salarial. Use como referência, não como oráculo.

---

## Roadmap

- [x] Fase 1: Pipeline ETL multi-fonte
- [x] Fase 2: Normalização e data warehouse DuckDB
- [x] Fase 3: Dashboard Streamlit interativo
- [ ] Fase 4: Análises em Jupyter Notebook
- [ ] Fase 5: Integração com Power BI (alternativo ao Streamlit)
- [ ] Fase 6: Análise de custo de vida × salário por região
- [ ] Fase 7: NL → SQL (consultas em linguagem natural)

---

## Estrutura do projeto

```
careercompass-br/
├── src/careercompass/        # Pipeline ETL
│   ├── ingestion/            # Coletores (Gupy, GeekHunter, Programathor)
│   ├── processing/           # Normalização + deduplicação
│   ├── warehouse/            # DuckDB (schema star + upsert idempotente)
│   ├── reports/              # Relatórios gerados
│   ├── pipeline.py           # Orquestração ETL
│   └── config.py             # Configuração via env
├── src/dashboard/            # Dashboard Streamlit
│   ├── app.py                # Entry point
│   ├── pages/                # 5 páginas (overview, salaries, regions, stacks, about)
│   ├── data_loader.py        # Carregamento de dados
│   ├── charts.py             # Gráficos Plotly
│   └── mock_data.py          # Dados de demonstração
├── tests/                    # 56 testes pytest
├── notebooks/                # Análises exploratórias (a preparar)
├── data/                     # Dados brutos + warehouse (gitignored)
├── Dockerfile                # Container para rodar o pipeline
└── pyproject.toml            # Configuração do projeto
```

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.

---

## Contato

**Leandro Prazeres Coelho**

- 🐙 [GitHub](https://github.com/devLeandroCoelho)
- 💼 [LinkedIn](https://www.linkedin.com/in/devleandrocoelho/)
- 📧 devleandrocoelho@gmail.com
- 🌐 [Portfólio](https://devleandrocoelho.github.io/meu-portifolio)

---

## English Version

> **From infrastructure/backend to Data Analysis — a portfolio of the Brazilian job market**

### Why this project exists

The story is straightforward: I've been in IT for 18 years — infrastructure, support, backend, team management. In 2026, I decided to transition to Data Analysis.

But career transition isn't just about learning Python or SQL. It's about understanding **the market you want to enter**.

So I created CareerCompass BR: an ETL pipeline that collects real TI/Data job postings in Brazil, normalizes the data, and answers with numbers the questions every candidate asks:

- **How much does each stack pay?**
- **Where are the jobs?** (region, city, state)
- **Remote vs. on-site vs. hybrid?**

It's not a salary decision tool — it's exploratory analysis. A portfolio that shows I can collect, transform, store, and visualize data. And that I transferred backend skills (SQL, Docker, tests, automation) to this new field.

### Business questions

| # | Question | Dashboard page |
|---|----------|----------------|
| 1 | How much does each stack pay? | 💰 Salaries |
| 2 | Where are the jobs? | 🗺️ Regions |
| 3 | Remote vs. on-site vs. hybrid? | 📊 Overview |

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Ingestion     │     │   Processing     │     │   Storage       │
│                 │     │                  │     │                 │
│  Gupy (API)     │────▶│  Normalization   │────▶│  DuckDB         │
│  GeekHunter     │     │  (stack/seniority│     │  (star schema)  │
│  Programathor   │     │   salary/state)  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │   Deduplication  │     │   Dashboard     │
                        │                  │     │   Streamlit     │
                        └──────────────────┘     └─────────────────┘
```

### How to run

```bash
# Pipeline
MAX_PAGES=3 python -m careercompass

# Dashboard
streamlit run src/dashboard/app.py

# Tests
python -m pytest          # 56 tests
ruff check .              # lint
mypy src/                 # type check
```

### First real run (2026-09-10)

| Metric | Value |
|--------|-------|
| Raw jobs | 156 |
| Unique jobs | 84 |
| Duplicates removed | 72 |

### Honest limitations

- **Salary coverage**: only ~8% of listed jobs have salary data available. This is a limitation of the sources, not the pipeline.
- **Allowed sources**: Gupy (SSR portal), GeekHunter (JSON-LD), Programathor (HTML). Blocked: LinkedIn, Indeed, Catho.
- **Throttle and respect**: collection with delay between requests and respect for sources' terms of use.
- **Exploratory data**: descriptive analysis, not a salary decision tool. Use as reference, not as oracle.

### Roadmap

- [x] Phase 1: Multi-source ETL pipeline
- [x] Phase 2: Normalization and DuckDB data warehouse
- [x] Phase 3: Interactive Streamlit dashboard
- [ ] Phase 4: Jupyter Notebook analyses
- [ ] Phase 5: Power BI integration (Streamlit alternative)
- [ ] Phase 6: Cost of living × salary analysis by region
- [ ] Phase 7: NL → SQL (natural language queries)

### Contact

**Leandro Prazeres Coelho**

- 🐙 [GitHub](https://github.com/devLeandroCoelho)
- 💼 [LinkedIn](https://www.linkedin.com/in/devleandrocoelho/)
- 📧 devleandrocoelho@gmail.com
- 🌐 [Portfolio](https://devleandrocoelho.github.io/meu-portifolio)

---

*Feito com Python, DuckDB e Streamlit. Dados reais do mercado brasileiro de TI/Dados.*
