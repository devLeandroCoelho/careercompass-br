"""Página: 📄 Sobre o Projeto — informações do CareerCompass BR."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    """Renderiza a página sobre o projeto."""
    st.header("📄 Sobre o CareerCompass BR")

    st.markdown("""
    ## O que é?

    **CareerCompass BR** é um projeto de portfólio em **Análise de Dados** que
    coleta, normaliza e analisa vagas reais de TI e Dados no Brasil. O objetivo é
    responder perguntas de negócio reais sobre o mercado de trabalho brasileiro
    usando dados coletados de fontes públicas.

    ## Perguntas de Negócio

    O dashboard responde a quatro perguntas centrais:

    1. **Quanto paga cada stack?** — Mediana e média salarial por categoria (backend, frontend, dados, etc.) com boxplot mostrando amplitude e nota de cobertura.
    2. **Onde estão as vagas?** — Distribuição por estado e top cidades.
    3. **Remoto vs presencial vs híbrido?** — Distribuição e salário por modalidade.
    4. **Tendências** — Volume diário de vagas e heatmap senioridade × stack.

    ## Fontes de Dados

    | Fonte | Tipo | Volume estimado |
    |---|---|---|
    | **Gupy** | API pública | 200–500 vagas/dia |
    | **GeekHunter** | Web scraping | 100–300 vagas/dia |
    | **Programathor** | Web scraping | 100–200 vagas/dia |

    > ⚠️ Os dados são coletados de fontes públicas e podem conter inconsistências.
    > A análise reflete **apenas as vagas com faixa salarial divulgada** (~30–40% do total).

    ## Stack Técnica

    | Camada | Tecnologia |
    |---|---|
    | Linguagem | Python 3.12 |
    | Coleta | requests, BeautifulSoup, Gupy API |
    | Transformação | pandas, Polars |
    | Warehouse | DuckDB |
    | Dashboard | Streamlit + Plotly |
    | Qualidade | pytest, ruff, mypy |
    | CI/CD | GitHub Actions |

    ## Como Rodar

    ```bash
    # Clone
    git clone https://github.com/devLeandroCoelho/careercompass-br.git
    cd careercompass-br

    # Ambiente virtual
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # .venv\\Scripts\\activate  # Windows

    # Dependências
    pip install -r requirements.txt

    # Dashboard (modo demo se não houver DuckDB)
    streamlit run src/dashboard/app.py
    ```

    > 📌 Se o arquivo `data/warehouse.duckdb` não existir, o dashboard carrega automaticamente
    > um **dataset de demonstração** com ~300 vagas plausíveis. Uma bandeira "Dados de Demonstração"
    > é exibida na sidebar.

    ## Limitações

    - **Cobertura salarial**: Apenas ~30–40% das vagas divulgam faixa salarial.
    - **Viés de amostra**: As fontes coletadas não representam 100% do mercado.
    - **Dados de demonstração**: Sem o pipeline ETL, o dashboard usa dados simulados.
    - **Deducação**: Pode haver vagas duplicadas entre fontes (dedup por URL).

    ## Contato

    **Leandro Prazeres Coelho**
    - [LinkedIn](https://www.linkedin.com/in/leandrocoelho)
    - [GitHub](https://github.com/devLeandroCoelho)

    ## Licença

    Distribuído sob a licença MIT. Veja [LICENSE](https://github.com/devLeandroCoelho/careercompass-br/blob/main/LICENSE).
    """)
