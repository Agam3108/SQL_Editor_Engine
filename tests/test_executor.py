import pytest
from src.pipeline import execute_pipeline

DATA_DIR = "data/"


def run(query):
    return execute_pipeline(query, DATA_DIR)


# ── basic queries ─────────────────────────────────────────────────────────────

def test_select_single_column():
    result = run("SELECT name FROM users")
    assert result.columns == ["name"]
    assert len(result.rows) == 7
    names = [r[0] for r in result.rows]
    assert "Alice" in names


def test_select_multiple_columns():
    result = run("SELECT name, age FROM users")
    assert result.columns == ["name", "age"]


def test_select_star():
    result = run("SELECT * FROM users")
    assert "name" in result.columns
    assert "age" in result.columns
    assert len(result.rows) == 7


# ── WHERE filtering ───────────────────────────────────────────────────────────

def test_where_gt():
    result = run("SELECT name FROM users WHERE age > 20")
    ages_returned = [r[0] for r in result.rows]
    assert "Bob" not in ages_returned   # age 17
    assert "Frank" not in ages_returned  # age 16


def test_where_eq_string():
    result = run("SELECT name FROM users WHERE city = 'Delhi'")
    names = [r[0] for r in result.rows]
    assert "Alice" in names
    assert "Bob" not in names  # Bob is in Mumbai


def test_where_gte():
    result = run("SELECT name FROM users WHERE age >= 25")
    names = [r[0] for r in result.rows]
    assert "Alice" in names  # age 25
    assert "Charlie" in names  # age 30
    assert "David" not in names  # age 22


def test_where_neq():
    result = run("SELECT name FROM users WHERE status != 'active'")
    names = [r[0] for r in result.rows]
    assert "Bob" in names
    assert "Alice" not in names


# ── ORDER BY ──────────────────────────────────────────────────────────────────

def test_order_by_numeric():
    """Numeric sort: '9' should NOT sort after '10' (fixes string-sort bug)."""
    result = run("SELECT name, age FROM users ORDER BY age")
    ages = [int(r[1]) for r in result.rows]
    assert ages == sorted(ages)


def test_order_by_string():
    result = run("SELECT name FROM users ORDER BY name")
    names = [r[0] for r in result.rows]
    assert names == sorted(names)


# ── GROUP BY ─────────────────────────────────────────────────────────────────

def test_group_by_sorts_by_column():
    result = run("SELECT name, city FROM users GROUP BY city")
    cities = [r[1] for r in result.rows]
    assert cities == sorted(cities)


# ── case-insensitive keywords ─────────────────────────────────────────────────

def test_lowercase_keywords():
    result = run("select name from users where age > 20")
    assert result.columns == ["name"]
    assert len(result.rows) > 0


# ── employees table ───────────────────────────────────────────────────────────

def test_employees_table():
    result = run("SELECT name, department FROM employees WHERE salary > 55000")
    names = [r[0] for r in result.rows]
    assert "Alice" in names
    assert "Bob" not in names  # salary 50000
