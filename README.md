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

<!-- TODO: completar com instruções de setup local, venv, variáveis de ambiente, rodar o pipeline e o dashboard -->

```bash
# Clone
git clone https://github.com/devLeandroCoelho/careercompass-br.git
cd careercompass-br

# Ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Dependências
pip install -r requirements.txt

# Pipeline ETL
python -m src.etl.pipeline

# Dashboard
streamlit run src/dashboard/app.py
```

## Estrutura do Projeto

```
careercompass-br/
├── src/
│   ├── etl/            # Pipeline de coleta e transformação
│   │   ├── parsers/    # Parsers por fonte (Gupy, GeekHunter, Programathor)
│   │   └── normalize/  # Normalização e padronização
│   ├── warehouse/      # Modelagem DuckDB (facts/dimensions)
│   └── dashboard/      # App Streamlit
├── notebooks/          # Análises exploratórias
├── tests/              # Testes automatizados
├── data/               # Dados brutos (gitignored)
└── reports/            # Relatórios gerados
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
