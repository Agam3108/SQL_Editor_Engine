from models.ast_nodes import (
    ASTNode, SelectNode, FromNode, WhereNode,
    OrderByNode, GroupByNode,
)
from models.plan import PlanNode, PlanType
from models.catalog import Catalog


class QueryPlanner:
    def __init__(self, root: ASTNode, catalog: Catalog | None = None) -> None:
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

        if where_node and where_node.condition.left:
            plan_nodes.append(PlanNode(type=PlanType.FILTER, condition=where_node.condition))

        if from_node and from_node.order_by:
            plan_nodes.append(PlanNode(type=PlanType.SORT, column=from_node.order_by.column))

        if from_node and from_node.group_by:
            plan_nodes.append(PlanNode(type=PlanType.GROUP, column=from_node.group_by.column))

        if select_node:
            # Expand SELECT * to all columns using catalog
            if select_node.star and self._catalog and from_node:
                schema = self._catalog.get_table(from_node.table)
                cols = [c.col_name for c in schema.columns] if schema else []
            else:
                cols = select_node.columns
            plan_nodes.append(PlanNode(type=PlanType.PROJECT, columns=cols))

        return plan_nodes
