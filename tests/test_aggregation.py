"""Tests for aggregation: SUM, AVG, COUNT, MIN, MAX — with and without GROUP BY."""
import pytest
from src.pipeline import execute_pipeline
from models.ast_nodes import AggregateExpr, SelectNode
from src.lexer.lexer import Lexer
from src.parser.parser import Parser

DATA_DIR = "data/"


def run(query: str):
    return execute_pipeline(query, DATA_DIR)


# ---------------------------------------------------------------------------
# Lexer: aggregate keywords
# ---------------------------------------------------------------------------

def test_lexer_recognizes_aggregate_keywords():
    from models.tokens import TokenType
    tokens = Lexer("SELECT SUM AVG COUNT MIN MAX").tokenize()
    types = [t.type for t in tokens if t.type not in (TokenType.SELECT, TokenType.EOF)]
    assert types == [TokenType.SUM, TokenType.AVG, TokenType.COUNT, TokenType.MIN, TokenType.MAX]


# ---------------------------------------------------------------------------
# Parser: aggregate expressions
# ---------------------------------------------------------------------------

def test_parser_sum():
    tokens = Lexer("SELECT SUM(salary) FROM employees").tokenize()
    ast = Parser(tokens).parse()
    assert isinstance(ast, SelectNode)
    assert len(ast.aggregates) == 1
    assert ast.aggregates[0] == AggregateExpr(func="SUM", column="salary")


def test_parser_count_star():
    tokens = Lexer("SELECT COUNT(*) FROM users").tokenize()
    ast = Parser(tokens).parse()
    assert ast.aggregates[0] == AggregateExpr(func="COUNT", column="*")


def test_parser_multiple_aggregates():
    tokens = Lexer("SELECT SUM(salary), AVG(salary), COUNT(*) FROM employees").tokenize()
    ast = Parser(tokens).parse()
    assert len(ast.aggregates) == 3
    funcs = [a.func for a in ast.aggregates]
    assert funcs == ["SUM", "AVG", "COUNT"]


def test_parser_aggregate_with_plain_column():
    tokens = Lexer("SELECT department, SUM(salary) FROM employees GROUP BY department").tokenize()
    ast = Parser(tokens).parse()
    assert ast.columns == ["department"]
    assert ast.aggregates[0].func == "SUM"


# ---------------------------------------------------------------------------
# End-to-end: aggregate over full table (no GROUP BY)
# ---------------------------------------------------------------------------

def test_count_star():
    result = run("SELECT COUNT(*) FROM employees")
    assert result.columns == ["COUNT(*)"]
    assert result.rows == [["7"]]


def test_sum_salary():
    result = run("SELECT SUM(salary) FROM employees")
    assert result.columns == ["SUM(salary)"]
    total = int(result.rows[0][0])
    assert total == 422000


def test_avg_salary():
    result = run("SELECT AVG(salary) FROM employees")
    assert result.columns == ["AVG(salary)"]
    avg = float(result.rows[0][0])
    assert abs(avg - 60285.71) < 1


def test_min_salary():
    result = run("SELECT MIN(salary) FROM employees")
    assert result.columns == ["MIN(salary)"]
    assert result.rows[0][0] == "42000"


def test_max_salary():
    result = run("SELECT MAX(salary) FROM employees")
    assert result.columns == ["MAX(salary)"]
    assert result.rows[0][0] == "90000"


def test_multiple_aggregates_no_group():
    result = run("SELECT SUM(salary), COUNT(*) FROM employees")
    assert result.columns == ["SUM(salary)", "COUNT(*)"]
    assert len(result.rows) == 1
    assert result.rows[0][0] == "422000"
    assert result.rows[0][1] == "7"


# ---------------------------------------------------------------------------
# End-to-end: aggregate with GROUP BY
# ---------------------------------------------------------------------------

def test_count_by_department():
    result = run("SELECT department, COUNT(*) FROM employees GROUP BY department")
    assert "department" in result.columns
    assert "COUNT(*)" in result.columns
    dept_col = result.columns.index("department")
    count_col = result.columns.index("COUNT(*)")
    counts = {row[dept_col]: int(row[count_col]) for row in result.rows}
    assert counts == {"Engineering": 3, "Marketing": 2, "HR": 2}


def test_sum_by_department():
    result = run("SELECT department, SUM(salary) FROM employees GROUP BY department")
    dept_col = result.columns.index("department")
    sum_col = result.columns.index("SUM(salary)")
    totals = {row[dept_col]: int(row[sum_col]) for row in result.rows}
    assert totals["Engineering"] == 230000
    assert totals["Marketing"] == 105000
    assert totals["HR"] == 87000


def test_avg_by_department():
    result = run("SELECT department, AVG(salary) FROM employees GROUP BY department")
    dept_col = result.columns.index("department")
    avg_col = result.columns.index("AVG(salary)")
    avgs = {row[dept_col]: float(row[avg_col]) for row in result.rows}
    assert abs(avgs["Engineering"] - 76666.67) < 1


def test_aggregate_with_where():
    result = run("SELECT SUM(salary) FROM employees WHERE department = Engineering")
    assert result.rows[0][0] == "230000"
