import os
from models.plan import PlanNode
from models.table import Table
from src.storage.csv_reader import CSVReader


class ScanNode:
    def __init__(self, plan: PlanNode, data_dir: str = "data/") -> None:
        self._plan = plan
        self._data_dir = data_dir

    def execute(self) -> Table:
        from models.exceptions import ExecutionError
        path = os.path.join(self._data_dir, f"{self._plan.table}.csv")
        if not os.path.exists(path):
            raise ExecutionError(
                f"table '{self._plan.table}' not found — "
                f"no file at '{path}'"
            )
        reader = CSVReader(path)
        cols = self._plan.columns if self._plan.columns else None
        return reader.read(columns=cols)
