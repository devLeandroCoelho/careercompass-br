"""Página: 💰 Salários — Análise salarial por stack, modalidade e região."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..charts import (
    bar_salario_medio_por_categoria,
    boxplot_salario_por_categoria,
    boxplot_salario_por_modalidade,
)


def render(df: pd.DataFrame) -> None:
    """Renderiza a página de salários."""
    st.header("💰 Análise Salarial")

    df_sal = df.dropna(subset=["salario_min", "salario_max"]).copy()

    if df_sal.empty:
        st.warning("⚠️ Nenhum dado salarial disponível. O pipeline ETL precisa "
                    "coletar faixas salariais das fontes.")
        return

    # ── Nota de cobertura ──────────────────────────────────────────────
    total = len(df)
    com_sal = len(df_sal)
    pct = com_sal / total * 100 if total > 0 else 0

    st.info(
        f"📋 **Cobertura salarial**: {com_sal} de {total} vagas divulgam faixa salarial "
        f"({pct:.1f}%). A análise abaixo reflete **apenas esse subconjunto**."
    )

    st.divider()

    # ── KPIs salariais ─────────────────────────────────────────────────
    df_sal["salario_medio"] = (df_sal["salario_min"] + df_sal["salario_max"]) / 2
    mediana_geral = df_sal["salario_medio"].median()
    media_geral = df_sal["salario_medio"].mean()
    min_geral = df_sal["salario_min"].min()
    max_geral = df_sal["salario_max"].max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mediana Geral", f"R$ {mediana_geral:,.0f}")
    c2.metric("Média Geral", f"R$ {media_geral:,.0f}")
    c3.metric("Mínimo", f"R$ {min_geral:,.0f}")
    c4.metric("Máximo", f"R$ {max_geral:,.0f}")

    st.divider()

    # ── Boxplot por categoria ──────────────────────────────────────────
    st.subheader("Distribuição Salarial por Stack")
    fig_box = boxplot_salario_por_categoria(df_sal)
    st.plotly_chart(fig_box, use_container_width=True, key="sal_boxplot_categoria")

    # ── Bar de mediana com cobertura ───────────────────────────────────
    st.subheader("Salário Mediano por Stack (com cobertura)")
    fig_bar = bar_salario_medio_por_categoria(df)
    st.plotly_chart(fig_bar, use_container_width=True, key="sal_bar_mediana")

    # ── Boxplot por modalidade ─────────────────────────────────────────
    st.subheader("Salário por Modalidade")
    fig_mod = boxplot_salario_por_modalidade(df_sal)
    st.plotly_chart(fig_mod, use_container_width=True, key="sal_boxplot_modalidade")

    # ── Tabela resumo ──────────────────────────────────────────────────
    st.subheader("Tabela Resumo por Stack")
    resumo = (
        df_sal.groupby("categoria")["salario_medio"]
        .agg(["median", "mean", "min", "max", "count"])
        .round(0)
        .rename(columns={
            "median": "Mediana",
            "mean": "Média",
            "min": "Mínimo",
            "max": "Máximo",
            "count": "Nº vagas c/ salário",
        })
    )
    # Adicionar coluna de cobertura
    total_por_cat = df.groupby("categoria").size().reset_index(name="Nº total vagas")
    resumo = resumo.merge(total_por_cat, on="categoria", how="left")
    resumo["Cobertura %"] = (resumo["Nº vagas c/ salário"] / resumo["Nº total vagas"] * 100).round(1)
    resumo = resumo.sort_values("Mediana", ascending=False)

    st.dataframe(
        resumo.style.format({
            "Mediana": "R$ {:,.0f}",
            "Média": "R$ {:,.0f}",
            "Mínimo": "R$ {:,.0f}",
            "Máximo": "R$ {:,.0f}",
            "Cobertura %": "{:.1f}%",
        }),
        use_container_width=True,
    )

    # ── Disclaimer ─────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "⚠️ **Limitação**: Os salários refletem apenas as vagas que divulgam faixa salarial "
        "publicada. Muitas empresas não publicam salário em anúncios. Esta análise NÃO "
        "representa o salário real de mercado — é um indicador da informação disponível "
        "nas fontes coletadas."
    )
