import pytest
from repl.formatter import format_result, format_error
from models.table import Table


def test_format_result_basic():
    table = Table(columns=["name", "age"], rows=[["Alice", "25"], ["Bob", "30"]])
    output = format_result(table)
    assert "Alice" in output
    assert "Bob" in output
    assert "(2 rows)" in output


def test_format_result_single_row():
    table = Table(columns=["name"], rows=[["Alice"]])
    output = format_result(table)
    assert "(1 row)" in output


def test_format_result_empty():
    table = Table(columns=[], rows=[])
    output = format_result(table)
    assert "(0 rows)" in output


def test_format_result_truncates_long_values():
    long_val = "x" * 100
    table = Table(columns=["col"], rows=[[long_val]])
    output = format_result(table)
    assert "..." in output
    assert long_val not in output


def test_format_error():
    msg = format_error("Semantic Error", "column 'email' does not exist in table 'users'")
    assert "[Semantic Error]" in msg
    assert "email" in msg
