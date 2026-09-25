import re
from pathlib import Path

import pytest

import build

ROOT = Path(__file__).resolve().parent.parent
# Данные салонов/покупателей для проверки лежат локально (в git не попадают — репозиторий публичный)
FORBIDDEN_FILE = Path(__file__).parent / "forbidden.local.txt"
FORBIDDEN = FORBIDDEN_FILE.read_text(encoding="utf-8").split() if FORBIDDEN_FILE.exists() else []
GEORGIAN = re.compile(r"[Ⴀ-ჿ]")


def car(slug, brand, added="2026-01-01", status="available"):
    return {"slug": slug, "brand": brand, "addedDate": added, "status": status}


def test_brand_order_volvo_landrover_porsche_then_alphabetical():
    cars = [car("a", "bmw"), car("b", "porsche"), car("c", "audi"), car("d", "land-rover"), car("e", "volvo")]
    cars = [dict(c, addedDate="2026-01-01") for c in cars]
    groups = build.group_by_brand(cars, ["volvo", "land-rover", "porsche"])
    assert [brand for brand, _ in groups] == ["volvo", "land-rover", "porsche", "audi", "bmw"]


def test_newest_first_within_brand():
    cars = [car("old", "volvo", "2026-01-01"), car("new", "volvo", "2026-09-25")]
    groups = build.group_by_brand(cars, ["volvo"])
    assert [c["slug"] for c in groups[0][1]] == ["new", "old"]


def test_sold_cars_go_after_available_within_brand():
    cars = [car("sold", "volvo", "2026-09-25", "sold"), car("avail", "volvo", "2026-01-01")]
    groups = build.group_by_brand(cars, ["volvo"])
    assert [c["slug"] for c in groups[0][1]] == ["avail", "sold"]


@pytest.mark.parametrize("amount,currency,expected", [
    (73000, "EUR", "73 000 €"),
    (125468, "USD", "125 468 $"),
    (999, "EUR", "999 €"),
])
def test_format_price(amount, currency, expected):
    assert build.format_price(amount, currency) == expected


def test_convert_eur_to_usd_and_back():
    assert build.convert(10000, "EUR", "USD", 1.2) == 12000
    assert build.convert(12000, "USD", "EUR", 1.2) == 10000
    assert build.convert(73050, "EUR", "EUR", 1.2) == 73050


def test_convert_is_exact_to_whole_units():
    assert build.convert(73000, "EUR", "USD", 1.1403) == 83242
    assert build.convert(125468, "USD", "EUR", 1.1403) == 110031


def test_prices_for_car_contains_both_currencies():
    prices = build.prices({"amount": 73000, "currency": "EUR"}, 1.1403)
    assert prices["EUR"] == 73000 and prices["USD"] == 83242


def test_price_labels_always_euro_first_then_dollars(site, valid_car):
    valid_car["price"] = {"amount": 125468, "currency": "USD"}
    car = build.enrich(valid_car, site, 1.1403)
    assert car["priceFirst"] == "110\u202f031\u00a0€"
    assert car["priceSecond"] == "125\u202f468\u00a0$"


def test_built_pages_have_no_approximate_prices_or_georgia(built_site):
    for page in built_site.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert "≈" not in text, page
        assert "Грузи" not in text and "Тбилиси" not in text, page


def test_whatsapp_and_telegram_links(site):
    links = build.contact_links(site["contacts"])
    assert links["whatsapp"] == "https://wa.me/79068646717"
    assert links["telegram"] == "https://t.me/+79068646717"
    assert links["phone"] == "tel:+79068646717"


def test_telegram_username_link():
    assert build.contact_links({"telegram": "@bovid"})["telegram"] == "https://t.me/bovid"


@pytest.fixture(scope="module")
def built_site(tmp_path_factory):
    out = tmp_path_factory.mktemp("docs")
    build.build(out_dir=out, rate=1.1403, rate_date="2026-09-25")
    return out


def test_build_creates_catalog_and_car_pages(built_site):
    assert (built_site / "index.html").exists()
    for slug in build.load_car_slugs():
        assert (built_site / "cars" / slug / "index.html").exists()
        assert (built_site / "print" / f"{slug}.html").exists()
        assert (built_site / "print" / f"{slug}-no-price.html").exists()
        assert any((built_site / "img" / slug).glob("*.webp"))


def test_build_writes_noindex_and_robots(built_site):
    assert "noindex" in (built_site / "index.html").read_text(encoding="utf-8")
    assert "Disallow: /" in (built_site / "robots.txt").read_text(encoding="utf-8")
    assert (built_site / ".nojekyll").exists()


def test_built_html_has_no_dealer_data_or_georgian(built_site):
    for page in built_site.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for word in FORBIDDEN:
            assert word not in text, f"{word} в {page}"
        assert not GEORGIAN.search(text), f"грузинский текст в {page}"


def test_catalog_lists_brands_in_required_order(built_site):
    html = (built_site / "index.html").read_text(encoding="utf-8")
    positions = [html.index(f'id="brand-{b}"') for b in ["volvo", "land-rover", "porsche"]]
    assert positions == sorted(positions)


def test_no_price_print_version_has_no_price(built_site):
    for slug in build.load_car_slugs():
        html = (built_site / "print" / f"{slug}-no-price.html").read_text(encoding="utf-8")
        assert "€" not in html and "$" not in html.replace("$(", "")
        assert 'class="price' not in html


def test_print_version_has_qr_and_contacts(built_site, site):
    slug = build.load_car_slugs()[0]
    html = (built_site / "print" / f"{slug}.html").read_text(encoding="utf-8")
    assert "<svg" in html and "qr" in html
    assert site["contacts"]["manager"] in html


def test_car_page_escapes_html(tmp_path, valid_car, site):
    valid_car["extraOptions"] = ["<script>alert(1)</script>"]
    html = build.render_car_page(valid_car, site, rate=1.1, rate_date="2026-09-25")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_unknown_brand_is_reported(capsys, site):
    build.warn_unknown_brands([{"slug": "x", "brand": "bmw"}, {"slug": "y", "brand": "volvo"}], site)
    out = capsys.readouterr().out
    assert "bmw" in out and "volvo" not in out


def test_contact_links_include_mailto():
    links = build.contact_links({"email": " a@b.ru "})
    assert links["email"] == "mailto:a@b.ru"


def test_footer_signature_has_full_contacts(built_site, site):
    html = (built_site / "index.html").read_text(encoding="utf-8")
    c = site["contacts"]
    for value in (c["manager"], c["title"], c["company"], c["email"], c["address"]):
        assert value in html
    assert f'href="mailto:{c["email"]}"' in html


def test_print_card_has_signature(built_site, site):
    slug = build.load_car_slugs()[0]
    html = (built_site / "print" / f"{slug}-no-price.html").read_text(encoding="utf-8")
    c = site["contacts"]
    for value in (c["title"], c["company"], c["email"], c["address"]):
        assert value in html
