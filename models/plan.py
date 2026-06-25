from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
from models.ast_nodes import ConditionNode, AggregateExpr


class PlanType(Enum):
    SCAN = auto()
    FILTER = auto()
    SORT = auto()
    GROUP = auto()
    PROJECT = auto()
    AGGREGATE = auto()
    HASH_JOIN = auto()


@dataclass
class PlanNode:
    type: PlanType
    table: str = ""
    column: str = ""
    condition: Optional[ConditionNode] = None
    columns: list[str] = field(default_factory=list)
    # AGGREGATE fields
    aggregates: list[AggregateExpr] = field(default_factory=list)
    group_col: str = ""
    # HASH_JOIN fields
    join_left_col: str = ""
    join_right_col: str = ""
    join_table: str = ""
