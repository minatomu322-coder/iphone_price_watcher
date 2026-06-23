from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


CSV_HEADER = [
    "timestamp",
    "product",
    "capacity",
    "shop",
    "price",
    "cost_price",
    "profit",
    "decision",
    "previous_delta",
    "yesterday_delta",
    "status",
    "message",
    "url",
]


def ensure_csv(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists():
        return

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    ensure_csv(csv_path)
    with csv_path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def get_latest_price(csv_path: Path, product: str, shop: str) -> int | None:
    latest_price: int | None = None
    for row in read_rows(csv_path):
        if row["product"] != product or row["shop"] != shop or row["status"] != "ok":
            continue
        if row["price"]:
            latest_price = int(row["price"])
    return latest_price


def get_price_near_yesterday(csv_path: Path, product: str, shop: str, now: datetime) -> int | None:
    target_time = now - timedelta(days=1)
    max_distance_seconds = 3 * 60 * 60
    best_row: dict[str, str] | None = None
    best_distance: float | None = None

    for row in read_rows(csv_path):
        if row["product"] != product or row["shop"] != shop or row["status"] != "ok" or not row["price"]:
            continue
        try:
            observed_at = datetime.fromisoformat(row["timestamp"])
        except ValueError:
            continue
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        distance = abs((observed_at - target_time).total_seconds())
        if distance > max_distance_seconds:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_row = row

    return int(best_row["price"]) if best_row else None


def append_history(csv_path: Path, row: dict) -> None:
    ensure_csv(csv_path)
    with csv_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADER)
        writer.writerow(row)
