import csv
import os
from models.table import Table


class CSVReader:
    def __init__(self, filepath: str) -> None:
        self._filepath = filepath

    def read(self, columns: list[str] | None = None) -> Table:
        """Read the CSV. If `columns` is given, return only those columns (projection pruning)."""
        table = Table()

        with open(self._filepath, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            raw_headers = [h.strip() for h in next(reader, [])]

            if columns:
                # Only read the projected columns
                indices = [raw_headers.index(c) for c in columns if c in raw_headers]
                table.columns = [raw_headers[i] for i in indices]
                for row in reader:
                    table.rows.append([row[i].strip() if i < len(row) else "" for i in indices])
            else:
                table.columns = raw_headers
                for row in reader:
                    table.rows.append([v.strip() for v in row])

        return table

    def read_headers(self) -> list[str]:
        with open(self._filepath, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            return [h.strip() for h in next(reader, [])]
