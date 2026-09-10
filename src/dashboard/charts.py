"""
Funções de construção de gráficos Plotly para o dashboard.

Todos os gráficos retornam `go.Figure` para composição no Streamlit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.dashboard.utils.normalizacao import VALOR_NAO_INFORMADO, preencher_missing

# ── Paleta de cores (acessível, alto contraste) ───────────────────────
CORES_CATEGORIA = {
    "backend": "#2563EB",
    "frontend": "#7C3AED",
    "dados": "#059669",
    "qa": "#D97706",
    "devops": "#DC2626",
    "mobile": "#DB2777",
    "fullstack": "#0891B2",
}

CORES_MODALIDADE = {
    "remoto": "#2563EB",
    "hibrido": "#7C3AED",
    "presencial": "#059669",
}

COR_NEUTRA = "#6B7280"


def boxplot_salario_por_categoria(df: pd.DataFrame) -> go.Figure:
    """Boxplot de salário médio por categoria (stack)."""
    df_sal = df.dropna(subset=["salario_min", "salario_max"]).copy()
    df_sal["salario_medio"] = (df_sal["salario_min"] + df_sal["salario_max"]) / 2

    if df_sal.empty:
        return _figura_vazia("Sem dados salariais disponíveis")

    fig = px.box(
        df_sal,
        x="categoria",
        y="salario_medio",
        color="categoria",
        color_discrete_map=CORES_CATEGORIA,
        labels={
            "categoria": "Stack / Categoria",
            "salario_medio": "Salário Médio (R$/mês)",
        },
        title="Distribuição Salarial por Stack",
        points="outliers",
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="Stack / Categoria",
        yaxis_title="Salário Médio (R$/mês)",
        font=dict(size=13),
        yaxis_tickformat=",.0f",
        hoverlabel=dict(font_size=13),
    )
    return fig


def bar_vagas_por_estado(df: pd.DataFrame) -> go.Figure:
    """Bar chart: top 15 estados por volume de vagas.

    Estado ausente é exibido como "não informado" (não descartado) —
    escolha documentada em `utils/normalizacao.py`.
    """
    df["estado"] = preencher_missing(df["estado"])
    contagem = (
        df.groupby("estado")
        .size()
        .reset_index(name="vagas")
        .sort_values("vagas", ascending=True)
        .tail(15)
    )

    fig = px.bar(
        contagem,
        x="vagas",
        y="estado",
        orientation="h",
        color="vagas",
        color_continuous_scale="Blues",
        labels={"estado": "Estado", "vagas": "Nº de Vagas"},
        title="Volume de Vagas por Estado",
    )
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        font=dict(size=13),
    )
    return fig


def bar_top_cidades(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Bar chart: top N cidades por volume de vagas.

    Cidade/estado ausentes são exibidos como "não informado".
    """
    df["cidade"] = preencher_missing(df["cidade"])
    df["estado"] = preencher_missing(df["estado"])
    contagem = (
        df.groupby(["cidade", "estado"])
        .size()
        .reset_index(name="vagas")
        .sort_values("vagas", ascending=True)
        .tail(top_n)
    )
    contagem["local"] = contagem["cidade"] + " (" + contagem["estado"] + ")"

    fig = px.bar(
        contagem,
        x="vagas",
        y="local",
        orientation="h",
        color="vagas",
        color_continuous_scale="Teal",
        labels={"local": "Cidade (UF)", "vagas": "Nº de Vagas"},
        title=f"Top {top_n} Cidades com Mais Vagas",
    )
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        font=dict(size=13),
    )
    return fig


def pie_modalidade(df: pd.DataFrame) -> go.Figure:
    """Pizza da distribuição por modalidade."""
    modalidade = preencher_missing(df["modalidade"], label="não informado")
    contagem = modalidade.value_counts().reset_index()
    contagem.columns = ["modalidade", "vagas"]
    labels_map = {"remoto": "Remoto", "hibrido": "Híbrido", "presencial": "Presencial"}
    contagem["modalidade_label"] = contagem["modalidade"].map(
        lambda m: labels_map.get(m, m)
    )
    colors = [CORES_MODALIDADE.get(m, COR_NEUTRA) for m in contagem["modalidade"]]

    fig = px.pie(
        contagem,
        names="modalidade_label",
        values="vagas",
        color="modalidade",
        color_discrete_map=CORES_MODALIDADE,
        title="Distribuição por Modalidade",
        hole=0.35,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(font=dict(size=13))
    return fig


def boxplot_salario_por_modalidade(df: pd.DataFrame) -> go.Figure:
    """Boxplot de salário por modalidade."""
    df_sal = df.dropna(subset=["salario_min", "salario_max"]).copy()
    df_sal["salario_medio"] = (df_sal["salario_min"] + df_sal["salario_max"]) / 2
    labels_map = {"remoto": "Remoto", "hibrido": "Híbrido", "presencial": "Presencial"}
    df_sal["modalidade_label"] = df_sal["modalidade"].map(labels_map)

    if df_sal.empty:
        return _figura_vazia("Sem dados salariais disponíveis")

    fig = px.box(
        df_sal,
        x="modalidade_label",
        y="salario_medio",
        color="modalidade",
        color_discrete_map=CORES_MODALIDADE,
        labels={
            "modalidade_label": "Modalidade",
            "salario_medio": "Salário Médio (R$/mês)",
        },
        title="Salário por Modalidade (Remoto vs Híbrido vs Presencial)",
        points="outliers",
    )
    fig.update_layout(
        showlegend=False,
        font=dict(size=13),
        yaxis_tickformat=",.0f",
    )
    return fig


def heatmap_senioridade_categoria(df: pd.DataFrame) -> go.Figure:
    """Heatmap: senioridade vs categoria (contagem de vagas)."""
    ord_sen = ["estagio", "junior", "pleno", "senior", "lead"]
    labels_sen = {"estagio": "Estágio", "junior": "Júnior", "pleno": "Pleno",
                  "senior": "Sênior", "lead": "Lead"}

    pivot = (
        df.groupby(
            [
                preencher_missing(df["categoria"], label="sem-info"),
                preencher_missing(df["senioridade"], label="não informado"),
            ]
        )
        .size()
        .unstack(fill_value=0)
    )
    # Reordena
    pivot = pivot.reindex(columns=[c for c in ord_sen if c in pivot.columns])
    pivot.columns = [labels_sen.get(c, c) for c in pivot.columns]
    pivot.index = [str(i) for i in pivot.index]

    fig = px.imshow(
        pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        color_continuous_scale="YlOrRd",
        labels=dict(x="Senioridade", y="Categoria", color="Nº de Vagas"),
        title="Heatmap: Senioridade × Stack",
        text_auto=True,
    )
    fig.update_layout(font=dict(size=13))
    return fig


def linha_tendencia_vagas(df: pd.DataFrame) -> go.Figure:
    """Linha: volume de vagas por dia de publicação."""
    df_valid = df.dropna(subset=["publicado_em"]).copy()
    if df_valid.empty:
        return _figura_vazia("Sem datas de publicação disponíveis")

    df_valid["data"] = df_valid["publicado_em"].dt.date
    diario = df_valid.groupby("data").size().reset_index(name="vagas")
    diario = diario.sort_values("data")

    fig = px.line(
        diario,
        x="data",
        y="vagas",
        labels={"data": "Data de Publicação", "vagas": "Nº de Vagas"},
        title="Tendência Diária de Vagas Publicadas",
        markers=True,
    )
    fig.update_layout(font=dict(size=13))
    return fig


def bar_salario_medio_por_categoria(df: pd.DataFrame) -> go.Figure:
    """Bar: salário médio (mediana) por categoria com annotation de cobertura."""
    df_sal = df.dropna(subset=["salario_min", "salario_max"]).copy()
    df_sal["salario_medio"] = (df_sal["salario_min"] + df_sal["salario_max"]) / 2

    stats = (
        df_sal.groupby("categoria")["salario_medio"]
        .agg(["median", "mean", "count"])
        .reset_index()
    )
    stats.columns = ["categoria", "mediana", "media", "n_salario"]
    stats = stats.sort_values("mediana", ascending=True)

    total_por_cat = df.groupby("categoria").size().reset_index(name="total")
    stats = stats.merge(total_por_cat, on="categoria")
    stats["cobertura"] = (stats["n_salario"] / stats["total"] * 100).round(1)
    stats["label"] = stats["categoria"] + " (" + stats["cobertura"].astype(str) + "% cobertura)"

    fig = px.bar(
        stats,
        x="mediana",
        y="label",
        orientation="h",
        color="mediana",
        color_continuous_scale="Blues",
        labels={"label": "Stack (cobertura salarial)", "mediana": "Mediana Salarial (R$/mês)"},
        title="Salário Mediano por Stack (com % de vagas que divulgam salário)",
    )
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        font=dict(size=13),
        xaxis_tickformat=",.0f",
    )

    # Adicionar annotations de média
    for _, row in stats.iterrows():
        fig.add_annotation(
            x=row["media"],
            y=row["label"],
            text=f"Média: R$ {row['media']:,.0f}",
            showarrow=False,
            font=dict(size=10, color="#6B7280"),
            xshift=10,
        )

    return fig


def mapa_bolhas_estado(df: pd.DataFrame) -> go.Figure:
    """Mapa de bolhas por estado usando scatter geo."""
    # Centroides dos estados BR (aproximados)
    _CENTROIDES = {
        "AC": (-8.77, -70.55), "AL": (-9.57, -36.64), "AM": (-3.07, -61.66),
        "AP": (1.42, -51.77), "BA": (-12.57, -41.71), "CE": (-5.20, -39.31),
        "DF": (-15.78, -47.93), "ES": (-19.19, -40.34), "GO": (-15.78, -49.26),
        "MA": (-4.97, -45.28), "MG": (-17.86, -43.13), "MS": (-20.51, -54.55),
        "MT": (-12.64, -55.72), "PA": (-3.79, -52.48), "PB": (-7.28, -36.18),
        "PE": (-8.28, -37.86), "PI": (-7.55, -42.27), "PR": (-24.89, -51.55),
        "RJ": (-22.25, -42.66), "RN": (-5.81, -36.59), "RO": (-11.14, -62.33),
        "RR": (2.82, -62.63), "RS": (-30.03, -53.08), "SC": (-28.16, -48.49),
        "SE": (-10.91, -37.68), "SP": (-22.19, -48.79), "TO": (-10.25, -48.26),
    }

    df_geo = df.copy()
    df_geo["estado"] = preencher_missing(df["estado"])
    contagem = df_geo.groupby("estado").size().reset_index(name="vagas")
    # "não informado" (estado ausente) não tem coordenadas: excluído do mapa.
    # Exceção documentada — barras/tabelas mantêm o rótulo para ser honesto.
    contagem = contagem[contagem["estado"] != VALOR_NAO_INFORMADO]
    contagem["lat"] = contagem["estado"].map(lambda e: _CENTROIDES.get(e, (0, 0))[0])
    contagem["lon"] = contagem["estado"].map(lambda e: _CENTROIDES.get(e, (0, 0))[1])
    contagem["texto"] = contagem["estado"] + ": " + contagem["vagas"].astype(str) + " vagas"

    fig = px.scatter_geo(
        contagem,
        lat="lat",
        lon="lon",
        size="vagas",
        color="vagas",
        hover_name="texto",
        color_continuous_scale="Blues",
        size_max=40,
        projection="natural earth",
        title="Distribuição Geográfica de Vagas por Estado",
        labels={"vagas": "Nº de Vagas"},
    )
    fig.update_geos(
        scope="south america",
        center=dict(lat=-14.24, lon=-51.93),
        projection_scale=4,
        showcountries=False,
        showlakes=True,
        lakecolor="rgb(200,220,255)",
    )
    fig.update_layout(font=dict(size=13))
    return fig


def _figura_vazia(msg: str) -> go.Figure:
    """Retorna figura com mensagem centralizada quando não há dados."""
    fig = go.Figure()
    fig.add_annotation(
        text=msg,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="#6B7280"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
    )
    return fig
