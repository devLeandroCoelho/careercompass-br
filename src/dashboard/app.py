"""
CareerCompass BR — Dashboard Streamlit
Portfólio de Análise de Dados do mercado brasileiro de TI.

Execução:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garantir que o src/ está no path
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

# ── Configuração da página (DEVE ser primeiro call do Streamlit) ───────
st.set_page_config(
    page_title="CareerCompass BR — Dashboard",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "CareerCompass BR — Portfólio de Análise de Dados (Python + Streamlit + DuckDB)",
    },
)

# ── CSS customizado (acessibilidade: alto contraste, fontes legíveis) ──
st.markdown("""
<style>
    /* Fonte principal ≥ 16px */
    .stMarkdown { font-size: 16px; }
    h1 { font-size: 2rem !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.25rem !important; }

    /* Alerta de dados demo */
    .demo-banner {
        background: linear-gradient(90deg, #FEF3C7, #FDE68A);
        border-left: 4px solid #D97706;
        padding: 12px 16px;
        border-radius: 6px;
        font-weight: 600;
        color: #92400E;
        margin-bottom: 16px;
    }

    /* KPI cards */
    [data-testid="stMetric"] {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #F1F5F9;
    }

    /* Contraste de texto */
    .stApp { color: #1E293B; }

    /* Focus visível para acessibilidade */
    button:focus, a:focus, [tabindex]:focus {
        outline: 3px solid #2563EB !important;
        outline-offset: 2px;
    }
</style>
""", unsafe_allow_html=True)


from src.dashboard.data_loader import FonteDados, carregar_dados, get_snapshot_meta, join_completo
from src.dashboard.pages import about, overview, regions, salaries, stacks


def _sidebar_banner(fonte: FonteDados, meta: dict | None = None) -> None:
    """Exibe banner na sidebar indicando a fonte de dados ativa."""
    if fonte == FonteDados.DUCKDB:
        st.sidebar.success("✅ Conectado ao warehouse DuckDB")
    elif fonte == FonteDados.SNAPSHOT:
        data_geracao = meta.get("data_geracao", "") if meta else ""
        n_vagas = meta.get("jobs_snapshot_linhas", "?") if meta else "?"
        if data_geracao:
            # Converter YYYY-MM-DD para DD/MM/YYYY
            partes = str(data_geracao).split("-")
            if len(partes) == 3:
                data_fmt = f"{partes[2]}/{partes[1]}/{partes[0]}"
            else:
                data_fmt = str(data_geracao)
        else:
            data_fmt = "data desconhecida"
        st.sidebar.markdown(
            '<div class="demo-banner">'
            '📊 <strong>Dados reais coletados</strong><br>'
            f'Amostra de <strong>{n_vagas} vagas</strong> — '
            f'coletadas em {data_fmt}<br>'
            '<span style="font-size:0.85em;">'
            'Execute o pipeline ETL para dados completos.'
            '</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<div class="demo-banner">'
            '⚠️ <strong>Dados de Demonstração</strong><br>'
            'Dataset simulado com ~300 vagas plausíveis.<br>'
            'Execute o pipeline ETL para dados reais.'
            '</div>',
            unsafe_allow_html=True,
        )


def _sidebar_filtros(df) -> dict:
    """Renderiza filtros na sidebar e retorna dict com seleções."""
    st.sidebar.header("🔍 Filtros")

    # Stack / Categoria
    categorias = sorted(df["categoria"].unique())
    cat_sel = st.sidebar.multiselect(
        "Stack / Categoria",
        options=categorias,
        default=categorias,
        key="filter_categoria",
        help="Filtrar por área de atuação",
    )

    # Estado
    estados = sorted(df["estado"].unique())
    uf_sel = st.sidebar.multiselect(
        "Estado",
        options=estados,
        default=estados,
        key="filter_estado",
        help="Filtrar por estado",
    )

    # Cidade (dinâmico ao estado selecionado)
    df_filtrado_parcial = df[df["estado"].isin(uf_sel)]
    cidades = sorted(df_filtrado_parcial["cidade"].unique())
    cid_sel = st.sidebar.multiselect(
        "Cidade",
        options=cidades,
        default=cidades,
        key="filter_cidade",
        help="Filtrar por cidade",
    )

    # Modalidade
    modalidades_labels = {
        "remoto": "🏠 Remoto",
        "hibrido": "🔄 Híbrido",
        "presencial": "🏢 Presencial",
    }
    mod_opcoes = list(modalidades_labels.keys())
    mod_sel = st.sidebar.multiselect(
        "Modalidade",
        options=mod_opcoes,
        default=mod_opcoes,
        format_func=lambda x: modalidades_labels.get(x, x),
        key="filter_modalidade",
        help="Filtrar por modelo de trabalho",
    )

    # Senioridade
    senioridades_labels = {
        "estagio": "📋 Estágio",
        "junior": "🟢 Júnior",
        "pleno": "🟡 Pleno",
        "senior": "🟠 Sênior",
        "lead": "🔴 Lead",
    }
    sen_opcoes = list(senioridades_labels.keys())
    sen_sel = st.sidebar.multiselect(
        "Senioridade",
        options=sen_opcoes,
        default=sen_opcoes,
        format_func=lambda x: senioridades_labels.get(x, x),
        key="filter_senioridade",
        help="Filtrar por nível de senioridade",
    )

    return {
        "categoria": cat_sel,
        "estado": uf_sel,
        "cidade": cid_sel,
        "modalidade": mod_sel,
        "senioridade": sen_sel,
    }


def _aplicar_filtros(df, filtros: dict):
    """Aplica filtros selecionados ao DataFrame."""
    mask = (
        df["categoria"].isin(filtros["categoria"])
        & df["estado"].isin(filtros["estado"])
        & df["cidade"].isin(filtros["cidade"])
        & df["modalidade"].isin(filtros["modalidade"])
        & df["senioridade"].isin(filtros["senioridade"])
    )
    return df[mask].copy()


def main() -> None:
    """Função principal do dashboard."""

    # ── Carregar dados ─────────────────────────────────────────────────
    dados, fonte = carregar_dados()
    df = join_completo(dados)

    # Meta do snapshot (se aplicável)
    snapshot_meta = get_snapshot_meta() if fonte == FonteDados.SNAPSHOT else None

    # ── Sidebar ────────────────────────────────────────────────────────
    with st.sidebar:
        st.image(
            "https://img.shields.io/badge/CareerCompass-BR-2563EB?style=for-the-badge&logo=compass&logoColor=white",
            use_container_width=True,
        )
        st.title("🧭 CareerCompass BR")
        st.caption("Análise de Mercado de TI/Dados no Brasil")

        _sidebar_banner(fonte, snapshot_meta)

        filtros = _sidebar_filtros(df)

        st.divider()
        st.caption(
            f"📊 {len(df)} vagas carregadas\n"
            f"🏢 {df['empresa'].nunique()} empresas\n"
            f"📍 {df['cidade'].nunique()} cidades"
        )

    # ── Aplicar filtros ────────────────────────────────────────────────
    df_filtrado = _aplicar_filtros(df, filtros)

    if df_filtrado.empty:
        st.warning(
            "⚠️ Nenhuma vaga encontrada com os filtros selecionados. "
            "Tente ampliar os filtros na sidebar."
        )
        return

    # ── Navegação ──────────────────────────────────────────────────────
    paginas = {
        "📊 Visão Geral": "overview",
        "💰 Salários": "salaries",
        "🗺️ Regiões": "regions",
        "🧰 Stacks": "stacks",
        "📄 Sobre o Projeto": "about",
    }

    # Radio buttons na sidebar para navegação
    with st.sidebar:
        st.divider()
        pagina_sel = st.radio(
            "Navegação",
            options=list(paginas.keys()),
            key="nav_pagina",
            help="Navegue entre as seções do dashboard",
        )

    # ── Renderizar página ──────────────────────────────────────────────
    pagina_key = paginas[pagina_sel]

    if pagina_key == "overview":
        overview.render(df_filtrado)
    elif pagina_key == "salaries":
        salaries.render(df_filtrado)
    elif pagina_key == "regions":
        regions.render(df_filtrado)
    elif pagina_key == "stacks":
        stacks.render(df_filtrado, dados)
    elif pagina_key == "about":
        about.render()

    # ── Rodapé ─────────────────────────────────────────────────────────
    st.divider()

    # Caveat de cobertura salarial
    total = len(df)
    com_sal = df["salario_min"].notna().sum()
    pct_sal = (com_sal / total * 100) if total > 0 else 0
    st.caption(
        f"⚠️ **Salário divulgado em ~{pct_sal:.0f}% das vagas** "
        f"({com_sal} de {total}). "
        "Muitas empresas não publicam faixa salarial — a análise reflete "
        "apenas o subconjunto disponível."
    )

    st.caption(
        "🧭 **CareerCompass BR** — Portfólio de Análise de Dados | "
        "Dados coletados de fontes públicas (Gupy, GeekHunter, Programathor) | "
        "Licença MIT"
    )


if __name__ == "__main__":
    main()
