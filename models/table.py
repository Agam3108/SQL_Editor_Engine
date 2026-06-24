from dataclasses import dataclass, field


@dataclass
class Table:
    columns: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
