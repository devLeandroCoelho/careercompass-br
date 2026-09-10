"""Página: 🧰 Stacks — Análise de tecnologias e skills mais requisitadas."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from ..charts import CORES_CATEGORIA, heatmap_senioridade_categoria


def render(df: pd.DataFrame, dados: dict[str, pd.DataFrame]) -> None:
    """Renderiza a página de stacks/tecnologias."""
    st.header("🧰 Stacks e Tecnologias")

    # ── Skills mais requisitadas ───────────────────────────────────────
    st.subheader("Skills Mais Requisitadas")

    if "dim_skill" in dados and "fact_job_skill" in dados:
        skills = dados["dim_skill"]
        job_skills = dados["fact_job_skill"]

        # Join para ter nome da skill
        skills_count = (
            job_skills.merge(skills, on="skill_id")
            .groupby("nome")
            .size()
            .reset_index(name="vagas")
            .sort_values("vagas", ascending=True)
            .tail(25)
        )

        fig_skills = px.bar(
            skills_count,
            x="vagas",
            y="nome",
            orientation="h",
            color="vagas",
            color_continuous_scale="Viridis",
            labels={"nome": "Skill / Tecnologia", "vagas": "Nº de Vagas que Requerem"},
            title="Top 25 Skills Mais Requisitadas",
        )
        fig_skills.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            font=dict(size=13),
            height=600,
        )
        st.plotly_chart(fig_skills, use_container_width=True, key="stk_skills")
    else:
        st.info("📊 Dados de skills não disponíveis. O pipeline ETL precisa extrair skills das vagas.")

    st.divider()

    # ── Vagas por categoria ────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição por Categoria")
        cat_counts = df["categoria"].value_counts().reset_index()
        cat_counts.columns = ["categoria", "vagas"]

        fig_cat = px.pie(
            cat_counts,
            names="categoria",
            values="vagas",
            color="categoria",
            color_discrete_map=CORES_CATEGORIA,
            hole=0.35,
            title="Proporção de Vagas por Stack",
        )
        fig_cat.update_traces(textposition="inside", textinfo="percent+label")
        fig_cat.update_layout(font=dict(size=13))
        st.plotly_chart(fig_cat, use_container_width=True, key="stk_pie_cat")

    with col2:
        st.subheader("Vagas por Categoria")
        fig_cat_bar = px.bar(
            cat_counts.sort_values("vagas", ascending=True),
            x="vagas",
            y="categoria",
            orientation="h",
            color="categoria",
            color_discrete_map=CORES_CATEGORIA,
            labels={"categoria": "Categoria", "vagas": "Nº de Vagas"},
        )
        fig_cat_bar.update_layout(
            showlegend=False,
            font=dict(size=13),
        )
        st.plotly_chart(fig_cat_bar, use_container_width=True, key="stk_bar_cat")

    st.divider()

    # ── Heatmap senioridade × categoria ────────────────────────────────
    st.subheader("Heatmap: Senioridade × Stack")
    fig_heat = heatmap_senioridade_categoria(df)
    st.plotly_chart(fig_heat, use_container_width=True, key="stk_heatmap")

    # ── Skills por categoria (tabela) ──────────────────────────────────
    st.divider()
    st.subheader("Skills por Categoria (frequência)")

    if "dim_skill" in dados and "fact_job_skill" in dados:
        skills = dados["dim_skill"]
        job_skills = dados["fact_job_skill"]
        fj = dados["fact_job"]

        # Join completo
        js_full = job_skills.merge(skills, on="skill_id").merge(
            fj[["job_id", "categoria_principal"]], on="job_id"
        )

        # Top 5 skills por categoria
        for cat in sorted(df["categoria"].unique()):
            cat_skills = (
                js_full[js_full["categoria_principal"] == cat]
                .groupby("nome")
                .size()
                .reset_index(name="frequencia")
                .sort_values("frequencia", ascending=False)
                .head(8)
            )
            if not cat_skills.empty:
                with st.expander(f"📌 {cat.upper()} — Top 8 Skills"):
                    st.dataframe(
                        cat_skills,
                        column_config={
                            "nome": "Skill",
                            "frequencia": st.column_config.NumberColumn("Frequência"),
                        },
                        use_container_width=True,
                        hide_index=True,
                    )
