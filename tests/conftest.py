import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture
def valid_car() -> dict:
    return copy.deepcopy({
        "slug": "test-car",
        "brand": "volvo",
        "model": "EX90",
        "trim": "Ultra",
        "year": 2027,
        "engineType": "electric",
        "color": "Denim Blue",
        "interior": "Кожа",
        "wheels": "21″",
        "vin": "YV1TFEVB2SG022136",
        "configId": None,
        "status": "available",
        "addedDate": "2026-09-25",
        "price": {"amount": 73000, "currency": "EUR"},
        "keySpecs": [{"label": "Мощность", "value": "456 л.с."}],
        "extraOptions": ["Опция"],
        "specs": [{"title": "Силовая установка", "rows": [{"label": "Мощность", "value": "456 л.с."}]}],
        "features": [{"title": "Безопасность", "items": ["ABS"]}],
        "supplemented": [],
        "sourcePdf": "PDF 25.09.2026/x.pdf",
    })


@pytest.fixture
def site() -> dict:
    return json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
