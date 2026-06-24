import pytest
from src.lexer.lexer import Lexer
from models.tokens import TokenType
from models.exceptions import LexerError


def tokenize(query):
    return Lexer(query).tokenize()


def types(query):
    return [t.type for t in tokenize(query)]


def values(query):
    return [t.value for t in tokenize(query)]


# ── keyword recognition ──────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected", [
    ("SELECT name FROM users",
     [TokenType.SELECT, TokenType.IDENTIFIER, TokenType.FROM, TokenType.IDENTIFIER, TokenType.EOF]),
    ("select name from users",          # fixed: case-insensitive keywords
     [TokenType.SELECT, TokenType.IDENTIFIER, TokenType.FROM, TokenType.IDENTIFIER, TokenType.EOF]),
    ("SELECT * FROM users",
     [TokenType.SELECT, TokenType.STAR, TokenType.FROM, TokenType.IDENTIFIER, TokenType.EOF]),
])
def test_keywords(query, expected):
    assert types(query) == expected


# ── operators ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("op,expected_type", [
    (">",  TokenType.GT),
    ("<",  TokenType.LT),
    (">=", TokenType.GTE),
    ("<=", TokenType.LTE),
    ("=",  TokenType.EQ),
    ("!=", TokenType.NEQ),
])
def test_operators(op, expected_type):
    tokens = tokenize(f"SELECT x FROM t WHERE age {op} 18")
    op_token = next(t for t in tokens if t.type == expected_type)
    assert op_token.value == op


# ── literals ─────────────────────────────────────────────────────────────────

def test_integer_literal():
    toks = tokenize("WHERE age > 20")
    assert any(t.type == TokenType.INTEGER and t.value == "20" for t in toks)


def test_float_literal():
    toks = tokenize("WHERE salary > 50000.50")
    assert any(t.type == TokenType.FLOAT and t.value == "50000.50" for t in toks)


def test_string_literal():
    toks = tokenize("WHERE city = 'Delhi'")
    assert any(t.type == TokenType.STRING and t.value == "Delhi" for t in toks)


# ── identifiers ──────────────────────────────────────────────────────────────

def test_identifier_with_digit():
    toks = tokenize("SELECT table1 FROM db2")
    idents = [t.value for t in toks if t.type == TokenType.IDENTIFIER]
    assert "table1" in idents and "db2" in idents


# ── bug fixes ────────────────────────────────────────────────────────────────

def test_star_token():
    toks = tokenize("SELECT * FROM users")
    assert any(t.type == TokenType.STAR for t in toks)


def test_case_insensitive_select():
    toks = tokenize("select name from users")
    assert toks[0].type == TokenType.SELECT
    assert toks[2].type == TokenType.FROM


def test_unterminated_string_raises():
    with pytest.raises(LexerError, match="Unterminated"):
        tokenize("SELECT name FROM users WHERE city = 'Delhi")


def test_eof_always_appended():
    toks = tokenize("SELECT name FROM users")
    assert toks[-1].type == TokenType.EOF
