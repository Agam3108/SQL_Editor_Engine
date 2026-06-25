from models.plan import PlanNode, PlanType
from models.table import Table
from models.exceptions import ExecutionError
from src.executor.scan_node import ScanNode
from src.executor.filter_node import FilterNode
from src.executor.sort_node import SortNode
from src.executor.aggregate_node import AggregateNode
from src.executor.join_node import HashJoinNode


class Executor:
    def __init__(self, plan: list[PlanNode], data_dir: str = "data/") -> None:
        self._plan = plan
        self._data_dir = data_dir

    def execute(self) -> Table:
        result = Table()
        # Buffer for multi-table queries: each SCAN appends here; HASH_JOIN reads from it
        scan_buffer: list[Table] = []

        for node in self._plan:
            if node.type == PlanType.SCAN:
                scanned = ScanNode(node, self._data_dir).execute()
                scan_buffer.append(scanned)
                result = scanned

            elif node.type == PlanType.HASH_JOIN:
                if len(scan_buffer) < 2:
                    raise ExecutionError("HASH_JOIN requires two scanned tables")
                result = HashJoinNode(node).execute(scan_buffer[-2], scan_buffer[-1])
                # Replace buffer contents with the joined table so subsequent JOINs chain
                scan_buffer = [result]

            elif node.type == PlanType.FILTER:
                result = FilterNode(node).execute(result)

            elif node.type == PlanType.SORT:
                result = SortNode(node).execute(result)

            elif node.type == PlanType.GROUP:
                result = SortNode(node).execute(result)

            elif node.type == PlanType.AGGREGATE:
                result = AggregateNode(node).execute(result)

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
