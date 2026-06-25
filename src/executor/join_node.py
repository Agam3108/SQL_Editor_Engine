from collections import defaultdict
from models.plan import PlanNode
from models.table import Table
from models.exceptions import ExecutionError


class HashJoinNode:
    def __init__(self, plan_node: PlanNode) -> None:
        self._left_col = plan_node.join_left_col
        self._right_col = plan_node.join_right_col

    def execute(self, left: Table, right: Table) -> Table:
        try:
            left_idx = left.columns.index(self._left_col)
        except ValueError:
            raise ExecutionError(
                f"Join column '{self._left_col}' not found in left table (columns: {left.columns})"
            )
        try:
            right_idx = right.columns.index(self._right_col)
        except ValueError:
            raise ExecutionError(
                f"Join column '{self._right_col}' not found in right table (columns: {right.columns})"
            )

        # Build phase: hash right table on right_col
        hash_map: dict[str, list[list[str]]] = defaultdict(list)
        for row in right.rows:
            hash_map[row[right_idx]].append(row)

        # Resolve column name collisions by prefixing duplicates
        combined_cols = _merge_columns(left.columns, right.columns)

        out = Table()
        out.columns = combined_cols

        # Probe phase: for each left row find matching right rows
        for left_row in left.rows:
            key = left_row[left_idx]
            for right_row in hash_map.get(key, []):
                out.rows.append(left_row + right_row)

        return out


def _merge_columns(left_cols: list[str], right_cols: list[str]) -> list[str]:
    """Combine column lists, suffixing duplicates with _1 / _2."""
    left_set = set(left_cols)
    result = list(left_cols)
    for col in right_cols:
        if col in left_set:
            result.append(col + "_1")
        else:
            result.append(col)
    return result
