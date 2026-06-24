import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.catalog.catalog import build_catalog
from src.semantic.analyzer import SemanticAnalyzer
from models.exceptions import SemanticError


DATA_DIR = "data/"


def analyze(query, data_dir=DATA_DIR):
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
    catalog = build_catalog(table_name, data_dir)
    SemanticAnalyzer(ast, catalog).analyze()


def test_valid_query():
    analyze("SELECT name FROM users")


def test_valid_query_with_where():
    analyze("SELECT name FROM users WHERE age > 18")


def test_invalid_column():
    with pytest.raises(SemanticError, match="column 'email'"):
        analyze("SELECT email FROM users")


def test_invalid_where_column():
    with pytest.raises(SemanticError, match="column 'score'"):
        analyze("SELECT name FROM users WHERE score > 10")


def test_invalid_table():
    tokens = Lexer("SELECT name FROM nonexistent").tokenize()
    from src.parser.parser import Parser as P
    ast = P(tokens).parse()
    from models.catalog import Catalog
    empty_catalog = Catalog()
    with pytest.raises(SemanticError, match="table 'nonexistent'"):
        SemanticAnalyzer(ast, empty_catalog).analyze()


def test_select_star_is_valid():
    analyze("SELECT * FROM users")
