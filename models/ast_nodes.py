from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ASTNode:
    child: Optional[ASTNode] = field(default=None, repr=False)


@dataclass
class AggregateExpr:
    func: str = ""    # "SUM", "AVG", "COUNT", "MIN", "MAX"
    column: str = ""  # column name or "*" for COUNT(*)


@dataclass
class JoinClause:
    table: str = ""
    left_col: str = ""   # column on the left (FROM) table
    right_col: str = ""  # column on the right (JOIN) table


@dataclass
class SelectNode(ASTNode):
    columns: list[str] = field(default_factory=list)
    star: bool = False
    aggregates: list[AggregateExpr] = field(default_factory=list)


@dataclass
class FromNode(ASTNode):
    table: str = ""
    order_by: Optional[OrderByNode] = field(default=None, repr=False)
    group_by: Optional[GroupByNode] = field(default=None, repr=False)
    joins: list[JoinClause] = field(default_factory=list)


@dataclass
class ConditionNode:
    left: str = ""
    op: str = ""
    right: str = ""


@dataclass
class WhereNode(ASTNode):
    condition: ConditionNode = field(default_factory=ConditionNode)


@dataclass
class OrderByNode(ASTNode):
    column: str = ""


@dataclass
class GroupByNode(ASTNode):
    column: str = ""
