# sql-engine-py

A SQL query engine built from scratch in Python. No ORM, no database driver, no query library. Raw pipeline engineering — from a string like `SELECT name FROM users WHERE age > 20 ORDER BY age` to a formatted result table, every step implemented by hand.

---

## How a query is executed

Every SQL string passes through six stages in sequence. Each stage is isolated — it only knows about its own input and output types.

```
Raw SQL string
     │
     ▼
┌─────────┐
│  Lexer  │  src/lexer/         breaks the string into tokens
└────┬────┘
     │  list[Token]
     ▼
┌──────────┐
│  Parser  │  src/parser/       builds an Abstract Syntax Tree
└────┬─────┘
     │  ASTNode (linked chain)
     ▼
┌─────────────────────┐
│  Semantic Analyzer  │  src/semantic/   validates tables and columns
└──────────┬──────────┘
           │  ASTNode (unchanged, errors raised if invalid)
           ▼
┌──────────────────┐
│  Query Planner   │  src/planner/    converts AST → flat execution plan
└────────┬─────────┘
         │  list[PlanNode]
         ▼
┌───────────────┐
│   Optimizer   │  src/optimizer/  reorders and prunes the plan
└──────┬────────┘
       │  list[PlanNode] (optimized)
       ▼
┌──────────────┐
│   Executor   │  src/executor/   runs each plan node, returns a Table
└──────┬───────┘
       │  Table (columns + rows)
       ▼
  Formatted result
```

### Stage 1 — Lexer (`src/lexer/`)

The lexer reads the raw SQL string character by character and produces a flat list of `Token` objects. Each token has a type (e.g. `SELECT`, `IDENTIFIER`, `GTE`, `INTEGER`) and a string value.

**Example:**
```
"SELECT name FROM users WHERE age >= 18"
→ [SELECT] [IDENTIFIER:name] [FROM] [IDENTIFIER:users]
  [WHERE] [IDENTIFIER:age] [GTE:>=] [INTEGER:18] [EOF]
```

The lexer normalizes keywords to uppercase before matching, so `select` and `SELECT` both produce a `SELECT` token. It also handles multi-character operators (`>=`, `<=`, `!=`), string literals in single quotes, integer and float literals, the `*` wildcard, and the `.` dot for qualified column names (`table.column`).

### Stage 2 — Parser (`src/parser/`)

The parser consumes the token list and builds an Abstract Syntax Tree (AST) — a chain of node objects that represent the logical structure of the query.

**AST chain for `SELECT name FROM users WHERE age >= 18 ORDER BY age`:**
```
SelectNode(columns=["name"])
    └── WhereNode(condition: age >= 18)
            └── FromNode(table="users", order_by=OrderByNode(column="age"))
```

Each clause maps to a node class defined in `models/ast_nodes.py`. The chain is always `SelectNode → [WhereNode →] FromNode`. `ORDER BY` and `GROUP BY` are stored as separate attributes on `FromNode` (not competing for the same child pointer — a bug present in the original C++ version).

Aggregate functions (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`) are parsed into `AggregateExpr` objects stored on `SelectNode.aggregates`. JOIN clauses are parsed into `JoinClause` objects stored on `FromNode.joins`.

### Stage 3 — Semantic Analyzer (`src/semantic/`)

The semantic analyzer walks the AST and validates it against the catalog — the runtime schema of the queried tables. It runs several passes:

1. **Table resolution** — finds the `FromNode` and looks up every table name (including join targets) in the catalog. Raises `SemanticError` if any table does not exist.
2. **Column validation** — checks every column in `SELECT` against the known column names across all joined tables. `SELECT *` skips this check.
3. **WHERE column validation** — checks that the column in the `WHERE` condition exists.
4. **Aggregate column validation** — checks columns referenced inside aggregate functions; skips `COUNT(*)`.
5. **Join column validation** — checks that each join key exists in its respective table.

### Stage 4 — Catalog (`src/catalog/`)

The catalog is not stored on disk — it is built at runtime by reading CSV file headers and sampling the first 20 rows to infer column types (`INT`, `FLOAT`, or `STRING`). For multi-table queries (joins), all involved tables are loaded into a single `Catalog` via `build_catalog_for_tables()`.

### Stage 5 — Query Planner (`src/planner/`)

The planner walks the AST and emits a flat, ordered list of `PlanNode` objects — one per operation:

```
SCAN        → read a table from disk
HASH_JOIN   → join two scanned tables on a key column (hash join)
FILTER      → apply the WHERE condition
SORT        → apply ORDER BY
GROUP       → apply GROUP BY (sort by column, no aggregation)
AGGREGATE   → compute SUM / AVG / COUNT / MIN / MAX, optionally grouped
PROJECT     → select only the requested columns
```

For `SELECT *`, the planner expands the star to the full column list from the catalog at planning time. When aggregate functions are present, `AGGREGATE` replaces `GROUP` and the `PROJECT` column list is auto-derived from the group column and aggregate output names (e.g. `SUM(salary)`).

### Stage 6 — Optimizer (`src/optimizer/`)

The optimizer applies two rules to the plan before execution:

**Projection pruning** — copies the `PROJECT` column list into each `SCAN` node so the CSV reader loads only needed columns. Columns required by `FILTER`, `SORT`, `GROUP`, `AGGREGATE`, or `HASH_JOIN` (but not in the final projection) are also included.

**Predicate pushdown** — ensures `FILTER` is placed immediately after the last `SCAN` or `HASH_JOIN`, so filtering happens before sorting or grouping, reducing rows flowing through the rest of the pipeline.

### Stage 7 — Executor (`src/executor/`)

The executor runs each plan node in sequence, threading a `Table` object through the pipeline:

| Node | File | What it does |
|---|---|---|
| `SCAN` | `scan_node.py` | Opens the CSV file via `CSVReader`, reads only projected columns |
| `HASH_JOIN` | `join_node.py` | Builds a hash map on the right table's join column, probes with the left table — O(n+m) |
| `FILTER` | `filter_node.py` | Iterates rows, evaluates the condition; tries numeric comparison first, falls back to string equality |
| `SORT` | `sort_node.py` | Uses Python's `sorted()` with a type-aware key — converts to `float` for numeric columns so `9` sorts before `10` |
| `GROUP` | `sort_node.py` | Same sort mechanism applied to the group column |
| `AGGREGATE` | `aggregate_node.py` | Groups rows by `group_col`, computes each aggregate function per group (or over the whole table if no group) |
| `PROJECT` | `executor.py` | Selects column subsets by index; strips any extra columns loaded for intermediate operations |

---

## Project structure

```
sql-engine-py/
│
├── models/                   shared data types — no logic, no I/O
│   ├── tokens.py             TokenType enum + Token dataclass
│   ├── ast_nodes.py          ASTNode hierarchy (SelectNode, FromNode, AggregateExpr, JoinClause, …)
│   ├── plan.py               PlanType enum + PlanNode dataclass
│   ├── table.py              Table dataclass (columns + rows)
│   ├── catalog.py            ColumnSchema, TableSchema, Catalog dataclasses
│   └── exceptions.py         EngineError hierarchy (LexerError, SemanticError, etc.)
│
├── src/
│   ├── pipeline.py           central entry point — wires all stages together
│   ├── lexer/lexer.py        Lexer class
│   ├── parser/parser.py      Parser class
│   ├── semantic/analyzer.py  SemanticAnalyzer class
│   ├── catalog/catalog.py    build_catalog() / build_catalog_for_tables()
│   ├── planner/              QueryPlanner class
│   ├── optimizer/            Optimizer class (projection pruning + predicate pushdown)
│   ├── executor/
│   │   ├── executor.py       Executor orchestrator
│   │   ├── scan_node.py      ScanNode
│   │   ├── filter_node.py    FilterNode
│   │   ├── sort_node.py      SortNode
│   │   ├── aggregate_node.py AggregateNode (SUM / AVG / COUNT / MIN / MAX)
│   │   └── join_node.py      HashJoinNode
│   └── storage/csv_reader.py CSVReader — reads CSV files into Table objects
│
├── repl/                     interactive SQL shell (prompt_toolkit)
│   ├── repl.py               main REPL loop
│   ├── completer.py          SQL keyword + table/column autocomplete
│   ├── formatter.py          tabulate-based result renderer
│   └── history.py            persistent command history
│
├── data/                     CSV files — the "database"
│   ├── users.csv
│   ├── employees.csv
│   └── departments.csv
│
├── tests/                    pytest suite — 86 tests across 9 files
│
├── main.py                   CLI entry point
└── pyproject.toml            dependencies + project metadata
```

---

## SQL support

| Feature | Status |
|---|---|
| `SELECT col1, col2` / `SELECT *` | Yes |
| `FROM table` | Yes |
| `WHERE col op value` — `>` `<` `>=` `<=` `=` `!=` | Yes — numeric-aware |
| `ORDER BY col` | Yes — numeric-aware sort |
| `GROUP BY col` | Yes |
| `SUM(col)`, `AVG(col)`, `COUNT(*)`, `MIN(col)`, `MAX(col)` | Yes |
| `INNER JOIN table ON left_col = right_col` | Yes — hash join O(n+m) |
| `AND` / `OR` in `WHERE` | Not yet |
| Subqueries | Not yet |

---

## Running locally

```bash
cd sql-engine-py
python3 -m venv .venv && source .venv/bin/activate
pip install prompt-toolkit tabulate pygments pytest pytest-cov

pytest tests/ -v

# single query
python main.py -e "SELECT department, SUM(salary) FROM employees GROUP BY department"

# interactive REPL
python main.py
```

Any `.csv` file placed in the data directory is immediately queryable — no schema registration required.

---

## Example queries

```sql
-- aggregation without GROUP BY
SELECT COUNT(*), SUM(salary), AVG(salary) FROM employees

-- aggregation with GROUP BY
SELECT department, COUNT(*), AVG(salary) FROM employees GROUP BY department

-- inner join
SELECT name, budget FROM employees INNER JOIN departments ON dept_id = id

-- join with filter
SELECT name, salary FROM employees INNER JOIN departments ON dept_id = id WHERE salary > 55000
```

---

## The REPL

```
$ python main.py
sql-engine> SELECT name, city FROM users WHERE age > 20 ORDER BY name
+---------+---------+
| name    | city    |
|---------+---------|
| Alice   | Delhi   |
| Charlie | Delhi   |
| David   | Chennai |
| Eve     | Mumbai  |
| Grace   | Delhi   |
+---------+---------+
(5 rows)
```

**Tab completion** — keywords, table names after `FROM`, column names after `SELECT`/`WHERE`.

**Persistent history** — saved to `~/.sql_engine_history`, available via the up arrow across sessions.

**Descriptive errors** — labeled with the pipeline stage that raised them:
```
[Semantic Error] column 'email' does not exist in table 'users'
```

### Meta-commands

| Command | Description |
|---|---|
| `\dt` | List all available tables |
| `\d <table>` | Show column names and inferred types |
| `\timing` | Toggle query execution timing on/off |
| `\q` / `exit` / `quit` | Exit the REPL |
