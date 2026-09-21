from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def open_read_only_database(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database was not found: {db_path}")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def collect_schema_report(db_path: str | Path) -> dict[str, Any]:
    path = Path(db_path)
    with open_read_only_database(path) as connection:
        tables = _collect_tables(connection)
        views = _collect_views(connection)
        indexes = _collect_indexes(connection, [table["name"] for table in tables])
        return {
            "database_path": str(path),
            "schema_version": _current_schema_version(connection),
            "tables": tables,
            "indexes": indexes,
            "views": views,
        }


def _current_schema_version(connection: sqlite3.Connection) -> int | None:
    if not _object_exists(connection, "table", "SchemaVersion"):
        return None
    row = connection.execute("SELECT MAX(version) AS version FROM SchemaVersion").fetchone()
    return int(row["version"]) if row and row["version"] is not None else None


def _collect_tables(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    tables: list[dict[str, Any]] = []
    for row in rows:
        table_name = str(row["name"])
        tables.append(
            {
                "name": table_name,
                "internal": table_name.startswith("sqlite_"),
                "row_count": _row_count(connection, table_name),
                "columns": _table_columns(connection, table_name),
                "primary_key": _primary_key_columns(connection, table_name),
                "foreign_keys": _foreign_keys(connection, table_name),
                "sql": row["sql"],
            }
        )
    return tables


def _table_columns(connection: sqlite3.Connection, table_name: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [
        {
            "cid": int(row["cid"]),
            "name": row["name"],
            "type": row["type"],
            "not_null": bool(row["notnull"]),
            "default": row["dflt_value"],
            "primary_key_position": int(row["pk"]),
        }
        for row in rows
    ]


def _primary_key_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    columns = _table_columns(connection, table_name)
    return [
        str(column["name"])
        for column in sorted(columns, key=lambda column: int(column["primary_key_position"]))
        if int(column["primary_key_position"]) > 0
    ]


def _foreign_keys(connection: sqlite3.Connection, table_name: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA foreign_key_list({quote_identifier(table_name)})").fetchall()
    return [
        {
            "id": int(row["id"]),
            "seq": int(row["seq"]),
            "table": row["table"],
            "from": row["from"],
            "to": row["to"],
            "on_update": row["on_update"],
            "on_delete": row["on_delete"],
            "match": row["match"],
        }
        for row in rows
    ]


def _row_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS row_count FROM {quote_identifier(table_name)}").fetchone()
    return int(row["row_count"])


def _collect_indexes(connection: sqlite3.Connection, table_names: list[str]) -> list[dict[str, Any]]:
    indexes: list[dict[str, Any]] = []
    for table_name in table_names:
        for row in connection.execute(f"PRAGMA index_list({quote_identifier(table_name)})").fetchall():
            index_name = str(row["name"])
            indexes.append(
                {
                    "name": index_name,
                    "table": table_name,
                    "unique": bool(row["unique"]),
                    "origin": row["origin"],
                    "partial": bool(row["partial"]),
                    "columns": _index_columns(connection, index_name),
                    "sql": _index_sql(connection, index_name),
                }
            )
    return sorted(indexes, key=lambda index: (str(index["table"]), str(index["name"])))


def _index_columns(connection: sqlite3.Connection, index_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA index_info({quote_identifier(index_name)})").fetchall()
    return [str(row["name"]) for row in rows]


def _index_sql(connection: sqlite3.Connection, index_name: str) -> str | None:
    row = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'index' AND name = ?
        """,
        (index_name,),
    ).fetchone()
    return str(row["sql"]) if row and row["sql"] is not None else None


def _collect_views(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'view'
        ORDER BY name
        """
    ).fetchall()
    return [{"name": row["name"], "sql": row["sql"]} for row in rows]


def _object_exists(connection: sqlite3.Connection, object_type: str, name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = ? AND name = ?
        """,
        (object_type, name),
    ).fetchone()
    return row is not None


def print_text_report(report: dict[str, Any]) -> None:
    print("MCEGold Discovery Portal SQLite Schema Report")
    print("=" * 48)
    print(f"Database path: {report['database_path']}")
    print(f"Current schema version: {report['schema_version']}")
    print()

    print("Tables")
    print("-" * 48)
    for table in report["tables"]:
        internal_marker = " (internal)" if table["internal"] else ""
        print(f"{table['name']}{internal_marker}")
        print(f"  rows: {table['row_count']}")
        primary_key = ", ".join(table["primary_key"]) or "(none)"
        print(f"  primary key: {primary_key}")
        print("  columns:")
        for column in table["columns"]:
            parts = [str(column["name"]), str(column["type"] or "(no type)")]
            if column["not_null"]:
                parts.append("NOT NULL")
            if column["default"] is not None:
                parts.append(f"DEFAULT {column['default']}")
            if column["primary_key_position"]:
                parts.append(f"PK position {column['primary_key_position']}")
            print(f"    - {' | '.join(parts)}")
        if table["foreign_keys"]:
            print("  foreign keys:")
            for foreign_key in table["foreign_keys"]:
                print(
                    "    - "
                    f"{foreign_key['from']} -> {foreign_key['table']}.{foreign_key['to']} "
                    f"(on update {foreign_key['on_update']}, on delete {foreign_key['on_delete']})"
                )
        else:
            print("  foreign keys: (none)")
        print()

    print("Indexes")
    print("-" * 48)
    for index in report["indexes"]:
        unique = " UNIQUE" if index["unique"] else ""
        origin = f", origin={index['origin']}" if index["origin"] else ""
        partial = ", partial" if index["partial"] else ""
        columns = ", ".join(index["columns"]) or "(expression or unavailable)"
        print(f"{index['name']} on {index['table']} ({columns}){unique}{origin}{partial}")
        if index["sql"]:
            print(f"  {index['sql']}")
    print()

    print("Views")
    print("-" * 48)
    for view in report["views"]:
        print(view["name"])
        print(view["sql"])
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the configured Discovery Portal SQLite schema.")
    parser.add_argument("--json", action="store_true", help="Print the schema report as JSON.")
    parser.add_argument(
        "--database",
        help="Override the configured SQLite database path for this inspection only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = args.database or settings.discovery_database_path
    try:
        report = collect_schema_report(db_path)
    except (FileNotFoundError, sqlite3.Error) as error:
        print(f"Could not inspect database: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
