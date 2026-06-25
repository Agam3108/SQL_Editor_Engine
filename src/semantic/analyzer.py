from models.ast_nodes import ASTNode, SelectNode, FromNode, WhereNode
from models.catalog import Catalog, TableSchema, ColumnSchema
from models.exceptions import SemanticError
from typing import Optional


class SemanticAnalyzer:
    def __init__(self, root: ASTNode, catalog: Catalog) -> None:
        self._root = root
        self._catalog = catalog

    def analyze(self) -> None:
        from_node = self._find_from_node()
        merged = self._build_merged_schema(from_node)
        self._validate_join_columns(from_node)
        self._validate_select_columns(merged)
        self._validate_where_column(merged)
        self._validate_aggregate_columns(merged)
        self._validate_group_by_column(merged, from_node)

    def _find_from_node(self) -> Optional[FromNode]:
        node = self._root
        while node is not None:
            if isinstance(node, FromNode):
                return node
            node = node.child
        return None

    def _build_merged_schema(self, from_node: Optional[FromNode]) -> TableSchema:
        """Return a pseudo-schema merging columns from all tables in the query."""
        if from_node is None:
            raise SemanticError("No FROM clause found in query")
        table = self._catalog.get_table(from_node.table)
        if table is None:
            raise SemanticError(f"table '{from_node.table}' does not exist")
        all_cols: list[ColumnSchema] = list(table.columns)
        for join in from_node.joins:
            jt = self._catalog.get_table(join.table)
            if jt is None:
                raise SemanticError(f"table '{join.table}' does not exist")
            all_cols.extend(jt.columns)
        return TableSchema(table_name="<merged>", columns=all_cols)

    def _validate_join_columns(self, from_node: Optional[FromNode]) -> None:
        if from_node is None:
            return
        left_schema = self._catalog.get_table(from_node.table)
        if left_schema is None:
            return
        left_cols = {c.col_name for c in left_schema.columns}
        for join in from_node.joins:
            right_schema = self._catalog.get_table(join.table)
            if right_schema is None:
                raise SemanticError(f"table '{join.table}' does not exist")
            right_cols = {c.col_name for c in right_schema.columns}
            if join.left_col and join.left_col not in left_cols:
                raise SemanticError(
                    f"join column '{join.left_col}' does not exist in table '{from_node.table}'"
                )
            if join.right_col and join.right_col not in right_cols:
                raise SemanticError(
                    f"join column '{join.right_col}' does not exist in table '{join.table}'"
                )

    def _validate_select_columns(self, merged: TableSchema) -> None:
        node = self._root
        while node is not None:
            if isinstance(node, SelectNode):
                if node.star:
                    return
                known = {c.col_name for c in merged.columns}
                for col in node.columns:
                    if col not in known:
                        raise SemanticError(
                            f"column '{col}' does not exist in table '{merged.table_name}'"
                        )
            node = node.child

    def _validate_where_column(self, merged: TableSchema) -> None:
        node = self._root
        while node is not None:
            if isinstance(node, WhereNode):
                col = node.condition.left
                if not col:
                    node = node.child
                    continue
                known = {c.col_name for c in merged.columns}
                if col not in known:
                    raise SemanticError(
                        f"column '{col}' does not exist in table '{merged.table_name}'"
                    )
            node = node.child

    def _validate_aggregate_columns(self, merged: TableSchema) -> None:
        node = self._root
        while node is not None:
            if isinstance(node, SelectNode):
                known = {c.col_name for c in merged.columns}
                for agg in node.aggregates:
                    if agg.column != "*" and agg.column not in known:
                        raise SemanticError(
                            f"column '{agg.column}' does not exist (used in {agg.func})"
                        )
            node = node.child

    def _validate_group_by_column(self, merged: TableSchema, from_node: Optional[FromNode]) -> None:
        if from_node is None or from_node.group_by is None:
            return
        col = from_node.group_by.column
        known = {c.col_name for c in merged.columns}
        if col and col not in known:
            raise SemanticError(f"GROUP BY column '{col}' does not exist")
