# CareerCompass BR

Análise de dados do mercado de vagas de TI e Dados no Brasil — portfólio de Data Analyst.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<!-- TODO: adicionar badges de CI, coverage, deploy, version -->

## Sobre o projeto

<!-- TODO: completar com descrição detalhada do produto, motivação e resultados esperados -->

Este projeto realiza coleta, normalização e análise exploratória de vagas de emprego das áreas de Tecnologia e Dados no mercado brasileiro. As fontes de dados incluem a **Gupy** (API pública), **GeekHunter** e **Programathor** (web scraping).

O resultado é um **dashboard interativo** construído com Streamlit que responde perguntas de negócio como:

- Quais stacks e tecnologias são mais requisitadas?
- Como varia a senioridade exigida por região?
- Qual a distribuição salarial por cargo e localidade?
- O mercado está mais presencial, híbrido ou remoto?

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Coleta | `requests`, `BeautifulSoup`, Gupy API |
| Transformação | pandas / Polars |
| Warehouse | DuckDB |
| Dashboard | Streamlit |
| Análise | Jupyter Notebooks |
| Qualidade | pytest, ruff, mypy |
| Containerização | Docker |
| CI/CD | GitHub Actions |

## Getting Started

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

### Rodar o pipeline ETL

```bash
# Dry-run com limite de páginas (default: MAX_PAGES=3)
MAX_PAGES=3 python -m careercompass

# Ou com mais páginas por fonte
MAX_PAGES=5 REQUEST_DELAY=2.0 python -m careercompass
```

O pipeline:
1. Coleta vagas das 3 fontes (Gupy API + GeekHunter + Programathor) com throttle,
2. Normaliza (stack, senioridade, salário, cidade/UF, modalidade),
3. Deduplica por `(fonte, url)` / `(fonte, id)`,
4. Carrega no DuckDB (`data/warehouse.duckdb`),
5. Gera relatório em `src/careercompass/reports/pipeline-report-<data>.md`
   com contagens por fonte, erros e cobertura salarial.

> **Dados brutos** ficam em `data/raw/*.jsonl` e **não** são versionados.
> O warehouse DuckDB também é local (gitignored).

### Testes, lint e tipos

```bash
python -m pytest          # testes (52 casos)
ruff check .              # lint (E, F, I, UP, B)
ruff format --check .     # formatação
mypy src/                 # type check estrito
```

## Estrutura do Projeto

```
careercompass-br/
├── src/careercompass/
│   ├── ingestion/        # Coletores (Gupy, GeekHunter, Programathor, base)
│   ├── processing/       # Normalização (stack/senioridade/salário/location) + dedup
│   ├── warehouse/        # DuckDB (schema DDL + upsert idempotente)
│   ├── reports/          # Relatórios gerados (gitignored)
│   ├── pipeline.py       # Orquestração ETL
│   └── config.py         # Configuração via env
├── notebooks/            # Análises exploratórias (placeholder)
├── tests/                # Testes pytest + fixtures
├── data/                 # Dados brutos + warehouse (gitignored)
└── Dockerfile            # Image para rodar o pipeline em container
```

## Roadmap

- [ ] Fase 1: Pipeline ETL multi-fonte
- [ ] Fase 2: Normalização e data warehouse DuckDB
- [ ] Fase 3: Dashboard Streamlit interativo
- [ ] Fase 4: Análises em notebook + relatório

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.

## Contato

**Leandro Prazeres Coelho** — [LinkedIn](https://www.linkedin.com/in/leandrocoelho) — leandro@exemplo.com
