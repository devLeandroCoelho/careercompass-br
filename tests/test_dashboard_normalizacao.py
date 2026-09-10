"""Testes da normalização defensiva do dashboard.

Regressão do crash de produção (Streamlit Cloud):

    File ".../src/dashboard/app.py", line 134, in _sidebar_filtros
        estados = sorted(df["estado"].unique())
    TypeError: '<' not supported between instances of 'str' and 'float'

O snapshot real mistura NaN (float) com strings na mesma coluna
(`estado` e `cidade`). As funções em `src/dashboard/utils/normalizacao.py`
garantem que `sorted()` nunca compare tipos mistos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]


def _normalizacao() -> tuple:
    """Importa o módulo do dashboard (não é pacote instalável)."""
    sys.path.insert(0, str(_ROOT))
    from src.dashboard.utils.normalizacao import (
        preencher_missing,
        unique_ordered_values,
    )

    return unique_ordered_values, preencher_missing


class TestUniqueOrderedValues:
    """Cobertura da função usada nos filtros da sidebar."""

    def test_mistura_str_float_nao_lanca_typeerror(self) -> None:
        unique_ordered_values, _ = _normalizacao()
        series = pd.Series(["SP", None, "MG", float("nan"), " sp ", "", "RJ"])

        valores = unique_ordered_values(series)

        # Sem TypeError e com tipagem única (str)
        assert all(isinstance(v, str) for v in valores)
        assert valores == ["MG", "não informado", "RJ", "SP"]

    def test_sem_titulo_quando_label_missing_none(self) -> None:
        unique_ordered_values, _ = _normalizacao()
        series = pd.Series(["SP", None, "MG"])

        valores = unique_ordered_values(series, label_missing=None)

        assert valores == ["MG", "SP"]

    def test_pd_na_e_empty_string(self) -> None:
        unique_ordered_values, _ = _normalizacao()
        series = pd.Series(["BA", pd.NA, "", "  ", "BA"])

        valores = unique_ordered_values(series)

        assert valores == ["BA", "não informado"]

    def test_apenas_strings_limpas(self) -> None:
        unique_ordered_values, _ = _normalizacao()
        series = pd.Series(["rj", "SP", "mg"])

        valores = unique_ordered_values(series)

        assert valores == ["mg", "rj", "SP"]


class TestPreencherMissing:
    """Cobertura da função aplicada antes de groupby()/isin()."""

    def test_substitui_nan_por_rotulo(self) -> None:
        _, preencher_missing = _normalizacao()
        series = pd.Series(["SP", None, float("nan"), "RJ"])

        resultado = preencher_missing(series)

        assert resultado.tolist() == ["SP", "não informado", "não informado", "RJ"]
        assert all(isinstance(v, str) for v in resultado.tolist())

    def test_normaliza_espacos_e_vazios(self) -> None:
        _, preencher_missing = _normalizacao()
        series = pd.Series(["  São   Paulo ", "", "Curitiba"])

        resultado = preencher_missing(series)

        assert resultado.tolist() == ["São Paulo", "não informado", "Curitiba"]

    def test_label_personalizado(self) -> None:
        _, preencher_missing = _normalizacao()
        series = pd.Series([None, "remoto"])

        resultado = preencher_missing(series, label="sem-info")

        assert resultado.tolist() == ["sem-info", "remoto"]
