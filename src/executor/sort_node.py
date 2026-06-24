from models.plan import PlanNode
from models.table import Table


class SortNode:
    def __init__(self, plan: PlanNode) -> None:
        self._plan = plan

    def execute(self, table: Table) -> Table:
        try:
            col_idx = table.columns.index(self._plan.column)
        except ValueError:
            return table  # column not in result — skip sort silently

        def sort_key(row: list[str]) -> float | str:
            val = row[col_idx] if col_idx < len(row) else ""
            try:
                return float(val)
            except ValueError:
                return val

        result = Table(columns=list(table.columns))
        result.rows = sorted(table.rows, key=sort_key)
        return result
