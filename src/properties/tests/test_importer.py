import pytest

from properties.models import Property
from properties.services import import_properties

pytestmark = pytest.mark.django_db


def test_carga_mescla_csv_e_json_em_uma_unica_tabela() -> None:
    summary = import_properties()

    assert summary.created == 20
    assert Property.objects.filter(source="csv").count() == 10
    assert Property.objects.filter(source="json").count() == 10
    assert Property.objects.filter(code__in=["IMV-001", "C011"]).count() == 2


def test_carga_repetida_nao_duplica_e_atualiza_registros() -> None:
    import_properties()
    Property.objects.filter(code="IMV-001").update(price=1)

    summary = import_properties()

    assert summary.created == 0
    assert summary.updated == 20
    assert Property.objects.count() == 20
    assert Property.objects.get(code="IMV-001").price == 2500
