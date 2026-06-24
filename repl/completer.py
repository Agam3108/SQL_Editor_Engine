import os
import re
from prompt_toolkit.completion import Completer, Completion

_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "ORDER BY", "GROUP BY",
    "AND", "OR", "NOT",
]

_META_COMMANDS = ["\\q", "\\dt", "\\d ", "\\timing", "\\help"]


class SQLCompleter(Completer):
    def __init__(self, data_dir: str = "data/") -> None:
        self._data_dir = data_dir

    def _tables(self) -> list[str]:
        try:
            return [
                f[:-4] for f in os.listdir(self._data_dir) if f.endswith(".csv")
            ]
        except FileNotFoundError:
            return []

    def _columns(self, table: str) -> list[str]:
        import csv
        path = os.path.join(self._data_dir, f"{table}.csv")
        try:
            with open(path, encoding="utf-8", newline="") as f:
                return [h.strip() for h in next(csv.reader(f), [])]
        except (FileNotFoundError, StopIteration):
            return []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        upper = text.upper()

        # After FROM — complete table names
        if re.search(r"\bFROM\s+\w*$", upper):
            for t in self._tables():
                if t.lower().startswith(word.lower()):
                    yield Completion(t, start_position=-len(word))
            return

        # After SELECT or WHERE — try to complete column names using the FROM table
        m = re.search(r"\bFROM\s+(\w+)", upper)
        if m and re.search(r"\b(SELECT|WHERE)\b", upper):
            table = m.group(1).lower()
            for col in self._columns(table):
                if col.lower().startswith(word.lower()):
                    yield Completion(col, start_position=-len(word))

        # SQL keywords
        for kw in _SQL_KEYWORDS:
            if kw.startswith(word.upper()):
                yield Completion(kw, start_position=-len(word))

        # Meta-commands
        if word.startswith("\\"):
            for cmd in _META_COMMANDS:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
