from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
from models.ast_nodes import ConditionNode


class PlanType(Enum):
    SCAN = auto()
    FILTER = auto()
    SORT = auto()
    GROUP = auto()
    PROJECT = auto()


@dataclass
class PlanNode:
    type: PlanType
    table: str = ""
    column: str = ""
    condition: Optional[ConditionNode] = None
    columns: list[str] = field(default_factory=list)
