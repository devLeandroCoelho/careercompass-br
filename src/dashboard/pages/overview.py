"""Página: 📊 Visão Geral — KPIs e resumo do mercado."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import (
    bar_vagas_por_estado,
    pie_modalidade,
    linha_tendencia_vagas,
    mapa_bolhas_estado,
)


def render(df: pd.DataFrame) -> None:
    """Renderiza a página de visão geral."""
    st.header("📊 Visão Geral do Mercado")

    # ── KPIs ───────────────────────────────────────────────────────────
    total_vagas = len(df)
    n_empresas = df["empresa"].nunique()
    n_cidades = df["cidade"].nunique()
    n_estados = df["estado"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Vagas", f"{total_vagas:,}")
    col2.metric("Empresas", f"{n_empresas:,}")
    col3.metric("Cidades", f"{n_cidades:,}")
    col4.metric("Estados", f"{n_estados:,}")

    st.divider()

    # ── Modalidade ─────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Distribuição por Modalidade")
        fig_modalidade = pie_modalidade(df)
        st.plotly_chart(fig_modalidade, use_container_width=True, key="overview_pie_modalidade")

    with col_right:
        st.subheader("Volume de Vagas por Estado")
        fig_estado = bar_vagas_por_estado(df)
        st.plotly_chart(fig_estado, use_container_width=True, key="overview_bar_estado")

    # ── Mapa + Tendência ──────────────────────────────────────────────
    st.subheader("Distribuição Geográfica")
    fig_mapa = mapa_bolhas_estado(df)
    st.plotly_chart(fig_mapa, use_container_width=True, key="overview_mapa")

    # Tendência (só se houver datas)
    df_com_data = df.dropna(subset=["publicado_em"])
    if not df_com_data.empty:
        st.subheader("Tendência Diária de Vagas")
        fig_tendencia = linha_tendencia_vagas(df_com_data)
        st.plotly_chart(fig_tendencia, use_container_width=True, key="overview_tendencia")
    else:
        st.info("📅 Datas de publicação não disponíveis neste dataset.")

    # ── Resumo textual ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Resumo Rápido")

    # Modalidade mais comum
    mod_counts = df["modalidade"].value_counts()
    mod_top = mod_counts.index[0] if len(mod_counts) > 0 else "N/A"
    labels = {"remoto": "Remoto", "hibrido": "Híbrido", "presencial": "Presencial"}

    # Estado com mais vagas
    uf_counts = df["estado"].value_counts()
    uf_top = uf_counts.index[0] if len(uf_counts) > 0 else "N/A"

    st.markdown(f"""
    - **Modalidade predominante**: {labels.get(mod_top, mod_top)} ({mod_counts.iloc[0] if len(mod_counts) > 0 else 0} vagas)
    - **Estado com mais vagas**: {uf_top} ({uf_counts.iloc[0] if len(uf_counts) > 0 else 0} vagas)
    - **Período coberto**: {df['publicado_em'].min().strftime('%d/%m/%Y') if df['publicado_em'].notna().any() else 'N/A'} a {df['publicado_em'].max().strftime('%d/%m/%Y') if df['publicado_em'].notna().any() else 'N/A'}
    """)
