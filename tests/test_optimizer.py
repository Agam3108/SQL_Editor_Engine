import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.catalog.catalog import build_catalog
from src.planner.query_planner import QueryPlanner
from src.optimizer.optimizer import Optimizer
from models.plan import PlanType


DATA_DIR = "data/"


def optimized_plan(query, data_dir=DATA_DIR):
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
    plan = QueryPlanner(ast, catalog).plan()
    return Optimizer(plan).optimize()


def test_projection_pruning_pushes_columns_into_scan():
    nodes = optimized_plan("SELECT name, age FROM users")
    scan = next(n for n in nodes if n.type == PlanType.SCAN)
    assert set(scan.columns) == {"name", "age"}


def test_predicate_pushdown_filter_after_scan():
    nodes = optimized_plan("SELECT name FROM users WHERE age > 18")
    types = [n.type for n in nodes]
    scan_idx = types.index(PlanType.SCAN)
    filt_idx = types.index(PlanType.FILTER)
    assert filt_idx == scan_idx + 1


def test_optimizer_does_not_mutate_original_plan():
    tokens = Lexer("SELECT name FROM users WHERE age > 18").tokenize()
    ast = Parser(tokens).parse()
    from models.ast_nodes import FromNode
    node = ast
    while node:
        if isinstance(node, FromNode):
            break
        node = node.child
    catalog = build_catalog("users", DATA_DIR)
    plan = QueryPlanner(ast, catalog).plan()
    original_scan_cols = list(next(n for n in plan if n.type == PlanType.SCAN).columns)
    Optimizer(plan).optimize()
    # Original plan's SCAN columns unchanged
    assert next(n for n in plan if n.type == PlanType.SCAN).columns == original_scan_cols
