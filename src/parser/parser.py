from models.tokens import Token, TokenType
from models.ast_nodes import (
    ASTNode, SelectNode, FromNode, WhereNode,
    OrderByNode, GroupByNode, ConditionNode,
)
from models.exceptions import ParseError
from typing import Optional

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
                    while self.peek().type not in _STOP_TOKENS | {TokenType.FROM}:
                        tok = self.consume()
                        if tok.type == TokenType.IDENTIFIER:
                            select_node.columns.append(tok.value)
                        # skip commas

            elif t == TokenType.FROM:
                self.consume()
                from_node = FromNode()
                while self.peek().type not in _STOP_TOKENS:
                    tok = self.consume()
                    if tok.type == TokenType.IDENTIFIER:
                        from_node.table = tok.value

            elif t == TokenType.WHERE:
                self.consume()
                left = self.consume().value
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
