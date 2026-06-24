from models.ast_nodes import ASTNode, SelectNode, FromNode, WhereNode
from models.catalog import Catalog, TableSchema
from models.exceptions import SemanticError
from typing import Optional


class SemanticAnalyzer:
    def __init__(self, root: ASTNode, catalog: Catalog) -> None:
        self._root = root
        self._catalog = catalog

    def analyze(self) -> None:
        table = self._resolve_table()
        self._validate_select_columns(table)
        self._validate_where_column(table)

    def _resolve_table(self) -> TableSchema:
        node = self._root
        while node is not None:
            if isinstance(node, FromNode):
                table = self._catalog.get_table(node.table)
                if table is None:
                    raise SemanticError(f"table '{node.table}' does not exist")
                return table
            node = node.child
        raise SemanticError("No FROM clause found in query")

    def _validate_select_columns(self, table: TableSchema) -> None:
        node = self._root
        while node is not None:
            if isinstance(node, SelectNode):
                if node.star:
                    return  # SELECT * is always valid
                known = {c.col_name for c in table.columns}
                for col in node.columns:
                    if col not in known:
                        raise SemanticError(
                            f"column '{col}' does not exist in table '{table.table_name}'"
                        )
            node = node.child

    def _validate_where_column(self, table: TableSchema) -> None:
        node = self._root
        while node is not None:
            if isinstance(node, WhereNode):
                col = node.condition.left
                if not col:
                    node = node.child
                    continue
                known = {c.col_name for c in table.columns}
                if col not in known:
                    raise SemanticError(
                        f"column '{col}' does not exist in table '{table.table_name}'"
                    )
            node = node.child
