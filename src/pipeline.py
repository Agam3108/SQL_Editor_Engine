"""Central pipeline: lex → parse → semantic → plan → optimize → execute."""

from models.table import Table
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.catalog.catalog import build_catalog_for_tables
from src.semantic.analyzer import SemanticAnalyzer
from src.planner.query_planner import QueryPlanner
from src.optimizer.optimizer import Optimizer
from src.executor.executor import Executor
from models.ast_nodes import FromNode


def _extract_all_table_names(root) -> list[str]:
    node = root
    while node is not None:
        if isinstance(node, FromNode):
            names = [node.table] if node.table else []
            names += [j.table for j in node.joins if j.table]
            return names
        node = node.child
    return []


def execute_pipeline(query: str, data_dir: str = "data/") -> Table:
    tokens = Lexer(query).tokenize()
    ast = Parser(tokens).parse()

    table_names = _extract_all_table_names(ast)
    catalog = build_catalog_for_tables(table_names, data_dir) if table_names else None

    if catalog:
        SemanticAnalyzer(ast, catalog).analyze()

    planner = QueryPlanner(ast, catalog)
    plan = planner.plan()

    optimized = Optimizer(plan).optimize()

    return Executor(optimized, data_dir).execute()
