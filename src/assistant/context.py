from dataclasses import dataclass, field


@dataclass(slots=True)
class ToolContext:
    """Estado compartilhado pelas tools durante um único processamento da conversa."""

    excluded_codes: set[str] = field(default_factory=set)
    recommended_codes: list[str] = field(default_factory=list)

    def register_recommendation(self, code: str) -> None:
        if code not in self.excluded_codes:
            self.excluded_codes.add(code)
            self.recommended_codes.append(code)
