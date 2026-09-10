"""Página: 🗺️ Regiões — Distribuição geográfica de vagas."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import (
    bar_top_cidades,
    bar_vagas_por_estado,
    mapa_bolhas_estado,
)


def render(df: pd.DataFrame) -> None:
    """Renderiza a página de regiões."""
    st.header("🗺️ Regiões e Localização")

    # ── Mapa ───────────────────────────────────────────────────────────
    st.subheader("Mapa de Vagas por Estado")
    fig_mapa = mapa_bolhas_estado(df)
    st.plotly_chart(fig_mapa, use_container_width=True, key="reg_mapa")

    # ── Top estados ────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Estados")
        fig_est = bar_vagas_por_estado(df)
        st.plotly_chart(fig_est, use_container_width=True, key="reg_bar_estado")

    with col2:
        st.subheader("Top 10 Cidades")
        fig_cid = bar_top_cidades(df, top_n=10)
        st.plotly_chart(fig_cid, use_container_width=True, key="reg_bar_cidades")

    # ── Tabela detalhada ──────────────────────────────────────────────
    st.divider()
    st.subheader("Detalhamento por Estado")

    uf_stats = (
        df.groupby("estado")
        .agg(
            vagas=("id", "count"),
            empresas=("empresa", "nunique"),
            cidades=("cidade", "nunique"),
        )
        .sort_values("vagas", ascending=False)
        .reset_index()
    )

    # Adicionar info de modalidade
    mod_pivot = df.groupby(["estado", "modalidade"]).size().unstack(fill_value=0)
    for col in ["remoto", "hibrido", "presencial"]:
        if col not in mod_pivot.columns:
            mod_pivot[col] = 0
    mod_pivot = mod_pivot[["remoto", "hibrido", "presencial"]]
    mod_pivot.columns = ["Remoto", "Híbrido", "Presencial"]
    mod_pivot = mod_pivot.reset_index()

    uf_stats = uf_stats.merge(mod_pivot, on="estado", how="left")

    # Mapear nomes dos estados
    _UF_NOMES = {
        "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
        "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
        "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
        "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
        "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí",
        "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
        "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
        "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
        "TO": "Tocantins",
    }
    uf_stats["Estado"] = uf_stats["estado"].map(_UF_NOMES)

    st.dataframe(
        uf_stats[["Estado", "vagas", "empresas", "cidades", "Remoto", "Híbrido", "Presencial"]],
        column_config={
            "vagas": st.column_config.NumberColumn("Vagas"),
            "empresas": st.column_config.NumberColumn("Empresas"),
            "cidades": st.column_config.NumberColumn("Cidades"),
            "Remoto": st.column_config.NumberColumn("Remoto"),
            "Híbrido": st.column_config.NumberColumn("Híbrido"),
            "Presencial": st.column_config.NumberColumn("Presencial"),
        },
        use_container_width=True,
        hide_index=True,
    )
