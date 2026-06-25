"""Tests for INNER JOIN using hash join."""
import pytest
from src.pipeline import execute_pipeline
from models.ast_nodes import JoinClause, SelectNode, FromNode
from src.lexer.lexer import Lexer
from src.parser.parser import Parser

DATA_DIR = "data/"


def run(query: str):
    return execute_pipeline(query, DATA_DIR)


# ---------------------------------------------------------------------------
# Lexer: join keywords
# ---------------------------------------------------------------------------

def test_lexer_join_keywords():
    from models.tokens import TokenType
    tokens = Lexer("INNER JOIN ON").tokenize()
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert types == [TokenType.INNER, TokenType.JOIN, TokenType.ON]


def test_lexer_dot():
    from models.tokens import TokenType
    tokens = Lexer("users.dept_id").tokenize()
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert types == [TokenType.IDENTIFIER, TokenType.DOT, TokenType.IDENTIFIER]


# ---------------------------------------------------------------------------
# Parser: JOIN clause
# ---------------------------------------------------------------------------

def test_parser_inner_join():
    tokens = Lexer(
        "SELECT name FROM employees INNER JOIN departments ON dept_id = id"
    ).tokenize()
    ast = Parser(tokens).parse()
    assert isinstance(ast, SelectNode)
    # Drill to FromNode
    node = ast.child
    while node and not isinstance(node, FromNode):
        node = node.child
    assert node is not None
    assert node.table == "employees"
    assert len(node.joins) == 1
    assert node.joins[0] == JoinClause(table="departments", left_col="dept_id", right_col="id")


def test_parser_join_without_inner_keyword():
    tokens = Lexer(
        "SELECT name FROM employees JOIN departments ON dept_id = id"
    ).tokenize()
    ast = Parser(tokens).parse()
    node = ast.child
    while node and not isinstance(node, FromNode):
        node = node.child
    assert len(node.joins) == 1
    assert node.joins[0].table == "departments"


def test_parser_join_strips_table_prefix():
    tokens = Lexer(
        "SELECT name FROM employees JOIN departments ON employees.dept_id = departments.id"
    ).tokenize()
    ast = Parser(tokens).parse()
    node = ast.child
    while node and not isinstance(node, FromNode):
        node = node.child
    j = node.joins[0]
    assert j.left_col == "dept_id"
    assert j.right_col == "id"


# ---------------------------------------------------------------------------
# End-to-end: hash join execution
# ---------------------------------------------------------------------------

def test_join_returns_combined_columns():
    result = run("SELECT name FROM employees INNER JOIN departments ON dept_id = id")
    assert "name" in result.columns


def test_join_row_count():
    """Every employee has a matching department — expect 7 rows."""
    result = run("SELECT * FROM employees INNER JOIN departments ON dept_id = id")
    assert len(result.rows) == 7


def test_join_correct_pairing():
    """Engineering employees should be paired with the Engineering department."""
    result = run("SELECT name, department FROM employees INNER JOIN departments ON dept_id = id")
    name_col = result.columns.index("name")
    dept_col = result.columns.index("department")
    eng_employees = {row[name_col] for row in result.rows if row[dept_col] == "Engineering"}
    assert eng_employees == {"Alice", "Charlie", "Eve"}


def test_join_no_match_returns_empty():
    """A join on a non-matching key produces no rows."""
    result = run("SELECT name FROM employees INNER JOIN departments ON name = id")
    assert result.rows == []


def test_join_with_where():
    result = run(
        "SELECT name, salary FROM employees INNER JOIN departments ON dept_id = id "
        "WHERE salary > 55000"
    )
    name_col = result.columns.index("name")
    names = {row[name_col] for row in result.rows}
    assert names == {"Alice", "Charlie", "Eve"}


def test_join_budget_column_accessible():
    """departments.budget should be available after join."""
    result = run("SELECT name, budget FROM employees INNER JOIN departments ON dept_id = id")
    assert "budget" in result.columns
    budget_col = result.columns.index("budget")
    # All Engineering employees should have budget 500000
    name_col = result.columns.index("name")
    for row in result.rows:
        if row[name_col] == "Alice":
            assert row[budget_col] == "500000"
            break
