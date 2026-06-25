import csv
import os
from models.catalog import Catalog, TableSchema, ColumnSchema


def _infer_type(samples: list[str]) -> str:
    """Infer column type by attempting numeric conversion on non-empty samples."""
    non_empty = [s for s in samples if s.strip()]
    if not non_empty:
        return "STRING"
    for val in non_empty:
        try:
            int(val)
        except ValueError:
            break
    else:
        return "INT"
    for val in non_empty:
        try:
            float(val)
        except ValueError:
            return "STRING"
    return "FLOAT"


def build_catalog_for_tables(table_names: list[str], data_dir: str = "data/") -> Catalog:
    """Build a Catalog containing schemas for multiple tables."""
    catalog = Catalog()
    for name in table_names:
        single = build_catalog(name, data_dir)
        catalog.tables.extend(single.tables)
    return catalog


def build_catalog(table_name: str, data_dir: str = "data/") -> Catalog:
    """Read CSV headers (and first few rows) to build a Catalog for the given table."""
    from models.exceptions import SemanticError
    path = os.path.join(data_dir, f"{table_name}.csv")
    if not os.path.exists(path):
        raise SemanticError(f"table '{table_name}' not found — no file at '{path}'")
    schema = TableSchema(table_name=table_name)

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        headers = [h.strip() for h in headers]

        # Collect sample values per column for type inference
        samples: dict[str, list[str]] = {h: [] for h in headers}
        for i, row in enumerate(reader):
            if i >= 20:
                break
            for j, val in enumerate(row):
                if j < len(headers):
                    samples[headers[j]].append(val.strip())

    for h in headers:
        schema.columns.append(ColumnSchema(col_name=h, col_type=_infer_type(samples[h])))

    catalog = Catalog()
    catalog.tables.append(schema)
    return catalog
