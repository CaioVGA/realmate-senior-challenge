from decimal import Decimal

import pytest

from conversations.models import Conversation
from properties.models import Property, TransactionType


@pytest.fixture
def conversation() -> Conversation:
    return Conversation.objects.create(user_phone="+5581982860171")


@pytest.fixture
def properties() -> list[Property]:
    return [
        make_property(code="IMV-001", neighborhood="Boa Viagem", price=Decimal("2500"), bedrooms=2),
        make_property(code="IMV-002", neighborhood="Boa Viagem", price=Decimal("2800"), bedrooms=3),
        make_property(code="IMV-003", neighborhood="Boa Viagem", price=Decimal("6000"), bedrooms=4),
        make_property(
            code="IMV-004",
            neighborhood="Casa Forte",
            price=Decimal("850000"),
            bedrooms=4,
            transaction_type=TransactionType.SALE,
        ),
    ]


def make_property(
    code: str,
    neighborhood: str = "Boa Viagem",
    price: Decimal = Decimal("2000"),
    bedrooms: int = 2,
    transaction_type: str = TransactionType.RENT,
) -> Property:
    return Property.objects.create(
        code=code,
        transaction_type=transaction_type,
        neighborhood=neighborhood,
        price=price,
        bedrooms=bedrooms,
        address="Rua Teste, 100",
        description=f"Imóvel de teste {code}",
        source="test",
    )
