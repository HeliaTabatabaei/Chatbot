import json
from pathlib import Path
from typing import Any


CUSTOMERS_FILE = Path("data/customers.json")


def load_customers() -> list[dict[str, Any]]:
    with CUSTOMERS_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return payload["customers"]


def normalize_text(value: str) -> str:
    return (
        value.casefold()
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("\u200c", " ")
        .strip()
    )


def resolve_customer_from_query(
    query: str,
    customers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    normalized_query = normalize_text(query)

    matches: list[tuple[int, dict[str, Any]]] = []

    for customer in customers:
        for alias in customer.get("aliases", []):
            normalized_alias = normalize_text(alias)

            if normalized_alias and normalized_alias in normalized_query:
                matches.append((len(normalized_alias), customer))

    if not matches:
        return None

    # انتخاب alias دقیق‌تر و طولانی‌تر
    matches.sort(key=lambda item: item[0], reverse=True)

    # نکته مهم: کل customer برگردانده می‌شود
    return matches[0][1]
