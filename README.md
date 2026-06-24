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

The lexer normalizes keywords to uppercase before matching, so `select` and `SELECT` both produce a `SELECT` token. It also handles multi-character operators (`>=`, `<=`, `!=`), string literals in single quotes, integer and float literals, and the `*` wildcard.

### Stage 2 — Parser (`src/parser/`)

The parser consumes the token list and builds an Abstract Syntax Tree (AST) — a chain of node objects that represent the logical structure of the query.

**AST chain for `SELECT name FROM users WHERE age >= 18 ORDER BY age`:**
```
SelectNode(columns=["name"])
    └── WhereNode(condition: age >= 18)
            └── FromNode(table="users", order_by=OrderByNode(column="age"))
```

Each clause maps to a node class defined in `models/ast_nodes.py`. The chain is always `SelectNode → [WhereNode →] FromNode`. `ORDER BY` and `GROUP BY` are stored as separate attributes on `FromNode` (not competing for the same child pointer — a bug present in the original C++ version).

A `WhereNode` is only created if a `WHERE` token is actually seen. `SELECT *` sets a `star=True` flag on `SelectNode` rather than producing an empty column list.

### Stage 3 — Semantic Analyzer (`src/semantic/`)

The semantic analyzer walks the AST and validates it against the catalog — the runtime schema of the queried table. It runs three passes:

1. **Table resolution** — finds the `FromNode` and looks up the table name in the catalog. Raises `SemanticError` if the table does not exist.
2. **Column validation** — checks every column in `SELECT` against the known column names. `SELECT *` skips this check.
3. **WHERE column validation** — checks that the column in the `WHERE` condition exists in the table.

Errors at this stage are always labeled `[Semantic Error]` in the REPL.

### Stage 4 — Catalog (`src/catalog/`)

The catalog is not stored on disk — it is built at runtime by reading the CSV file's headers and sampling the first 20 rows to infer column types (`INT`, `FLOAT`, or `STRING`). This type information is used later for correct numeric sorting.

The catalog is built just before semantic analysis and passed into both the semantic analyzer and the planner.

### Stage 5 — Query Planner (`src/planner/`)

The planner walks the AST and emits a flat, ordered list of `PlanNode` objects — one per operation. The order reflects correct execution semantics:

```
SCAN    → read the table from disk
FILTER  → apply the WHERE condition
SORT    → apply ORDER BY
GROUP   → apply GROUP BY (currently: sort by column; aggregation is a future feature)
PROJECT → select only the requested columns
```

For `SELECT *`, the planner expands the star to the full column list from the catalog at planning time, so the executor never has to think about it.

### Stage 6 — Optimizer (`src/optimizer/`)

The optimizer applies two rules to the plan before execution:

**Projection pruning** — copies the `PROJECT` column list into the `SCAN` node. This tells the CSV reader to read only the needed columns from disk rather than the full row width. Columns required by `FILTER`, `SORT`, or `GROUP` (but not in the final projection) are also included, so downstream operators can still find them.

**Predicate pushdown** — ensures `FILTER` is placed immediately after `SCAN`. This means filtering happens as early as possible, before sorting or grouping, reducing the number of rows that flow through the rest of the pipeline.

### Stage 7 — Executor (`src/executor/`)

The executor runs each plan node in sequence, threading a `Table` object (a list of column names + a list of rows) through the pipeline:

| Node | File | What it does |
|---|---|---|
| `SCAN` | `scan_node.py` | Opens the CSV file via `CSVReader`, reads only the projected columns |
| `FILTER` | `filter_node.py` | Iterates rows, evaluates the condition; tries numeric comparison first, falls back to string equality |
| `SORT` | `sort_node.py` | Uses Python's `sorted()` with a type-aware key — converts to `float` for numeric columns so `9` sorts before `10` |
| `GROUP` | `sort_node.py` | Same sort mechanism applied to the group column |
| `PROJECT` | `executor.py` | Selects column subsets by index; strips any extra columns that were loaded for filtering/sorting |

---

## Project structure

```
sql-engine-py/
│
├── models/                   shared data types — no logic, no I/O
│   ├── tokens.py             TokenType enum + Token dataclass
│   ├── ast_nodes.py          ASTNode class hierarchy (SelectNode, FromNode, etc.)
│   ├── plan.py               PlanType enum + PlanNode dataclass
│   ├── table.py              Table dataclass (columns + rows)
│   ├── catalog.py            ColumnSchema, TableSchema, Catalog dataclasses
│   └── exceptions.py         EngineError hierarchy (LexerError, SemanticError, etc.)
│
├── src/
│   ├── pipeline.py           central entry point — wires all six stages together
│   ├── lexer/lexer.py        Lexer class
│   ├── parser/parser.py      Parser class
│   ├── semantic/analyzer.py  SemanticAnalyzer class
│   ├── catalog/catalog.py    build_catalog() — reads CSV headers, infers types
│   ├── planner/              QueryPlanner class
│   ├── optimizer/            Optimizer class (projection pruning + predicate pushdown)
│   ├── executor/
│   │   ├── executor.py       Executor orchestrator
│   │   ├── scan_node.py      ScanNode
│   │   ├── filter_node.py    FilterNode
│   │   └── sort_node.py      SortNode
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
│   └── employees.csv
│
├── tests/                    pytest test suite
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_semantic.py
│   ├── test_planner.py
│   ├── test_optimizer.py
│   ├── test_executor.py
│   └── test_repl.py
│
├── main.py                   CLI entry point
└── pyproject.toml            dependencies + project metadata
```

### Why each `src/` folder exists

| Folder | Responsibility | Why it is separate |
|---|---|---|
| `lexer/` | Turns characters into tokens | Knows nothing about SQL grammar — only character rules |
| `parser/` | Turns tokens into an AST | Knows grammar, not semantics — never touches the catalog |
| `semantic/` | Validates the AST against the schema | The only stage that combines AST + catalog knowledge |
| `catalog/` | Builds runtime schema from CSV headers | Isolated so tests can inject a fake catalog without touching files |
| `planner/` | Converts AST to an ordered execution plan | Keeps optimization and execution concerns out of the tree-walking logic |
| `optimizer/` | Rewrites the plan for efficiency | Operates purely on `list[PlanNode]` — no AST, no I/O |
| `executor/` | Runs the plan and produces results | Each node type is its own class so new node types can be added without touching others |
| `storage/` | Reads CSV files into `Table` objects | Isolated I/O layer — swap CSV for Parquet or a binary format without touching the executor |

---

## What the tests cover

The test suite has 60 tests across 7 files. Each file targets one stage of the pipeline in isolation, plus an end-to-end executor suite.

### `test_lexer.py`
- Keyword recognition (`SELECT`, `FROM`, `WHERE`, `ORDER`, `BY`, `GROUP`)
- Case-insensitive keywords — `select` and `SELECT` both produce `TokenType.SELECT`
- `SELECT *` produces a `STAR` token (not silently ignored as in the C++ original)
- All six comparison operators (`>`, `<`, `>=`, `<=`, `=`, `!=`)
- Integer, float, and string literals
- Identifiers containing digits (`table1`, `db2`)
- Unterminated string literal raises `LexerError`
- `EOF` token always appended

### `test_parser.py`
- Basic `SELECT column FROM table` structure
- Multiple columns parsed into a list
- `SELECT *` sets `star=True` on `SelectNode`
- `WHERE` condition parsed into `ConditionNode(left, op, right)`
- No `WHERE` clause → no `WhereNode` in the AST (C++ bug: always allocated one)
- `ORDER BY` stored on `FromNode.order_by`
- `GROUP BY` stored on `FromNode.group_by`
- Both `ORDER BY` and `GROUP BY` present → both preserved (C++ bug: second overwrote first)
- `WHERE` + `ORDER BY` together

### `test_semantic.py`
- Valid queries pass without error
- Invalid `SELECT` column raises `SemanticError` naming the column and table
- Invalid `WHERE` column raises `SemanticError`
- Non-existent table raises `SemanticError` with table name
- `SELECT *` is always valid regardless of catalog

### `test_planner.py`
- Basic plan is `[SCAN, PROJECT]`
- `WHERE` inserts a `FILTER` node between `SCAN` and `PROJECT`
- `ORDER BY` inserts a `SORT` node
- `GROUP BY` inserts a `GROUP` node
- `SCAN` node carries the correct table name
- `FILTER` node carries the parsed condition
- `PROJECT` node carries the correct column list

### `test_optimizer.py`
- Projection pruning copies the `PROJECT` column list into `SCAN`
- Predicate pushdown places `FILTER` immediately after `SCAN`
- Optimizer works on a deep copy — original plan is not mutated

### `test_executor.py`
End-to-end tests that run a full SQL string against real CSV files and assert on the result:
- Single and multi-column `SELECT`
- `SELECT *` returns all columns
- `WHERE >`, `>=`, `=`, `!=` with numeric and string values
- `ORDER BY` on a numeric column — verifies `9` sorts before `10` (C++ bug: string sort)
- `ORDER BY` on a string column
- `GROUP BY` sorts by the grouped column
- Lowercase keywords work end-to-end
- Queries against the `employees` table

### `test_repl.py`
- Result table formatted with `psql`-style borders
- Row count footer: `(N rows)` / `(1 row)` / `(0 rows)`
- Long cell values truncated with `...`
- Error messages formatted with stage label

---

## Running locally

**Requirements:** Python 3.11 or later, pip.

```bash
# 1. Clone or copy the project
cd sql-engine-py

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install prompt-toolkit tabulate pygments pytest pytest-cov

# 4. Run the test suite
pytest tests/ -v

# 5. Run a single query (non-interactive)
python main.py -e "SELECT name, age FROM users WHERE age > 20 ORDER BY age"

# 6. Start the interactive REPL
python main.py
```

**Using a custom data directory:**
```bash
python main.py --data-dir /path/to/your/csvs/
python main.py --data-dir /path/to/your/csvs/ -e "SELECT * FROM orders"
```

Any `.csv` file placed in the data directory is immediately queryable — no schema registration required. The engine reads the headers on the first query.

---

## The REPL

The REPL is a full interactive SQL shell built on `prompt_toolkit`.

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
sql-engine>
```

### Features

**Tab completion** — press `Tab` at any point:
- After `FROM`: completes table names from the data directory
- After `SELECT` or `WHERE`: completes column names of the table already typed in `FROM`
- Anywhere: completes SQL keywords (`SELECT`, `FROM`, `WHERE`, `ORDER BY`, `GROUP BY`)
- For `\` commands: completes meta-commands

**Persistent history** — previous queries are saved to `~/.sql_engine_history` and available via the up arrow across sessions.

**Formatted output** — results are rendered as `psql`-style ASCII tables using `tabulate`, with a row count footer. Long cell values are truncated at 40 characters.

**Query timing** — toggle with `\timing`. When on, prints execution time in milliseconds after every result.

**Descriptive errors** — every stage of the pipeline has its own exception class. Errors are labeled with the stage that raised them:

```
sql-engine> SELECT email FROM users
[Semantic Error] column 'email' does not exist in table 'users'

sql-engine> SELECT name FROM ghost_table
[Semantic Error] table 'ghost_table' not found — no file at 'data/ghost_table.csv'
```

### Meta-commands

| Command | Description |
|---|---|
| `\dt` | List all available tables (CSV files in the data directory) |
| `\d <table>` | Show column names and inferred types for a table |
| `\timing` | Toggle query execution timing on/off |
| `\help` | Show all available commands |
| `\q` / `exit` / `quit` | Exit the REPL |

```
sql-engine> \dt
  employees
  users

sql-engine> \d users
Table: users
  name                 STRING
  age                  INT
  city                 STRING
  status               STRING
  salary               INT

sql-engine> \timing
Timing is on.
sql-engine> SELECT * FROM users
...
(7 rows)
Time: 1.23 ms
```

---

## SQL support

| Feature | Supported |
|---|---|
| `SELECT col1, col2, ...` | Yes |
| `SELECT *` | Yes |
| `FROM table` | Yes (single table) |
| `WHERE col op value` | Yes — `>` `<` `>=` `<=` `=` `!=` |
| `ORDER BY col` | Yes — numeric-aware sort |
| `GROUP BY col` | Partial — sorts by column; aggregation functions not yet implemented |
| `AND` / `OR` in `WHERE` | Not yet |
| `JOIN` | Not yet |
| `COUNT`, `SUM`, `AVG` | Not yet |
| Subqueries | Not yet |
| Case-sensitive keywords | Fixed — `select` and `SELECT` both work |

---
