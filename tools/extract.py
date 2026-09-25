"""Извлечение сырого текста и изображений из папки с КП.

Использование: python3 tools/extract.py "PDF 25.09.2026"
Результат: work/<имя pdf>/text.txt, work/<имя pdf>/img-*.{png,jpg}, page-*.jpg (рендеры страниц).
Это сырьё для ручного разбора — на сайт напрямую ничего не попадает.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "work"
MIN_IMAGE_BYTES = 20_000  # иконки и маски меньше — пропускаем
PAGE_RENDER_DPI = 110
FOLDER_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def folder_date(folder: Path) -> str:
    """'PDF 25.09.2026' -> '2026-09-25'."""
    match = FOLDER_DATE_RE.search(folder.name)
    if not match:
        raise ValueError(f"В имени папки нет даты дд.мм.гггг: {folder.name}")
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Команда завершилась с ошибкой: {' '.join(cmd)}\n{result.stderr}")


def smask_pairs(pdf: Path) -> list[tuple[int, int]]:
    """Пары (номер изображения, номер его маски прозрачности) по выводу `pdfimages -list`."""
    listing = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True, check=True)
    pairs = []
    for line in listing.stdout.splitlines()[2:]:
        cols = line.split()
        if len(cols) > 2 and cols[2] == "smask":
            num = int(cols[1])
            pairs.append((num - 1, num))
    return pairs


def find_image(folder: Path, num: int) -> Path | None:
    matches = sorted(folder.glob(f"img-{num:03d}.*"))
    return matches[0] if matches else None


def apply_smasks(pdf: Path, out: Path) -> None:
    """Склеивает изображение с его маской в прозрачный PNG (img-NNN-alpha.png)."""
    for base_num, mask_num in smask_pairs(pdf):
        base, mask = find_image(out, base_num), find_image(out, mask_num)
        if not base or not mask:
            continue
        with Image.open(base) as base_img, Image.open(mask) as mask_img:
            if base_img.size != mask_img.size:
                continue
            rgba = base_img.convert("RGB")
            rgba.putalpha(mask_img.convert("L"))
            rgba.save(out / f"img-{base_num:03d}-alpha.png")
        mask.unlink()


def extract_pdf(pdf: Path) -> Path:
    out = WORK_DIR / slugify(pdf.stem)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    run(["pdftotext", "-layout", str(pdf), str(out / "text.txt")])
    run(["pdfimages", "-all", str(pdf), str(out / "img")])
    run(["pdftoppm", "-r", str(PAGE_RENDER_DPI), "-jpeg", str(pdf), str(out / "page")])
    apply_smasks(pdf, out)
    for image in out.glob("img-*"):
        if image.exists() and image.stat().st_size < MIN_IMAGE_BYTES:
            image.unlink()
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    folder = (ROOT / argv[1]).resolve()
    if not folder.is_dir():
        print(f"Папка не найдена: {folder}")
        return 1
    print(f"Дата поступления: {folder_date(folder)}")
    for pdf in sorted(folder.glob("*.pdf")):
        out = extract_pdf(pdf)
        images = len(list(out.glob("img-*")))
        print(f"  {pdf.name} -> {out.relative_to(ROOT)} ({images} изобр.)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
