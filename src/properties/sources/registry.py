from collections.abc import Callable, Sequence

from django.conf import settings

from properties.sources.base import PropertySource
from properties.sources.files import CsvPropertySource, JsonPropertySource

SourceFactory = Callable[[], PropertySource]

SOURCES: dict[str, SourceFactory] = {
    CsvPropertySource.name: lambda: CsvPropertySource(settings.DATA_DIR / "imoveis.csv"),
    JsonPropertySource.name: lambda: JsonPropertySource(settings.DATA_DIR / "imoveis_resumo.json"),
}


def build_sources(names: Sequence[str] | None = None) -> list[PropertySource]:
    selected = list(names) if names else list(SOURCES)
    unknown = [name for name in selected if name not in SOURCES]
    if unknown:
        raise KeyError(f"origem(ns) desconhecida(s): {', '.join(unknown)}")
    return [SOURCES[name]() for name in selected]
