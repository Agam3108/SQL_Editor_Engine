from models.plan import PlanNode, PlanType
from models.ast_nodes import AggregateExpr


class Optimizer:
    def __init__(self, plan: list[PlanNode]) -> None:
        self._plan = [PlanNode(
            type=n.type, table=n.table, column=n.column,
            condition=n.condition, columns=list(n.columns),
            aggregates=list(n.aggregates), group_col=n.group_col,
            join_left_col=n.join_left_col, join_right_col=n.join_right_col,
            join_table=n.join_table,
        ) for n in plan]

    def optimize(self) -> list[PlanNode]:
        self._projection_pruning()
        self._predicate_pushdown()
        return self._plan

    def _projection_pruning(self) -> None:
        """Push the PROJECT column list into each SCAN node so it reads only needed columns.

        Includes columns referenced in FILTER/SORT/GROUP/AGGREGATE/HASH_JOIN so downstream
        operators can find them even if not in the final projection.
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
            elif node.type == PlanType.AGGREGATE:
                if node.group_col and node.group_col not in projected and node.group_col not in extra:
                    extra.append(node.group_col)
                for agg in node.aggregates:
                    if agg.column != "*" and agg.column not in projected and agg.column not in extra:
                        extra.append(agg.column)
            elif node.type == PlanType.HASH_JOIN:
                for col in (node.join_left_col, node.join_right_col):
                    if col and col not in projected and col not in extra:
                        extra.append(col)

        # Apply to all SCAN nodes (each table may need different subsets, but for simplicity
        # give every SCAN the full set — the CSV reader ignores columns it doesn't have)
        for node in self._plan:
            if node.type == PlanType.SCAN:
                node.columns = list(projected) + extra

    def _predicate_pushdown(self) -> None:
        """Move FILTER immediately after the last SCAN/HASH_JOIN when possible."""
        filter_idx = next((i for i, n in enumerate(self._plan) if n.type == PlanType.FILTER), -1)
        if filter_idx == -1:
            return
        # Find the last SCAN or HASH_JOIN before the filter
        last_data_node = -1
        for i, n in enumerate(self._plan):
            if n.type in (PlanType.SCAN, PlanType.HASH_JOIN) and i < filter_idx:
                last_data_node = i
        if last_data_node == -1:
            return
        target = last_data_node + 1
        if filter_idx != target:
            node = self._plan.pop(filter_idx)
            self._plan.insert(target, node)
