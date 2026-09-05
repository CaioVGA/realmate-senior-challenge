import csv
import json
import re
from collections.abc import Iterator, Mapping
from typing import ClassVar

from properties.sources.base import FilePropertySource


class CsvPropertySource(FilePropertySource):
    name: ClassVar[str] = "csv"
    code_pattern: ClassVar[re.Pattern[str]] = re.compile(r"codigo\s*:\s*(?P<code>[\w-]+)", re.IGNORECASE)

    def read_rows(self) -> Iterator[Mapping[str, object]]:
        with self.path.open(encoding="utf-8", newline="") as handler:
            yield from csv.DictReader(handler)


class JsonPropertySource(FilePropertySource):
    name: ClassVar[str] = "json"
    code_pattern: ClassVar[re.Pattern[str]] = re.compile(r"ref\s*:\s*(?P<code>[\w-]+)", re.IGNORECASE)

    def read_rows(self) -> Iterator[Mapping[str, object]]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{self.path.name} deveria conter uma lista de imóveis")
        for row in payload:
            if isinstance(row, dict):
                yield row
