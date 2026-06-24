import argparse
from repl.formatter import format_result
from src.pipeline import execute_pipeline
from models.exceptions import EngineError


def main() -> None:
    ap = argparse.ArgumentParser(description="SQL Engine — a from-scratch SQL query engine")
    ap.add_argument("--data-dir", default="data/", help="Path to CSV data directory")
    ap.add_argument("-e", "--execute", metavar="QUERY",
                    help="Execute a single query and exit (non-interactive)")
    args = ap.parse_args()

    if args.execute:
        try:
            result = execute_pipeline(args.execute, args.data_dir)
            print(format_result(result))
        except EngineError as exc:
            stage = type(exc).__name__.replace("Error", " Error")
            print(f"[{stage}] {exc}")
        except Exception as exc:
            print(f"[Engine Error] Cannot execute query: {type(exc).__name__}: {exc}")
    else:
        from repl.repl import run_repl
        run_repl(args.data_dir)


if __name__ == "__main__":
    main()
