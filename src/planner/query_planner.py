from __future__ import annotations
from typing import Optional
from models.ast_nodes import (
    ASTNode, SelectNode, FromNode, WhereNode,
    OrderByNode, GroupByNode,
)
from models.plan import PlanNode, PlanType
from models.catalog import Catalog


class QueryPlanner:
    def __init__(self, root: ASTNode, catalog: Optional[Catalog] = None) -> None:
        self._root = root
        self._catalog = catalog

    def plan(self) -> list[PlanNode]:
        select_node: SelectNode | None = None
        from_node: FromNode | None = None
        where_node: WhereNode | None = None

        node = self._root
        while node is not None:
            if isinstance(node, SelectNode):
                select_node = node
            elif isinstance(node, FromNode):
                from_node = node
            elif isinstance(node, WhereNode):
                where_node = node
            node = node.child

        plan_nodes: list[PlanNode] = []

        if from_node:
            plan_nodes.append(PlanNode(type=PlanType.SCAN, table=from_node.table))

        # Emit SCAN + HASH_JOIN for each JOIN clause
        if from_node:
            for join in from_node.joins:
                plan_nodes.append(PlanNode(type=PlanType.SCAN, table=join.table))
                plan_nodes.append(PlanNode(
                    type=PlanType.HASH_JOIN,
                    join_left_col=join.left_col,
                    join_right_col=join.right_col,
                    join_table=join.table,
                ))

        if where_node and where_node.condition.left:
            plan_nodes.append(PlanNode(type=PlanType.FILTER, condition=where_node.condition))

        if from_node and from_node.order_by:
            plan_nodes.append(PlanNode(type=PlanType.SORT, column=from_node.order_by.column))

        has_aggregates = select_node is not None and bool(select_node.aggregates)
        if has_aggregates:
            group_col = from_node.group_by.column if (from_node and from_node.group_by) else ""
            plan_nodes.append(PlanNode(
                type=PlanType.AGGREGATE,
                aggregates=list(select_node.aggregates),
                group_col=group_col,
            ))
        elif from_node and from_node.group_by:
            plan_nodes.append(PlanNode(type=PlanType.GROUP, column=from_node.group_by.column))

        if select_node:
            if has_aggregates:
                # Build projection columns: group_col (if any) + aggregate output names
                proj_cols: list[str] = []
                if from_node and from_node.group_by:
                    proj_cols.append(from_node.group_by.column)
                for agg in select_node.aggregates:
                    proj_cols.append(f"{agg.func}({agg.column})")
                # Include any plain columns the user also requested
                for col in select_node.columns:
                    if col not in proj_cols:
                        proj_cols.append(col)
                plan_nodes.append(PlanNode(type=PlanType.PROJECT, columns=proj_cols))
            elif select_node.star and self._catalog and from_node:
                # SELECT * — expand using catalog (merge columns from all tables)
                cols: list[str] = []
                for schema_name in [from_node.table] + [j.table for j in from_node.joins]:
                    schema = self._catalog.get_table(schema_name)
                    if schema:
                        cols.extend(c.col_name for c in schema.columns)
                plan_nodes.append(PlanNode(type=PlanType.PROJECT, columns=cols))
            else:
                plan_nodes.append(PlanNode(type=PlanType.PROJECT, columns=select_node.columns))

        return plan_nodes
