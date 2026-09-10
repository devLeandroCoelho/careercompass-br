"""
Normalização defensiva de valores categóricos do dashboard.

Problema raiz
-------------
O snapshot real (`data/snapshot/*.parquet`) — e o DuckDB — podem conter
valores ausentes (None, pd.NA, np.nan, string vazia) MISTURADOS com strings
na mesma coluna. `sorted(df[col].unique())` então compara ``str`` vs
``float`` e lança ``TypeError``:

    '<' not supported between instances of 'str' and 'float'

Foi exatamente o crash em produção no Streamlit Cloud
(`src/dashboard/app.py:134`, `_sidebar_filtros`).

Escolha de design (documentada)
-------------------------------
Valores ausentes NÃO são descartados: aparecem como **"não informado"** em
filtros, tabelas e gráficos de barra — legível e honesto, pois o dado existe
e só falta a informação. Única exceção: o mapa geográfico de bolhas não tem
coordenadas para "não informado", então essa categoria é excluída ali
(ver `charts.mapa_bolhas_estado`).

Este módulo expõe:
- ``unique_ordered_values(series)`` → lista ordenada de strings, segura
  contra tipos mistos (usada nos filtros da sidebar e páginas).
- ``preencher_missing(series, label)`` → troca ausentes por um rótulo
  legível (usada antes de ``groupby``/``isin`` para manter a consistência).
"""

from __future__ import annotations

import re

import pandas as pd

#: Rótulo padrão para valores ausentes (estado/cidade etc.).
VALOR_NAO_INFORMADO = "não informado"

#: Strings que representam ausência quando uma coluna object guarda
#: o valor como texto (ex.: parquet convertido errado).
_TEXTO_AUSENTE = {"", "nan", "none", "nat", "na", "n/a", "null", "undefined"}

_WHITESPACE = re.compile(r"\s+")


def _limpar_str(valor: object) -> str | None:
    """Converte valor para string normalizada, ou None se ausente/vazio.

    Aceita qualquer tipo (str, float NaN, None, pd.NA) sem lançar.
    ```
    """
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip()
    if texto.lower() in _TEXTO_AUSENTE:
        return None
    # Colapsa espaços/quebras de linha recorrentes em um único espaço
    texto = _WHITESPACE.sub(" ", texto).strip()
    return texto or None


def unique_ordered_values(
    series: pd.Series,
    *,
    label_missing: str | None = VALOR_NAO_INFORMADO,
) -> list[str]:
    """Valores únicos da série como lista ordenada de strings, SEM tipos mistos.

    - Remove None/pd.NA/np.nan/string vazia (e '' / 'nan' textual).
    - Converte tudo para ``str`` e normaliza espaços.
    - Deduplica sem diferenciar maiúsculas (o primeiro valor visto define o
      texto exibido — evita "SP" e " sp " virarem duas opções).
    - Ordena de forma segura (case-insensitive) — nunca compara str x float.
    - Se houver valores ausentes e ``label_missing`` for informado, inclui
      o rótulo na lista (padrão: "não informado").

    Exemplo:
        >>> unique_ordered_values(pd.Series(["SP", None, "MG", float("nan")]))
        ['MG', 'SP', 'não informado']
    """
    vistos: dict[str, str] = {}
    tem_missing = False
    for valor in series.tolist():
        limpo = _limpar_str(valor)
        if limpo is None:
            tem_missing = True
        else:
            vistos.setdefault(limpo.casefold(), limpo)
    if tem_missing and label_missing is not None:
        vistos.setdefault(label_missing.casefold(), label_missing)
    return sorted(vistos.values(), key=str.casefold)


def preencher_missing(
    series: pd.Series,
    label: str = VALOR_NAO_INFORMADO,
) -> pd.Series:
    """Substitui ausentes (None/NA/nan/vazio) por ``label`` e limpa o texto.

    Retorna uma cópia com dtype object composto só de strings → elimina
    colunas object com float NaN, garantindo que ``sorted()``/``groupby()``
    não recebam tipos mistos.
    """

    def _normalizar(valor: object) -> str:
        limpo = _limpar_str(valor)
        return label if limpo is None else limpo

    return series.map(_normalizar)