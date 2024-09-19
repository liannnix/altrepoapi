from pathlib import Path
import datetime

from typing import Iterator, Any, Union
from uuid import UUID

from .base import ConnectionProtocol


def _dump_value(v: Any) -> Union[int, float, str]:
    if isinstance(v, str):
        return f"'{v}'"

    if isinstance(v, (int, float)):
        return v

    if isinstance(v, (datetime.datetime)):
        return f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'"

    if isinstance(v, bool):
        return 1 if v else 0

    if isinstance(v, UUID):
        return str(v)

    return "NULL"


def dump_table(
    conn: ConnectionProtocol, table_name: str, **query_kwargs
) -> Iterator[tuple[Any]]:
    conn.request_line = f"SELECT * FROM {table_name}"
    status, response = conn.send_request(**query_kwargs)

    if not status:
        raise RuntimeError(f"Failed to get data from {table_name}")

    for row in response:
        yield tuple([_dump_value(e) for e in row])


def dump_table_to_csv(
    conn: ConnectionProtocol, table_name: str, **query_kwargs
) -> list[str]:
    return [
        "; ".join(e for e in row)
        for row in dump_table(conn, table_name, **query_kwargs)
    ]


def dumpt_table_to_file(conn: ConnectionProtocol, table_name: str, **query_kwargs):
    with open(Path.home() / f"{table_name}_dump.csv", "wt") as f:
        for line in dump_table_to_csv(conn, table_name, **query_kwargs):
            f.write(line + "\n")
        f.write("\n")
