from decimal import Decimal, InvalidOperation


def as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_int(value: object) -> int | None:
    text = as_text(value)
    if text is None:
        return None
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def as_decimal(value: object) -> Decimal | None:
    text = as_text(value)
    if text is None:
        return None
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None
