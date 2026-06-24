from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # Keywords
    SELECT = auto()
    FROM = auto()
    WHERE = auto()
    ORDER = auto()
    BY = auto()
    GROUP = auto()

    # Identifiers
    IDENTIFIER = auto()
    STAR = auto()

    # Operators
    GT = auto()
    LT = auto()
    EQ = auto()
    NEQ = auto()
    GTE = auto()
    LTE = auto()

    # Literals
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()

    # Symbols
    COMMA = auto()
    SEMICOLON = auto()
    LPAREN = auto()
    RPAREN = auto()

    # Special
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
