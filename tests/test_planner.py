import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.catalog.catalog import build_catalog
from src.planner.query_planner import QueryPlanner
from models.plan import PlanType


DATA_DIR = "data/"


def plan(query, data_dir=DATA_DIR):
    tokens = Lexer(query).tokenize()
    ast = Parser(tokens).parse()
    from models.ast_nodes import FromNode
    node = ast
    table_name = ""
    while node:
        if isinstance(node, FromNode):
            table_name = node.table
            break
        node = node.child
    catalog = build_catalog(table_name, data_dir) if table_name else None
    return QueryPlanner(ast, catalog).plan()


def plan_types(query):
    return [n.type for n in plan(query)]


def test_basic_plan_order():
    types = plan_types("SELECT name FROM users")
    assert types == [PlanType.SCAN, PlanType.PROJECT]


def test_plan_with_where():
    types = plan_types("SELECT name FROM users WHERE age > 18")
    assert types == [PlanType.SCAN, PlanType.FILTER, PlanType.PROJECT]


def test_plan_with_order_by():
    types = plan_types("SELECT name FROM users ORDER BY name")
    assert PlanType.SORT in types
    assert types.index(PlanType.SCAN) < types.index(PlanType.SORT)


def test_plan_with_group_by():
    types = plan_types("SELECT department FROM employees GROUP BY department")
    assert PlanType.GROUP in types


def test_scan_has_table():
    nodes = plan("SELECT name FROM users")
    scan = next(n for n in nodes if n.type == PlanType.SCAN)
    assert scan.table == "users"


def test_filter_has_condition():
    nodes = plan("SELECT name FROM users WHERE age > 18")
    filt = next(n for n in nodes if n.type == PlanType.FILTER)
    assert filt.condition.left == "age"
    assert filt.condition.op == ">"
    assert filt.condition.right == "18"


def test_project_has_columns():
    nodes = plan("SELECT name, age FROM users")
    proj = next(n for n in nodes if n.type == PlanType.PROJECT)
    assert proj.columns == ["name", "age"]
