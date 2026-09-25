"""Сборка сайта: data/*.json → docs/ (каталог, страницы авто, печатные версии для PDF).

Использование: python3 tools/build.py
Курс EUR→USD берётся из API ЕЦБ (frankfurter.dev); если API недоступен — резервный курс из data/site.json.
Каталог docs/pdf/ не трогается — его обновляет tools/pdf.py.
"""
from __future__ import annotations

import json
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

import segno
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image

from validate import load_cars, validate_car

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PHOTOS_DIR = DATA_DIR / "photos"
DOCS_DIR = ROOT / "docs"
KEEP_ON_REBUILD = {"pdf"}
CARD_IMAGE_WIDTH = 960
CARD_IMAGE_QUALITY = 82
PRINT_IMAGE_WIDTH = 1600
PRINT_IMAGE_QUALITY = 82
EDGE_BAND_RATIO = 0.03  # полоса по краям фото для подбора цвета полей
PRINT_BACKGROUND = (245, 245, 247)  # --parchment: фон под прозрачными фото в PDF
RATE_TIMEOUT_S = 10

STATUS_LABELS = {"available": "В наличии", "in_transit": "В пути", "reserved": "Забронировано", "sold": "Продано"}
STATUS_ORDER = {"available": 0, "in_transit": 1, "reserved": 2, "sold": 3}
ENGINE_LABELS = {"electric": "Электро", "diesel": "Дизель", "petrol": "Бензин", "hybrid": "Гибрид"}
CURRENCY_SIGNS = {"EUR": "€", "USD": "$"}
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря")


# ---------- чистые функции (покрыты тестами) ----------

def group_by_brand(cars: list[dict], brand_order: list[str]) -> list[tuple[str, list[dict]]]:
    """Марки в заданном порядке, остальные по алфавиту; внутри — по статусу, затем новые первыми."""
    brands = sorted({c["brand"] for c in cars},
                    key=lambda b: (brand_order.index(b) if b in brand_order else len(brand_order), b))
    groups = []
    for brand in brands:
        items = [c for c in cars if c["brand"] == brand]
        items = sorted(items, key=lambda c: c["addedDate"], reverse=True)
        items = sorted(items, key=lambda c: STATUS_ORDER.get(c["status"], 99))
        groups.append((brand, items))
    return groups


def format_number(value: float) -> str:
    return f"{round(value):,}".replace(",", " ")


def format_price(amount: float, currency: str) -> str:
    return f"{format_number(amount)} {CURRENCY_SIGNS[currency]}"


def convert(amount: float, source: str, target: str, eur_usd: float) -> int:
    if source == target:
        return round(amount)
    raw = amount * eur_usd if source == "EUR" else amount / eur_usd
    return int(round(raw))


def prices(price: dict, eur_usd: float) -> dict:
    return {cur: convert(price["amount"], price["currency"], cur, eur_usd) for cur in CURRENCY_SIGNS}


def contact_links(contacts: dict) -> dict:
    links = {}
    if contacts.get("whatsapp"):
        links["whatsapp"] = "https://wa.me/" + "".join(ch for ch in contacts["whatsapp"] if ch.isdigit())
    if contacts.get("telegram"):
        tg = contacts["telegram"].strip()
        links["telegram"] = "https://t.me/" + (tg[1:] if tg.startswith("@") else "+" + "".join(ch for ch in tg if ch.isdigit()))
    if contacts.get("phone"):
        links["phone"] = "tel:+" + "".join(ch for ch in contacts["phone"] if ch.isdigit())
    return links


def human_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


# ---------- данные ----------

def load_site() -> dict:
    return json.loads((DATA_DIR / "site.json").read_text(encoding="utf-8"))


def load_car_slugs() -> list[str]:
    return [c["slug"] for c in load_cars()]


def fetch_rate(site: dict) -> tuple[float, str]:
    """Курс EUR→USD ЕЦБ; при ошибке — резервный из site.json."""
    try:
        request = urllib.request.Request(site["rate"]["api"], headers={"User-Agent": "bovidcars-build/1.0"})
        with urllib.request.urlopen(request, timeout=RATE_TIMEOUT_S) as resp:
            payload = json.load(resp)
        return float(payload["rates"]["USD"]), payload["date"]
    except (OSError, ValueError, KeyError) as err:
        print(f"! Курс ЕЦБ недоступен ({err}), беру резервный из site.json")
        return site["rate"]["fallbackEurUsd"], site["rate"]["fallbackDate"]


def edge_color(img: Image.Image) -> str:
    """Медианный цвет краёв фото — им заливаются поля, когда фото вписывается в карточку целиком."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    band = max(2, round(min(w, h) * EDGE_BAND_RATIO))
    strips = [rgb.crop((0, 0, w, band)), rgb.crop((0, h - band, w, h)),
              rgb.crop((0, 0, band, h)), rgb.crop((w - band, 0, w, h))]
    pixels = [px for strip in strips for px in strip.resize((64, 64)).getdata()]
    channels = [sorted(px[i] for px in pixels)[len(pixels) // 2] for i in range(3)]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def car_photos(slug: str) -> list[dict]:
    photos = []
    for path in sorted((PHOTOS_DIR / slug).glob("*.webp")):
        with Image.open(path) as img:
            cutout = "A" in img.getbands()
            photos.append({"file": path.name, "width": img.width, "height": img.height,
                           "cutout": cutout, "edge": None if cutout else edge_color(img)})
    return photos


def enrich(car: dict, site: dict, eur_usd: float) -> dict:
    """Добавляет к данным авто вычисляемые поля для шаблонов (исходный словарь не меняется)."""
    brand = site["brands"].get(car["brand"], {"name": car["brand"].replace("-", " ").title(), "logo": None})
    all_prices = prices(car["price"], eur_usd)
    photos = car_photos(car["slug"])
    return {
        **car,
        "brandName": brand["name"],
        "brandLogo": brand["logo"],
        "fullName": f'{brand["name"]} {car["model"]} {car["trim"]}',
        "statusLabel": STATUS_LABELS[car["status"]],
        "engineLabel": ENGINE_LABELS[car["engineType"]],
        # всегда сначала евро, затем доллары
        "priceFirst": format_price(all_prices["EUR"], "EUR"),
        "priceSecond": format_price(all_prices["USD"], "USD"),
        "priceEur": all_prices["EUR"],
        "priceUsd": all_prices["USD"],
        "photos": photos,
        "hasOfficial": any(r.get("official") for s in car.get("specs", []) for r in s["rows"])
                       or any(k.get("official") for k in car["keySpecs"]),
        "url": f'{site["baseUrl"]}cars/{car["slug"]}/',
        "pdfName": f'bovidcars-{brand["name"]}-{car["model"]}-{car["color"]}'.replace(" ", "-") + ".pdf",
    }


# ---------- рендер ----------

def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["human_date"] = human_date
    return env


def _context(site: dict, eur_usd: float, rate_date: str) -> dict:
    return {"site": site, "links": contact_links(site["contacts"]), "rate": eur_usd,
            "rate_date": rate_date, "status_labels": STATUS_LABELS, "engine_labels": ENGINE_LABELS}


def qr_svg(url: str) -> Markup:
    svg = segno.make(url, error="m").svg_inline(scale=3, dark="#1d1d1f", light=None, border=0,
                                                svgclass="qr", omitsize=True)
    return Markup(svg)


def render_car_page(car: dict, site: dict, rate: float, rate_date: str) -> str:
    return _env().get_template("car.html").render(
        car=enrich(car, site, rate), root="../../", **_context(site, rate, rate_date))


def render_print_page(car: dict, site: dict, rate: float, rate_date: str, with_price: bool) -> str:
    rich = enrich(car, site, rate)
    return _env().get_template("print.html").render(
        car=rich, root="../", with_price=with_price, qr=qr_svg(rich["url"]),
        today=date.today().isoformat(), **_context(site, rate, rate_date))


def render_index(cars: list[dict], site: dict, rate: float, rate_date: str) -> str:
    rich = [enrich(c, site, rate) for c in cars]
    groups = group_by_brand(rich, site["brandOrder"])
    brands = {b: site["brands"].get(b, {"name": b.title(), "logo": None}) for b, _ in groups}
    return _env().get_template("index.html").render(
        groups=groups, brands=brands, cars=rich, root="",
        statuses=[s for s in STATUS_LABELS if any(c["status"] == s for c in rich)],
        engines=[e for e in ENGINE_LABELS if any(c["engineType"] == e for c in rich)],
        **_context(site, rate, rate_date))


# ---------- файлы ----------

def _clean(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for child in out_dir.iterdir():
        if child.name in KEEP_ON_REBUILD:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()


def _print_copy(src: Path, dest: Path) -> None:
    """JPEG для PDF: Chrome вшивает JPEG как есть, а WebP — без сжатия (файлы по 10 МБ)."""
    with Image.open(src) as img:
        img = img.convert("RGBA")
        img.thumbnail((PRINT_IMAGE_WIDTH, PRINT_IMAGE_WIDTH), Image.LANCZOS)
        flat = Image.new("RGB", img.size, PRINT_BACKGROUND)
        flat.paste(img, mask=img.getchannel("A"))
        flat.save(dest, "JPEG", quality=PRINT_IMAGE_QUALITY, optimize=True, progressive=True)


def _copy_media(cars: list[dict], out_dir: Path) -> None:
    shutil.copytree(ROOT / "assets", out_dir / "assets")
    shutil.copytree(DATA_DIR / "brands", out_dir / "assets" / "brands")
    for car in cars:
        src, dest = PHOTOS_DIR / car["slug"], out_dir / "img" / car["slug"]
        shutil.copytree(src, dest)
        (dest / "print").mkdir()
        photos = sorted(src.glob("*.webp"))
        for photo in photos:
            _print_copy(photo, dest / "print" / f"{photo.stem}.jpg")
        if photos:
            with Image.open(photos[0]) as img:
                img.thumbnail((CARD_IMAGE_WIDTH, CARD_IMAGE_WIDTH), Image.LANCZOS)
                img.save(dest / "card.webp", "WEBP", quality=CARD_IMAGE_QUALITY, method=6)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(out_dir: Path = DOCS_DIR, rate: float | None = None, rate_date: str | None = None) -> None:
    site = load_site()
    if rate is None:
        rate, rate_date = fetch_rate(site)
    cars = load_cars()
    invalid = {c.get("slug", "?"): validate_car(c) for c in cars}
    invalid = {k: v for k, v in invalid.items() if v}
    if invalid:
        raise ValueError(f"Некорректные данные авто: {invalid}")
    _clean(out_dir)
    _copy_media(cars, out_dir)
    _write(out_dir / "index.html", render_index(cars, site, rate, rate_date))
    for car in cars:
        _write(out_dir / "cars" / car["slug"] / "index.html", render_car_page(car, site, rate, rate_date))
        _write(out_dir / "print" / f'{car["slug"]}.html', render_print_page(car, site, rate, rate_date, True))
        _write(out_dir / "print" / f'{car["slug"]}-no-price.html',
               render_print_page(car, site, rate, rate_date, False))
    _write(out_dir / "robots.txt", "User-agent: *\nDisallow: /\n")
    _write(out_dir / ".nojekyll", "")
    print(f"Собрано: {len(cars)} авто → {out_dir} (курс EUR→USD {rate} на {rate_date})")


if __name__ == "__main__":
    try:
        build()
    except ValueError as err:
        print(f"✗ {err}")
        sys.exit(1)
