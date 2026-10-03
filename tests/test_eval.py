import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import agent


def _recado(content=None, tool_calls=None):
    recado = MagicMock()
    recado.content = content
    recado.tool_calls = tool_calls
    recado.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {
                "id": chamada.id,
                "type": "function",
                "function": {
                    "name": chamada.function.name,
                    "arguments": chamada.function.arguments,
                },
            }
            for chamada in (tool_calls or [])
        ],
    }
    return recado


def _chamada_ferramenta(nome, argumentos, call_id="call_1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=nome, arguments=json.dumps(argumentos)),
    )


def _cliente_com_respostas(recados):
    fila = list(recados)

    def create(**_kwargs):
        if not fila:
            raise AssertionError("o modelo foi chamado além das respostas previstas")
        return SimpleNamespace(choices=[SimpleNamespace(message=fila.pop(0))])

    cliente = MagicMock()
    cliente.chat.completions.create.side_effect = create
    return cliente


def avaliar(resposta: str, criterios: list) -> float:
    if not criterios:
        return 0.0
    return sum(1 for criterio in criterios if criterio(resposta)) / len(criterios)


@pytest.mark.eval
def test_eval_resposta_direta_sem_ferramenta(monkeypatch):
    esperado = "Não sei. Prefiro não inventar."
    monkeypatch.setattr(
        agent,
        "get_cliente",
        lambda: _cliente_com_respostas([_recado(content=esperado)]),
    )

    mensagens = [{"role": "user", "content": "qual o preço do plano?"}]
    resposta = agent.responder(mensagens)

    score = avaliar(
        resposta,
        [
            lambda texto: texto == esperado,
            lambda texto: "não sei" in texto.lower() or "nao sei" in texto.lower(),
        ],
    )
    assert score == 1.0


@pytest.mark.eval
def test_eval_loop_usa_somar_e_responde_com_resultado(monkeypatch):
    monkeypatch.setattr(
        agent,
        "get_cliente",
        lambda: _cliente_com_respostas(
            [
                _recado(tool_calls=[_chamada_ferramenta("somar", {"a": 1234, "b": 5678})]),
                _recado(content="O resultado exato é 6912."),
            ]
        ),
    )

    mensagens = [{"role": "user", "content": "quanto é 1234 mais 5678?"}]
    resposta = agent.responder(mensagens)

    resultado_ferramenta = json.loads(mensagens[-2]["content"])
    score = avaliar(
        resposta,
        [
            lambda texto: "6912" in texto,
            lambda texto: texto.strip() != "",
        ],
    )
    assert resultado_ferramenta == {"resultado": 6912}
    assert mensagens[-2]["role"] == "tool"
    assert score == 1.0


@pytest.mark.eval
def test_eval_respeita_limite_de_iteracoes(monkeypatch):
    monkeypatch.setattr(agent, "MAX_ITERACOES", 2)
    monkeypatch.setattr(
        agent,
        "get_cliente",
        lambda: _cliente_com_respostas(
            [
                _recado(tool_calls=[_chamada_ferramenta("somar", {"a": 1, "b": 1}, call_id="c1")]),
                _recado(tool_calls=[_chamada_ferramenta("somar", {"a": 2, "b": 2}, call_id="c2")]),
            ]
        ),
    )

    resposta = agent.responder([{"role": "user", "content": "some sem parar"}])
    score = avaliar(
        resposta,
        [
            lambda texto: "limite" in texto.lower(),
            lambda texto: "iterações" in texto.lower() or "iteracoes" in texto.lower(),
        ],
    )
    assert score == 1.0


@pytest.mark.eval
def test_eval_contexto_inclui_identidade_e_memoria():
    contexto = agent.carregar_contexto()
    score = avaliar(
        contexto,
        [
            lambda texto: "Identidade" in texto or "assistente" in texto.lower(),
            lambda texto: "Não invente" in texto or "não invente" in texto.lower(),
            lambda texto: "Memória" in texto,
        ],
    )
    assert score >= 2 / 3
