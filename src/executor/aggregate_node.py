from collections import defaultdict
from models.plan import PlanNode
from models.table import Table
from models.ast_nodes import AggregateExpr
from models.exceptions import ExecutionError


def _compute_aggregate(func: str, values: list[str]) -> str:
    if func == "COUNT":
        return str(len(values))
    nums: list[float] = []
    for v in values:
        try:
            nums.append(float(v))
        except ValueError:
            raise ExecutionError(f"Non-numeric value '{v}' in {func} aggregate")
    if not nums:
        return "0"
    if func == "SUM":
        result = sum(nums)
    elif func == "AVG":
        result = sum(nums) / len(nums)
    elif func == "MIN":
        result = min(nums)
    elif func == "MAX":
        result = max(nums)
    else:
        raise ExecutionError(f"Unknown aggregate function: {func}")
    # Return int string if no fractional part
    return str(int(result)) if result == int(result) else str(result)


class AggregateNode:
    def __init__(self, plan_node: PlanNode) -> None:
        self._aggregates: list[AggregateExpr] = plan_node.aggregates
        self._group_col: str = plan_node.group_col

    def execute(self, table: Table) -> Table:
        if self._group_col:
            return self._grouped_aggregate(table)
        return self._full_aggregate(table)

    def _full_aggregate(self, table: Table) -> Table:
        """Reduce entire table to a single row of aggregate values."""
        out = Table()
        for agg in self._aggregates:
            out.columns.append(f"{agg.func}({agg.column})")

        row: list[str] = []
        for agg in self._aggregates:
            if agg.column == "*":
                values = [str(i) for i in range(len(table.rows))]  # any non-empty list
            else:
                try:
                    idx = table.columns.index(agg.column)
                except ValueError:
                    raise ExecutionError(f"Column '{agg.column}' not found for aggregate {agg.func}")
                values = [r[idx] for r in table.rows]
            row.append(_compute_aggregate(agg.func, values))
        out.rows.append(row)
        return out

    def _grouped_aggregate(self, table: Table) -> Table:
        """Group rows by group_col and emit one aggregate row per group."""
        try:
            group_idx = table.columns.index(self._group_col)
        except ValueError:
            raise ExecutionError(f"GROUP BY column '{self._group_col}' not found")

        # Collect rows per group, preserving insertion order
        groups: dict[str, list[list[str]]] = defaultdict(list)
        for row in table.rows:
            key = row[group_idx]
            groups[key].append(row)

        out = Table()
        out.columns = [self._group_col] + [f"{a.func}({a.column})" for a in self._aggregates]

        for group_val, rows in groups.items():
            result_row: list[str] = [group_val]
            for agg in self._aggregates:
                if agg.column == "*":
                    values = [str(i) for i in range(len(rows))]
                else:
                    try:
                        idx = table.columns.index(agg.column)
                    except ValueError:
                        raise ExecutionError(f"Column '{agg.column}' not found for aggregate {agg.func}")
                    values = [r[idx] for r in rows]
                result_row.append(_compute_aggregate(agg.func, values))
            out.rows.append(result_row)

        return out
