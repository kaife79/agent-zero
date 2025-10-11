from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, asdict
from typing import Iterable, Optional

import pandas as pd


@dataclass
class PropertyRecord:
    source: str
    state: Optional[str]
    property_id: Optional[str]
    property_name: Optional[str]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    area: Optional[str]
    property_type: Optional[str]
    assigned_purpose: Optional[str]
    lease_value: Optional[str]
    market_value: Optional[str]
    notes: Optional[str] = None

    def to_row(self) -> dict:
        return asdict(self)


STANDARD_COLUMNS = list(PropertyRecord.__annotations__.keys())


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_csv(path: str, rows: Iterable[dict]) -> None:
    ensure_dir(os.path.dirname(path))
    rows_list = list(rows)
    if not rows_list:
        # Create an empty file with headers
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=STANDARD_COLUMNS)
            writer.writeheader()
        return

    # Normalize columns
    normalized_rows = []
    for r in rows_list:
        nr = {c: r.get(c) for c in STANDARD_COLUMNS}
        normalized_rows.append(nr)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STANDARD_COLUMNS)
        writer.writeheader()
        writer.writerows(normalized_rows)


def append_csv(path: str, rows: Iterable[dict]) -> None:
    ensure_dir(os.path.dirname(path))
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STANDARD_COLUMNS)
        if not exists:
            writer.writeheader()
        for r in rows:
            nr = {c: r.get(c) for c in STANDARD_COLUMNS}
            writer.writerow(nr)


def write_excel(path: str, rows: Iterable[dict], sheet_name: str = "data") -> None:
    ensure_dir(os.path.dirname(path))
    df = pd.DataFrame(list(rows), columns=STANDARD_COLUMNS)
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)


def write_json(path: str, data: dict) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
