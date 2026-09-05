from decimal import Decimal

import pytest

from properties.models import Property
from properties.services import IncompleteFiltersError, PropertyFilters, search_properties

pytestmark = pytest.mark.django_db


def test_busca_sem_filtros_obrigatorios_nao_retorna_imoveis(properties: list[Property]) -> None:
    with pytest.raises(IncompleteFiltersError) as error:
        search_properties(PropertyFilters(neighborhood="Boa Viagem"))

    assert error.value.missing == ("tipo_negocio", "preco")


def test_tipo_de_negocio_invalido_conta_como_ausente(properties: list[Property]) -> None:
    with pytest.raises(IncompleteFiltersError) as error:
        search_properties(
            PropertyFilters(transaction_type="temporada", neighborhood="Boa Viagem", max_price=Decimal("3000"))
        )

    assert error.value.missing == ("tipo_negocio",)


def test_codigo_dispensa_os_demais_filtros(properties: list[Property]) -> None:
    found = search_properties(PropertyFilters(code="imv-004"))

    assert [listing.code for listing in found] == ["IMV-004"]


def test_faixa_de_preco_e_bairro_sem_acento(properties: list[Property]) -> None:
    found = search_properties(
        PropertyFilters(
            transaction_type="aluguel",
            neighborhood="boa viagem",
            min_price=Decimal("2600"),
            max_price=Decimal("7000"),
        )
    )

    assert [listing.code for listing in found] == ["IMV-002", "IMV-003"]


def test_limite_de_dois_imoveis_por_busca(properties: list[Property]) -> None:
    found = search_properties(
        PropertyFilters(transaction_type="aluguel", neighborhood="Boa Viagem", max_price=Decimal("10000"))
    )

    assert len(found) == 2


def test_busca_por_codigo_ignora_a_exclusao_de_recomendados(properties: list[Property]) -> None:
    found = search_properties(PropertyFilters(code="IMV-001"), exclude_codes=["IMV-001"])

    assert [listing.code for listing in found] == ["IMV-001"]


def test_imoveis_ja_recomendados_sao_excluidos(properties: list[Property]) -> None:
    found = search_properties(
        PropertyFilters(transaction_type="aluguel", neighborhood="Boa Viagem", max_price=Decimal("10000")),
        exclude_codes=["IMV-001", "IMV-002"],
    )

    assert [listing.code for listing in found] == ["IMV-003"]
