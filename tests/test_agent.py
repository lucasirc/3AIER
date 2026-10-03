import json
from pathlib import Path

import agent


def test_somar():
    assert agent.somar(2, 3) == {"resultado": 5}
    assert agent.somar(-1.5, 0.5) == {"resultado": -1.0}


def test_executar_ferramenta_somar():
    saida = agent.executar_ferramenta("somar", {"a": 10, "b": 20})
    assert json.loads(saida) == {"resultado": 30}


def test_executar_ferramenta_inexistente():
    saida = json.loads(agent.executar_ferramenta("nao_existe", {}))
    assert "erro" in saida


def test_executar_ferramenta_argumentos_invalidos():
    saida = json.loads(agent.executar_ferramenta("somar", {"a": 1}))
    assert "erro" in saida


def test_carregar_contexto(tmp_path, monkeypatch):
    agent_md = tmp_path / "agent.md"
    memory_md = tmp_path / "memory.md"
    agent_md.write_text("sou o agente", encoding="utf-8")
    memory_md.write_text("lembro disto", encoding="utf-8")
    monkeypatch.setattr(agent, "AGENT_MD", agent_md)
    monkeypatch.setattr(agent, "MEMORY_MD", memory_md)

    contexto = agent.carregar_contexto()
    assert "sou o agente" in contexto
    assert "lembro disto" in contexto


def test_carregar_contexto_sem_arquivos(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "AGENT_MD", tmp_path / "agent.md")
    monkeypatch.setattr(agent, "MEMORY_MD", tmp_path / "memory.md")

    contexto = agent.carregar_contexto()
    assert "assistente" in contexto.lower()
