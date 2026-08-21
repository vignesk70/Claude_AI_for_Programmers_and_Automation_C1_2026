"""Seed the SupportOps AI MongoDB database with sample orders and FAQs."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from pymongo import ASCENDING, DESCENDING, TEXT

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db  # noqa: E402

SAMPLE_DATA = PROJECT_ROOT / "sample_data"


def load_json(filename: str) -> list[dict]:
    with (SAMPLE_DATA / filename).open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def prepare_order(document: dict) -> dict:
    prepared = dict(document)
    for field in ("order_date", "estimated_delivery", "delivered_at"):
        prepared[field] = parse_datetime(prepared.get(field))
    return prepared


def prepare_faq(document: dict) -> dict:
    prepared = dict(document)
    prepared["updated_at"] = parse_datetime(prepared.get("updated_at"))
    return prepared


def ensure_indexes(db) -> None:
    db.orders.create_index("order_id", unique=True)
    db.orders.create_index("customer_id")

    db.faqs.create_index("faq_id", unique=True)
    db.faqs.create_index(
        [("question", TEXT), ("answer", TEXT), ("keywords", TEXT)],
        name="faq_text_search",
    )

    db.tickets.create_index("ticket_id", unique=True)
    db.tickets.create_index(
        [("customer_id", ASCENDING), ("created_at", DESCENDING)]
    )
    db.tickets.create_index(
        [("status", ASCENDING), ("created_at", DESCENDING)]
    )


def seed(reset: bool) -> None:
    db = get_db()

    if reset:
        for collection_name in ("tickets", "orders", "faqs"):
            db[collection_name].delete_many({})
        print("Collections cleared.")

    # Seed orders if sample data exists
    orders_path = SAMPLE_DATA / "orders.json"
    order_count = 0
    if orders_path.exists():
        for order in load_json("orders.json"):
            prepared = prepare_order(order)
            db.orders.replace_one(
                {"order_id": prepared["order_id"]},
                prepared,
                upsert=True,
            )
            order_count += 1

    # Seed FAQs
    faq_count = 0
    for faq in load_json("faqs.json"):
        prepared = prepare_faq(faq)
        db.faqs.replace_one(
            {"faq_id": prepared["faq_id"]},
            prepared,
            upsert=True,
        )
        faq_count += 1

    ensure_indexes(db)

    total_orders = db.orders.count_documents({})
    total_faqs = db.faqs.count_documents({})

    print(f"Database: {db.name}")
    print(f"Orders seeded: {order_count} (total in DB: {total_orders})")
    print(f"FAQs seeded: {faq_count} (total in DB: {total_faqs})")
    print("Indexes: ready")
    print("Mode: reset and seed" if reset else "Mode: idempotent upsert")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the SupportOps AI training database."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear training collections before seeding.",
    )
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
