from models.tokens import Token, TokenType
from models.ast_nodes import (
    ASTNode, SelectNode, FromNode, WhereNode,
    OrderByNode, GroupByNode, ConditionNode,
    AggregateExpr, JoinClause,
)
from models.exceptions import ParseError
from typing import Optional

_AGGREGATE_TOKENS = {
    TokenType.SUM, TokenType.AVG, TokenType.COUNT, TokenType.MIN, TokenType.MAX,
}

_STOP_TOKENS = {
    TokenType.WHERE, TokenType.ORDER, TokenType.GROUP,
    TokenType.EOF, TokenType.SEMICOLON,
}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def peek(self) -> Token:
        return self._tokens[self._pos]

    def consume(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> ASTNode:
        select_node = SelectNode()
        from_node: Optional[FromNode] = None
        where_node: Optional[WhereNode] = None
        order_node: Optional[OrderByNode] = None
        group_node: Optional[GroupByNode] = None

        while self.peek().type != TokenType.EOF:
            t = self.peek().type

            if t == TokenType.SELECT:
                self.consume()
                if self.peek().type == TokenType.STAR:
                    self.consume()
                    select_node.star = True
                else:
                    self._parse_select_list(select_node)

            elif t == TokenType.FROM:
                self.consume()
                from_node = FromNode()
                # Read the primary table name
                while self.peek().type not in _STOP_TOKENS | {TokenType.INNER, TokenType.JOIN}:
                    tok = self.consume()
                    if tok.type == TokenType.IDENTIFIER:
                        from_node.table = tok.value
                # Parse any JOIN clauses
                while self.peek().type in (TokenType.INNER, TokenType.JOIN):
                    join = self._parse_join_clause()
                    from_node.joins.append(join)

            elif t == TokenType.WHERE:
                self.consume()
                left = self._consume_col_ref()
                op = self.consume().value
                right = self.consume().value
                where_node = WhereNode(condition=ConditionNode(left=left, op=op, right=right))

            elif t == TokenType.ORDER:
                self.consume()
                if self.peek().type == TokenType.BY:
                    self.consume()
                col = self.consume()
                if col.type not in (TokenType.IDENTIFIER, TokenType.EOF):
                    raise ParseError(f"Expected column name after ORDER BY, got '{col.value}'")
                order_node = OrderByNode(column=col.value)

            elif t == TokenType.GROUP:
                self.consume()
                if self.peek().type == TokenType.BY:
                    self.consume()
                col = self.consume()
                if col.type not in (TokenType.IDENTIFIER, TokenType.EOF):
                    raise ParseError(f"Expected column name after GROUP BY, got '{col.value}'")
                group_node = GroupByNode(column=col.value)

            else:
                self.consume()  # skip unrecognized tokens

        if from_node is None:
            from_node = FromNode()

        # Attach ORDER BY / GROUP BY as separate attributes (fixes C++ overwrite bug)
        from_node.order_by = order_node
        from_node.group_by = group_node

        # Build linked chain: SelectNode → [WhereNode →] FromNode
        if where_node is not None:
            select_node.child = where_node
            where_node.child = from_node
        else:
            select_node.child = from_node

        return select_node

    def _parse_select_list(self, select_node: SelectNode) -> None:
        """Parse column list and aggregate expressions after SELECT."""
        stop = _STOP_TOKENS | {TokenType.FROM}
        while self.peek().type not in stop:
            tok = self.peek()
            if tok.type in _AGGREGATE_TOKENS:
                agg = self._parse_aggregate()
                select_node.aggregates.append(agg)
            elif tok.type == TokenType.IDENTIFIER:
                self.consume()
                select_node.columns.append(tok.value)
            else:
                self.consume()  # skip commas and other punctuation

    def _parse_aggregate(self) -> AggregateExpr:
        """Parse SUM(col), AVG(col), COUNT(*), MIN(col), MAX(col)."""
        func_tok = self.consume()
        func = func_tok.value.upper()
        if self.peek().type != TokenType.LPAREN:
            raise ParseError(f"Expected '(' after {func}, got '{self.peek().value}'")
        self.consume()  # (
        if self.peek().type == TokenType.STAR:
            col = "*"
            self.consume()
        elif self.peek().type == TokenType.IDENTIFIER:
            col = self.consume().value
        else:
            raise ParseError(f"Expected column name or * inside {func}(), got '{self.peek().value}'")
        if self.peek().type != TokenType.RPAREN:
            raise ParseError(f"Expected ')' after {func}({col}), got '{self.peek().value}'")
        self.consume()  # )
        return AggregateExpr(func=func, column=col)

    def _parse_join_clause(self) -> JoinClause:
        """Parse [INNER] JOIN table ON left_col = right_col."""
        if self.peek().type == TokenType.INNER:
            self.consume()  # INNER
        if self.peek().type != TokenType.JOIN:
            raise ParseError(f"Expected JOIN, got '{self.peek().value}'")
        self.consume()  # JOIN

        if self.peek().type != TokenType.IDENTIFIER:
            raise ParseError(f"Expected table name after JOIN, got '{self.peek().value}'")
        join_table = self.consume().value

        if self.peek().type != TokenType.ON:
            raise ParseError(f"Expected ON after JOIN {join_table}, got '{self.peek().value}'")
        self.consume()  # ON

        left_col = self._consume_col_ref()

        if self.peek().type != TokenType.EQ:
            raise ParseError(f"Expected '=' in JOIN condition, got '{self.peek().value}'")
        self.consume()  # =

        right_col = self._consume_col_ref()

        return JoinClause(table=join_table, left_col=left_col, right_col=right_col)

    def _consume_col_ref(self) -> str:
        """Consume a column reference, stripping optional table prefix (table.col → col)."""
        if self.peek().type != TokenType.IDENTIFIER:
            return self.consume().value
        first = self.consume().value
        if self.peek().type == TokenType.DOT:
            self.consume()  # .
            col = self.consume().value
            return col  # strip table prefix
        return first
