from tabulate import tabulate
from models.table import Table

_MAX_COL_WIDTH = 40


def _truncate(val: str) -> str:
    return val if len(val) <= _MAX_COL_WIDTH else val[: _MAX_COL_WIDTH - 3] + "..."


def format_result(table: Table) -> str:
    if not table.columns:
        return "(0 rows)"

    rows = [[_truncate(v) for v in row] for row in table.rows]
    rendered = tabulate(rows, headers=table.columns, tablefmt="psql")
    count = len(table.rows)
    suffix = "row" if count == 1 else "rows"
    return f"{rendered}\n({count} {suffix})"


def format_error(stage: str, message: str) -> str:
    return f"[{stage}] {message}"
