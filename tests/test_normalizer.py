"""Testes do normalizador — stack, senioridade, salário, localização, modalidade."""

from __future__ import annotations

from careercompass.ingestion.base import RawJob
from careercompass.processing.normalizer import (
    normalize_cidade_estado,
    normalize_job,
    normalize_modalidade,
    normalize_salario,
    normalize_senioridade,
    normalize_stack,
)


class TestNormalizeStack:
    """Detecção de skills/stack no título+descrição."""

    def test_python_sql_detected(self) -> None:
        result = normalize_stack("Analista de Dados Python SQL")
        assert "dados" in result["matches"]
        assert "python" in result["skills"]
        assert "sql" in result["skills"]

    def test_react_detected(self) -> None:
        result = normalize_stack("Desenvolvedor React TypeScript")
        assert "frontend" in result["matches"]

    def test_docker_aws_detected(self) -> None:
        result = normalize_stack("DevOps Engineer Docker AWS", "Trabalhar com CI/CD")
        assert "devops" in result["matches"]

    def test_empty_input(self) -> None:
        result = normalize_stack("")
        assert result["matches"] == []
        assert result["skills"] == []

    def test_no_match(self) -> None:
        result = normalize_stack("Vaga de vendas")
        assert "dados" not in result["matches"]


class TestNormalizeSenioridade:
    """Extração de nível de senioridade."""

    def test_junior(self) -> None:
        assert normalize_senioridade("Analista de Dados Júnior") == "junior"

    def test_pleno(self) -> None:
        assert normalize_senioridade("Desenvolvedor Pleno Python") == "pleno"

    def test_senior(self) -> None:
        assert normalize_senioridade("Engenheiro Sênior de Dados") == "senior"

    def test_lideranca(self) -> None:
        assert normalize_senioridade("Líder de Equipe de Dados") == "lideranca"

    def test_gerente(self) -> None:
        assert normalize_senioridade("Gerente de Engenharia") == "lideranca"

    def test_sem_info(self) -> None:
        assert normalize_senioridade("Vaga de analista") == "sem-info"

    def test_empty(self) -> None:
        assert normalize_senioridade("") == "sem-info"


class TestNormalizeSalario:
    """Normalização de salários."""

    def test_structured_values(self) -> None:
        min_val, max_val, moeda = normalize_salario(3000.0, 5000.0, "BRL")
        assert min_val == 3000.0
        assert max_val == 5000.0
        assert moeda == "BRL"

    def test_a_combinar(self) -> None:
        min_val, max_val, moeda = normalize_salario(salario_raw="A combinar")
        assert min_val is None
        assert max_val is None

    def test_raw_with_values(self) -> None:
        min_val, max_val, moeda = normalize_salario(salario_min=2000.0, salario_max=3000.0)
        assert min_val == 2000.0
        assert moeda == "BRL"

    def test_no_salary(self) -> None:
        min_val, max_val, moeda = normalize_salario()
        assert min_val is None


class TestNormalizeModalidade:
    """Normalização de modalidade de trabalho."""

    def test_remoto(self) -> None:
        assert normalize_modalidade("remoto") == "remoto"
        assert normalize_modalidade(None, "Vaga Remota") == "remoto"

    def test_hibrido(self) -> None:
        assert normalize_modalidade("híbrido") == "hibrido"

    def test_presencial(self) -> None:
        assert normalize_modalidade("presencial") == "presencial"

    def test_nao_informado(self) -> None:
        assert normalize_modalidade(None) == "nao-informado"


class TestNormalizeCidadeEstado:
    """Normalização de cidade e estado."""

    def test_sao_paulo_sp(self) -> None:
        cidade, uf = normalize_cidade_estado("São Paulo", "SP")
        assert cidade == "São Paulo"
        assert uf == "SP"

    def test_nome_completo_estado(self) -> None:
        cidade, uf = normalize_cidade_estado("Curitiba", "Paraná")
        assert uf == "PR"

    def test_fixes_cidade(self) -> None:
        cidade, _ = normalize_cidade_estado("sao paulo", None)
        assert cidade == "São Paulo"

    def test_estado_invalido(self) -> None:
        _, uf = normalize_cidade_estado("Campinas", "XX")
        assert uf is None


class TestNormalizeJob:
    """Integração: normalização completa de um RawJob."""

    def test_full_normalization(self) -> None:
        job = RawJob(
            fonte="gupy",
            id="1",
            titulo="Analista de Dados Júnior Python SQL",
            empresa="TechCorp",
            cidade="São Paulo",
            estado="SP",
            url="https://example.com/1",
            modalidade="remote",
            salario_min=3000.0,
            salario_max=5000.0,
            salario_moeda="BRL",
            descricao="Vaga com pandas e power bi",
        )
        result = normalize_job(job)

        assert result["senioridade"] == "junior"
        assert result["modalidade"] == "remoto"
        assert "dados" in result["stack_matches"]
        assert "python" in result["stack_skills"]
        assert result["cidade"] == "São Paulo"
        assert result["estado"] == "SP"
        assert result["salario_min"] == 3000.0
