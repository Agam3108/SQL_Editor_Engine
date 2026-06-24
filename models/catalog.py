from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnSchema:
    col_name: str
    col_type: str = "STRING"


@dataclass
class TableSchema:
    table_name: str
    columns: list[ColumnSchema] = field(default_factory=list)


@dataclass
class Catalog:
    tables: list[TableSchema] = field(default_factory=list)

    def get_table(self, name: str) -> Optional[TableSchema]:
        return next((t for t in self.tables if t.table_name == name), None)
