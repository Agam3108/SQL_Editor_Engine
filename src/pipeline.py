"""Central pipeline: lex → parse → semantic → plan → optimize → execute."""

from models.table import Table
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.catalog.catalog import build_catalog
from src.semantic.analyzer import SemanticAnalyzer
from src.planner.query_planner import QueryPlanner
from src.optimizer.optimizer import Optimizer
from src.executor.executor import Executor
from models.ast_nodes import FromNode


def _extract_table_name(root) -> str:
    node = root
    while node is not None:
        if isinstance(node, FromNode):
            return node.table
        node = node.child
    return ""


def execute_pipeline(query: str, data_dir: str = "data/") -> Table:
    tokens = Lexer(query).tokenize()
    ast = Parser(tokens).parse()

    table_name = _extract_table_name(ast)
    catalog = build_catalog(table_name, data_dir) if table_name else None

    if catalog:
        SemanticAnalyzer(ast, catalog).analyze()

    planner = QueryPlanner(ast, catalog)
    plan = planner.plan()

    optimized = Optimizer(plan).optimize()

    return Executor(optimized, data_dir).execute()
