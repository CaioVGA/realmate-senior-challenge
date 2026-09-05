import pytest

from assistant.context import ToolContext
from assistant.tools import AVAILABLE_TOOLS
from assistant.tools.faq import search_faq
from assistant.tools.property_search import find_properties
from properties.models import Property


def test_faq_responde_apenas_com_conteudo_da_base() -> None:
    result = search_faq(ToolContext(), {"pergunta": "quais documentos preciso para alugar?"})

    assert "RG e CPF" in result["resultados"][0]["resposta"]


def test_faq_admite_nao_saber_quando_o_assunto_nao_existe() -> None:
    result = search_faq(ToolContext(), {"pergunta": "vocês vendem terrenos em Fernando de Noronha?"})

    assert result["resultados"] == []
    assert "Nenhuma informação" in result["mensagem"]


@pytest.mark.django_db
def test_busca_sem_filtros_minimos_nao_devolve_imoveis(properties: list[Property]) -> None:
    result = find_properties(ToolContext(), {"bairro": "Boa Viagem"})

    assert "imoveis" not in result
    assert result["erro"] == "filtros_insuficientes"
    assert result["campos_faltando"] == ["tipo_negocio", "preco"]


@pytest.mark.django_db
def test_busca_valida_registra_recomendacoes_no_contexto(properties: list[Property]) -> None:
    context = ToolContext()
    arguments = {"tipo_negocio": "aluguel", "bairro": "boa viagem", "preco_maximo": 10000}

    first = find_properties(context, arguments)
    second = find_properties(context, arguments)

    assert "erro" not in first
    assert "erro" not in second
    assert first["total"] == 2
    assert [listing["codigo"] for listing in first["imoveis"]] == ["IMV-001", "IMV-002"]
    assert [listing["codigo"] for listing in second["imoveis"]] == ["IMV-003"]
    assert context.recommended_codes == ["IMV-001", "IMV-002", "IMV-003"]


def test_tools_expostas_ao_modelo() -> None:
    assert set(AVAILABLE_TOOLS) == {"buscar_imoveis", "consultar_faq"}
