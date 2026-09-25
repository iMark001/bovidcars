"""Проверка данных авто в data/cars/*.json.

Использование: python3 tools/validate.py
Код возврата 0 — все авто корректны, 1 — есть ошибки (выводятся списком).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARS_DIR = ROOT / "data" / "cars"
PHOTOS_DIR = ROOT / "data" / "photos"

REQUIRED_FIELDS = ("slug", "brand", "model", "trim", "year", "engineType", "color",
                   "status", "addedDate", "price", "keySpecs", "features", "sourcePdf")
STATUSES = ("available", "in_transit", "reserved", "sold")
CURRENCIES = ("EUR", "USD")
ENGINE_TYPES = ("electric", "diesel", "petrol", "hybrid")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
GEORGIAN_RE = re.compile(r"[Ⴀ-ჿ]")


def _all_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _all_strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _all_strings(v)]
    return []


def _price_errors(price) -> list[str]:
    if not isinstance(price, dict):
        return ["price: ожидается объект {amount, currency}"]
    errors = []
    if price.get("currency") not in CURRENCIES:
        errors.append(f"price.currency: допустимо {CURRENCIES}")
    amount = price.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        errors.append("price.amount: должно быть положительное число")
    return errors


def _identity_errors(car: dict) -> list[str]:
    vin, config_id = car.get("vin"), car.get("configId")
    if not vin and not config_id:
        return ["vin/configId: нужен VIN или номер конфигурации"]
    if vin and not VIN_RE.match(vin):
        return [f"vin: неверный формат VIN ({vin})"]
    return []


def validate_car(car: dict, photos_root: Path = PHOTOS_DIR, require_photos: bool = True) -> list[str]:
    """Возвращает список ошибок; пустой список — авто корректно."""
    errors = [f"{field}: обязательное поле отсутствует" for field in REQUIRED_FIELDS if field not in car]
    if errors:
        return errors
    if not SLUG_RE.match(car["slug"]):
        errors.append("slug: только латиница в нижнем регистре, цифры и дефисы")
    if car["status"] not in STATUSES:
        errors.append(f"status: допустимо {STATUSES}")
    if car["engineType"] not in ENGINE_TYPES:
        errors.append(f"engineType: допустимо {ENGINE_TYPES}")
    if not DATE_RE.match(str(car["addedDate"])):
        errors.append("addedDate: формат ГГГГ-ММ-ДД")
    errors += _price_errors(car["price"])
    errors += _identity_errors(car)
    if any(GEORGIAN_RE.search(s) for s in _all_strings(car)):
        errors.append("текст: найден грузинский текст — нужен перевод")
    if require_photos and not any((photos_root / car["slug"]).glob("*.webp")):
        errors.append(f"фото: нет файлов в {photos_root / car['slug']}")
    return errors


def load_cars(cars_dir: Path = CARS_DIR) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(cars_dir.glob("*.json"))]


def main() -> int:
    cars = load_cars()
    failed = 0
    slugs = [c.get("slug") for c in cars]
    for dup in {s for s in slugs if slugs.count(s) > 1}:
        print(f"✗ повторяющийся slug: {dup}")
        failed += 1
    for car in cars:
        errors = validate_car(car)
        name = car.get("slug", "?")
        if errors:
            failed += 1
            print(f"✗ {name}")
            for error in errors:
                print(f"    {error}")
        else:
            print(f"✓ {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
