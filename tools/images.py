"""Импорт отобранных фото из work/ в data/photos/<slug>/ (WebP, обрезка чёрных рамок, ограничение размера).

Использование: python3 tools/images.py <slug> <src1> [<src2> ...]
Порядок аргументов = порядок в галерее; первое фото — главное (hero).
Прозрачные PNG (машина без фона) сохраняются с альфа-каналом.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PHOTOS_DIR = ROOT / "data" / "photos"
MAX_SIDE = 2400
WEBP_QUALITY = 86
FRAME_DARK_LEVEL = 12      # крайняя строка/столбец темнее этого — признак рамки
FRAME_CROP_RATIO = 0.018   # рамка-тень в КП Land Rover занимает ~1.5% стороны


def _is_dark_line(img: Image.Image, box: tuple[int, int, int, int]) -> bool:
    strip = img.crop(box).convert("L")
    return max(strip.getdata()) <= FRAME_DARK_LEVEL


def has_dark_frame(img: Image.Image) -> bool:
    w, h = img.size
    edges = [(0, 0, 1, h), (w - 1, 0, w, h), (0, 0, w, 1), (0, h - 1, w, h)]
    return all(_is_dark_line(img, box) for box in edges)


def trim_frame(img: Image.Image) -> Image.Image:
    """Срезает чёрную рамку с тенью по краям (есть у фото из КП Land Rover)."""
    if img.mode == "RGBA" or not has_dark_frame(img):
        return img
    w, h = img.size
    pad = round(max(w, h) * FRAME_CROP_RATIO)  # рамка одинаковой толщины со всех сторон
    return img.crop((pad, pad, w - pad, h - pad))


def crop_to_content(img: Image.Image) -> Image.Image:
    """У прозрачных изображений убирает пустые поля вокруг машины."""
    if img.mode != "RGBA":
        return img
    bbox = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return img.crop(bbox) if bbox else img


def process(src: Path, dest: Path) -> tuple[int, int]:
    with Image.open(src) as original:
        img = original.convert("RGBA" if "A" in original.getbands() else "RGB")
    img = crop_to_content(trim_frame(img))
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "WEBP", quality=WEBP_QUALITY, method=6)
    return img.size


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    slug, sources = argv[1], [Path(a) for a in argv[2:]]
    missing = [s for s in sources if not s.exists()]
    if missing:
        print("Файлы не найдены:", *missing, sep="\n  ")
        return 1
    out_dir = PHOTOS_DIR / slug
    for old in out_dir.glob("*.webp"):
        old.unlink()
    for index, src in enumerate(sources, start=1):
        dest = out_dir / f"{index:02d}.webp"
        width, height = process(src, dest)
        print(f"  {src} -> {dest.relative_to(ROOT)} ({width}x{height})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
