"""Lectura y escritura de tablas CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping


def read_csv(path: str | Path) -> list[dict[str, str]]:
    """Lee un CSV como lista de diccionarios; devuelve [] si no existe."""
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(rows: Iterable[Mapping[str, Any]], path: str | Path) -> None:
    """Escribe filas (diccionarios) en ``path`` creando el directorio padre."""
    rows = list(rows)
    if not rows:
        return
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
