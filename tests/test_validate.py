from pathlib import Path

import pytest

import validate

ROOT = Path(__file__).resolve().parent.parent


def test_valid_car_has_no_errors(valid_car):
    assert validate.validate_car(valid_car, require_photos=False) == []


@pytest.mark.parametrize("field", ["slug", "brand", "model", "trim", "year", "status", "price", "addedDate"])
def test_missing_required_field_is_reported(valid_car, field):
    del valid_car[field]
    errors = validate.validate_car(valid_car, require_photos=False)
    assert any(field in e for e in errors)


def test_unknown_status_is_rejected(valid_car):
    valid_car["status"] = "maybe"
    assert any("status" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_unknown_currency_is_rejected(valid_car):
    valid_car["price"] = {"amount": 1000, "currency": "GEL"}
    assert any("currency" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_non_positive_price_is_rejected(valid_car):
    valid_car["price"]["amount"] = 0
    assert any("amount" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_car_needs_vin_or_config_id(valid_car):
    valid_car["vin"] = None
    valid_car["configId"] = None
    assert any("vin" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_invalid_vin_format_is_rejected(valid_car):
    valid_car["vin"] = "SHORT123"
    assert any("vin" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_bad_date_is_rejected(valid_car):
    valid_car["addedDate"] = "25.09.2026"
    assert any("addedDate" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_bad_slug_is_rejected(valid_car):
    valid_car["slug"] = "Bad Slug/../x"
    assert any("slug" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_missing_photos_are_reported(valid_car, tmp_path):
    errors = validate.validate_car(valid_car, photos_root=tmp_path)
    assert any("фото" in e for e in errors)


def test_georgian_text_is_rejected(valid_car):
    valid_car["extraOptions"] = ["ტყავის საჭე"]
    assert any("грузин" in e for e in validate.validate_car(valid_car, require_photos=False))


def test_all_project_cars_are_valid():
    cars = validate.load_cars(ROOT / "data" / "cars")
    assert len(cars) >= 6
    for car in cars:
        assert validate.validate_car(car) == [], car["slug"]


def test_main_returns_zero_for_project_data():
    assert validate.main() == 0


@pytest.mark.parametrize("brand", ["Land Rover", "Volvo", "land rover", "land_rover"])
def test_brand_must_be_slug_key(valid_car, brand):
    valid_car["brand"] = brand
    assert any("brand" in e for e in validate.validate_car(valid_car, require_photos=False))
