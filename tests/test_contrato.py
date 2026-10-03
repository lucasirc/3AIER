import inspect
import json

import pytest

import agent


def _declacoes():
    for ferramenta in agent.FERRAMENTAS:
        yield ferramenta["function"]


@pytest.mark.contrato
def test_ferramentas_tem_formato_openai():
    assert agent.FERRAMENTAS, "é preciso declarar ao menos uma ferramenta"
    for item in agent.FERRAMENTAS:
        assert item.get("type") == "function"
        funcao = item["function"]
        assert funcao["name"]
        assert funcao["description"]
        params = funcao["parameters"]
        assert params["type"] == "object"
        assert isinstance(params.get("properties"), dict)
        for campo in params.get("required", []):
            assert campo in params["properties"]


@pytest.mark.contrato
def test_toda_declaracao_tem_executor():
    nomes = {item["name"] for item in _declacoes()}
    assert nomes <= set(agent.EXECUTORES)
    for nome in nomes:
        assert callable(agent.EXECUTORES[nome])


@pytest.mark.contrato
def test_todo_executor_esta_declarado():
    declarados = {item["name"] for item in _declacoes()}
    assert set(agent.EXECUTORES) <= declarados


@pytest.mark.contrato
def test_parametros_obrigatorios_casam_com_a_assinatura():
    for funcao in _declacoes():
        assinatura = inspect.signature(agent.EXECUTORES[funcao["name"]])
        obrigatorios = [
            nome
            for nome, param in assinatura.parameters.items()
            if param.default is inspect.Parameter.empty
            and param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]
        assert set(funcao["parameters"].get("required", [])) == set(obrigatorios)


@pytest.mark.contrato
def test_executar_ferramenta_sempre_devolve_json():
    casos = [
        ("somar", {"a": 1, "b": 2}),
        ("somar", {}),
        ("nao_existe", {"a": 1}),
    ]
    for nome, args in casos:
        saida = agent.executar_ferramenta(nome, args)
        assert isinstance(saida, str)
        json.loads(saida)


@pytest.mark.contrato
def test_contrato_somar():
    saida = json.loads(agent.executar_ferramenta("somar", {"a": 4, "b": 5}))
    assert set(saida) == {"resultado"}
    assert saida["resultado"] == 9


@pytest.mark.contrato
def test_carregar_contexto_devolve_texto():
    contexto = agent.carregar_contexto()
    assert isinstance(contexto, str)
    assert contexto.strip()
    assert "Memória" in contexto
