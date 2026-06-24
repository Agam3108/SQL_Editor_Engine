from models.plan import PlanNode
from models.table import Table
from models.exceptions import ExecutionError


class FilterNode:
    def __init__(self, plan: PlanNode) -> None:
        self._plan = plan

    def execute(self, table: Table) -> Table:
        cond = self._plan.condition
        if cond is None:
            return table

        try:
            col_idx = table.columns.index(cond.left)
        except ValueError:
            raise ExecutionError(f"Column '{cond.left}' not found for WHERE filter")

        result = Table(columns=list(table.columns))
        op = cond.op
        right_raw = cond.right

        for row in table.rows:
            val = row[col_idx] if col_idx < len(row) else ""
            if self._compare(val, op, right_raw):
                result.rows.append(row)

        return result

    @staticmethod
    def _compare(val: str, op: str, right: str) -> bool:
        try:
            lhs = float(val)
            rhs = float(right)
            return {
                ">":  lhs > rhs,
                "<":  lhs < rhs,
                ">=": lhs >= rhs,
                "<=": lhs <= rhs,
                "=":  lhs == rhs,
                "!=": lhs != rhs,
            }.get(op, False)
        except ValueError:
            if op == "=":
                return val == right
            if op == "!=":
                return val != right
            return False
