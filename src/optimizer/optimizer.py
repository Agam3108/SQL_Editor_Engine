from models.plan import PlanNode, PlanType


class Optimizer:
    def __init__(self, plan: list[PlanNode]) -> None:
        self._plan = [PlanNode(type=n.type, table=n.table, column=n.column,
                               condition=n.condition, columns=list(n.columns))
                      for n in plan]

    def optimize(self) -> list[PlanNode]:
        self._projection_pruning()
        self._predicate_pushdown()
        return self._plan

    def _projection_pruning(self) -> None:
        """Push the PROJECT column list into the SCAN node so it reads only needed columns.

        Also includes any columns referenced in FILTER/SORT/GROUP nodes so downstream
        operators can find them even though they're not in the final projection.
        """
        projected: list[str] = []
        for node in self._plan:
            if node.type == PlanType.PROJECT:
                projected = node.columns
                break
        if not projected:
            return

        # Collect extra columns needed by non-PROJECT operators
        extra: list[str] = []
        for node in self._plan:
            if node.type == PlanType.FILTER and node.condition:
                col = node.condition.left
                if col and col not in projected and col not in extra:
                    extra.append(col)
            elif node.type in (PlanType.SORT, PlanType.GROUP):
                col = node.column
                if col and col not in projected and col not in extra:
                    extra.append(col)

        for node in self._plan:
            if node.type == PlanType.SCAN:
                node.columns = list(projected) + extra
                break

    def _predicate_pushdown(self) -> None:
        """Move FILTER before SORT/GROUP when possible (safe — filter is row-independent)."""
        scan_idx = next((i for i, n in enumerate(self._plan) if n.type == PlanType.SCAN), -1)
        filter_idx = next((i for i, n in enumerate(self._plan) if n.type == PlanType.FILTER), -1)
        if filter_idx == -1 or scan_idx == -1:
            return
        # If FILTER is not immediately after SCAN, move it there
        target = scan_idx + 1
        if filter_idx != target:
            node = self._plan.pop(filter_idx)
            self._plan.insert(target, node)
