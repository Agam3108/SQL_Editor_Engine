import os
from prompt_toolkit.history import FileHistory as _FileHistory


_HISTORY_PATH = os.path.expanduser("~/.sql_engine_history")

_SKIP = {"exit", "quit", "\\q", ""}


class FilteredHistory(_FileHistory):
    """FileHistory that silently drops blank lines and exit commands."""

    def append_string(self, string: str) -> None:
        if string.strip().lower() not in _SKIP:
            super().append_string(string)


def make_history() -> FilteredHistory:
    return FilteredHistory(_HISTORY_PATH)
