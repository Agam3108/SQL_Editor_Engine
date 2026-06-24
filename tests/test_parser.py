import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from models.ast_nodes import SelectNode, FromNode, WhereNode, OrderByNode, GroupByNode


def parse(query):
    tokens = Lexer(query).tokenize()
    return Parser(tokens).parse()


def find_node(root, cls):
    node = root
    while node is not None:
        if isinstance(node, cls):
            return node
        node = node.child
    return None


# ── basic structure ──────────────────────────────────────────────────────────

def test_basic_select():
    root = parse("SELECT name FROM users")
    s = find_node(root, SelectNode)
    f = find_node(root, FromNode)
    assert s.columns == ["name"]
    assert f.table == "users"


def test_multiple_columns():
    root = parse("SELECT name, age, salary FROM employees")
    s = find_node(root, SelectNode)
    assert s.columns == ["name", "age", "salary"]


def test_select_star():
    root = parse("SELECT * FROM users")
    s = find_node(root, SelectNode)
    assert s.star is True
    assert s.columns == []


# ── WHERE clause ─────────────────────────────────────────────────────────────

def test_where_integer():
    root = parse("SELECT name FROM users WHERE age >= 18")
    w = find_node(root, WhereNode)
    assert w is not None
    assert w.condition.left == "age"
    assert w.condition.op == ">="
    assert w.condition.right == "18"


def test_where_string():
    root = parse("SELECT name FROM users WHERE city = 'Delhi'")
    w = find_node(root, WhereNode)
    assert w.condition.right == "Delhi"


def test_no_where_clause():
    root = parse("SELECT name FROM users")
    assert find_node(root, WhereNode) is None


# ── ORDER BY / GROUP BY ──────────────────────────────────────────────────────

def test_order_by():
    root = parse("SELECT name FROM users ORDER BY name")
    f = find_node(root, FromNode)
    assert f.order_by is not None
    assert f.order_by.column == "name"


def test_group_by():
    root = parse("SELECT department FROM employees GROUP BY department")
    f = find_node(root, FromNode)
    assert f.group_by is not None
    assert f.group_by.column == "department"


def test_order_and_group_both_preserved():
    """Regression: ORDER BY and GROUP BY no longer overwrite each other."""
    root = parse("SELECT name FROM users ORDER BY name GROUP BY name")
    f = find_node(root, FromNode)
    assert f.order_by is not None
    assert f.group_by is not None


def test_where_and_order_by():
    root = parse("SELECT name FROM users WHERE age > 20 ORDER BY name")
    assert find_node(root, WhereNode) is not None
    f = find_node(root, FromNode)
    assert f.order_by is not None
