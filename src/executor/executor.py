from models.plan import PlanNode, PlanType
from models.table import Table
from models.exceptions import ExecutionError
from src.executor.scan_node import ScanNode
from src.executor.filter_node import FilterNode
from src.executor.sort_node import SortNode


class Executor:
    def __init__(self, plan: list[PlanNode], data_dir: str = "data/") -> None:
        self._plan = plan
        self._data_dir = data_dir

    def execute(self) -> Table:
        result = Table()

        for node in self._plan:
            if node.type == PlanType.SCAN:
                result = ScanNode(node, self._data_dir).execute()

            elif node.type == PlanType.FILTER:
                result = FilterNode(node).execute(result)

            elif node.type == PlanType.SORT:
                result = SortNode(node).execute(result)

            elif node.type == PlanType.GROUP:
                # GROUP BY: sort by the group column (aggregation is a future feature)
                result = SortNode(node).execute(result)

            elif node.type == PlanType.PROJECT:
                result = self._project(node.columns, result)

        return result

    @staticmethod
    def _project(columns: list[str], table: Table) -> Table:
        if not columns:
            return table  # empty means SELECT * — return all columns

        projected = Table()
        indices: list[int] = []
        for col in columns:
            try:
                idx = table.columns.index(col)
                projected.columns.append(col)
                indices.append(idx)
            except ValueError:
                raise ExecutionError(f"Column '{col}' not found during projection")

        for row in table.rows:
            projected.rows.append([row[i] if i < len(row) else "" for i in indices])

        return projected
