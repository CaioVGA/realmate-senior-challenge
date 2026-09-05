import re
import unicodedata

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")

_STOPWORDS = frozenset(
    {
        "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
        "e", "em", "eh", "essa", "esse", "esta", "este", "eu", "faz", "fazer",
        "isso", "meu", "minha", "na", "nas", "no", "nos", "o", "os", "ou",
        "para", "pelo", "pela", "por", "posso", "pra", "qual", "quais", "quando",
        "que", "quem", "se", "sem", "ser", "sobre", "sua", "seu", "tem", "ter",
        "um", "uma", "voces", "vcs",
    }
)


def normalize(value: str) -> str:
    """Minúsculas, sem acentos e sem pontuação, para casar o texto livre digitado pelo cliente."""
    decomposed = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NON_ALPHANUMERIC.sub(" ", without_accents).strip()


def tokenize(value: str) -> set[str]:
    return {token for token in normalize(value).split() if len(token) > 2 and token not in _STOPWORDS}
