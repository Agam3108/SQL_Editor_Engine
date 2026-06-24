import os
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from repl.completer import SQLCompleter
from repl.formatter import format_result, format_error
from repl.history import make_history
from models.exceptions import EngineError

_STYLE = Style.from_dict({"prompt": "ansicyan bold"})

_HELP = """\
Available commands:
  \\q, exit, quit   Exit the REPL
  \\dt              List all available tables
  \\d <table>       Describe a table (columns + types)
  \\timing          Toggle query execution timing
  \\help            Show this help

Any other input is treated as a SQL query."""


def run_repl(data_dir: str = "data/") -> None:
    from src.pipeline import execute_pipeline  # local import to avoid circular dep at module level

    session = PromptSession(
        history=make_history(),
        completer=SQLCompleter(data_dir),
        style=_STYLE,
        mouse_support=False,
    )

    timing_enabled = False

    while True:
        try:
            query = session.prompt("sql-engine> ")
        except KeyboardInterrupt:
            continue
        except EOFError:
            print("\nBye.")
            break

        stripped = query.strip()

        if not stripped:
            continue

        if stripped.lower() in ("exit", "quit", "\\q"):
            print("Bye.")
            break

        if stripped == "\\help":
            print(_HELP)
            continue

        if stripped == "\\timing":
            timing_enabled = not timing_enabled
            state = "on" if timing_enabled else "off"
            print(f"Timing is {state}.")
            continue

        if stripped == "\\dt":
            _cmd_list_tables(data_dir)
            continue

        if stripped.startswith("\\d "):
            table_name = stripped[3:].strip()
            _cmd_describe(table_name, data_dir)
            continue

        # SQL query
        try:
            t0 = time.perf_counter()
            result = execute_pipeline(stripped, data_dir)
            elapsed = time.perf_counter() - t0
            print(format_result(result))
            if timing_enabled:
                print(f"Time: {elapsed * 1000:.2f} ms")
        except EngineError as e:
            stage = type(e).__name__.replace("Error", " Error")
            print(format_error(stage, str(e)))
        except Exception as e:
            print(f"[Engine Error] Cannot execute query: {type(e).__name__}: {e}")


def _cmd_list_tables(data_dir: str) -> None:
    try:
        tables = [f[:-4] for f in os.listdir(data_dir) if f.endswith(".csv")]
    except FileNotFoundError:
        print(f"Data directory '{data_dir}' not found.")
        return
    if not tables:
        print("No tables found.")
    else:
        print("\n".join(f"  {t}" for t in sorted(tables)))


def _cmd_describe(table_name: str, data_dir: str) -> None:
    from src.catalog.catalog import build_catalog
    try:
        catalog = build_catalog(table_name, data_dir)
        schema = catalog.get_table(table_name)
        if schema is None:
            print(f"Table '{table_name}' not found.")
            return
        print(f"Table: {schema.table_name}")
        for col in schema.columns:
            print(f"  {col.col_name:<20} {col.col_type}")
    except FileNotFoundError:
        print(f"Table '{table_name}' not found.")
