from pathlib import Path

import pytest
from PIL import Image

import extract
import images
import pdf

ROOT = Path(__file__).resolve().parent.parent


# ---------- extract ----------

def test_folder_date_parses_russian_format():
    assert extract.folder_date(Path("PDF 25.09.2026")) == "2026-09-25"


def test_folder_date_without_date_raises():
    with pytest.raises(ValueError):
        extract.folder_date(Path("PDF new"))


def test_slugify():
    assert extract.slugify("SAL1A2BW5TA664980  D SE D249") == "sal1a2bw5ta664980-d-se-d249"


def test_smask_pairs_reads_pdfimages_listing(monkeypatch):
    listing = (
        "page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio\n"
        "-----\n"
        "   1     0 image    1200   675  icc     3   8  image  no         5  0   203   203  261K  11%\n"
        "   1     1 smask    1200   675  gray    1   8  image  no         5  0   203   203 33.8K 4.3%\n"
        "   1     2 image    1200   675  icc     3   8  image  no         8  0   409   410  648K  27%\n"
    )

    class Result:
        stdout = listing

    monkeypatch.setattr(extract.subprocess, "run", lambda *a, **k: Result())
    assert extract.smask_pairs(Path("x.pdf")) == [(0, 1)]


def test_apply_smasks_builds_transparent_png(tmp_path, monkeypatch):
    Image.new("RGB", (4, 4), (10, 20, 30)).save(tmp_path / "img-000.png")
    Image.new("L", (4, 4), 128).save(tmp_path / "img-001.png")
    monkeypatch.setattr(extract, "smask_pairs", lambda pdf: [(0, 1)])
    extract.apply_smasks(Path("x.pdf"), tmp_path)
    result = Image.open(tmp_path / "img-000-alpha.png")
    assert result.mode == "RGBA" and result.getpixel((0, 0))[3] == 128
    assert not (tmp_path / "img-001.png").exists()


def test_extract_main_usage_and_missing_folder():
    assert extract.main(["extract.py"]) == 1
    assert extract.main(["extract.py", "нет-такой-папки"]) == 1


def test_run_raises_on_failed_command():
    with pytest.raises(RuntimeError):
        extract.run(["false"])


# ---------- images ----------

def framed_image(size=(1000, 600)) -> Image.Image:
    img = Image.new("RGB", size, (240, 240, 240))
    w, h = size
    for x in range(w):
        for y in (0, h - 1):
            img.putpixel((x, y), (0, 0, 0))
    for y in range(h):
        for x in (0, w - 1):
            img.putpixel((x, y), (0, 0, 0))
    return img


def test_trim_frame_removes_dark_border():
    trimmed = images.trim_frame(framed_image())
    assert trimmed.size == (964, 564)


def test_trim_frame_keeps_normal_photo():
    img = Image.new("RGB", (100, 50), (200, 200, 200))
    assert images.trim_frame(img).size == (100, 50)


def test_crop_to_content_trims_transparent_margins():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (20, 10), (255, 0, 0, 255)), (40, 50))
    assert images.crop_to_content(img).size == (20, 10)


def test_process_writes_webp_with_limited_size(tmp_path):
    src = tmp_path / "big.png"
    Image.new("RGB", (5000, 2000), (100, 100, 100)).save(src)
    size = images.process(src, tmp_path / "out" / "01.webp")
    assert max(size) == images.MAX_SIDE and (tmp_path / "out" / "01.webp").exists()


def test_images_main_imports_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(images, "PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(images, "ROOT", tmp_path)
    sources = []
    for i in range(2):
        path = tmp_path / f"src{i}.png"
        Image.new("RGB", (50, 30), (i * 100, 0, 0)).save(path)
        sources.append(str(path))
    assert images.main(["images.py", "car", *sources]) == 0
    assert sorted(p.name for p in (tmp_path / "photos" / "car").iterdir()) == ["01.webp", "02.webp"]


def test_images_main_reports_missing_files(tmp_path):
    assert images.main(["images.py"]) == 1
    assert images.main(["images.py", "car", str(tmp_path / "nope.png")]) == 1


# ---------- pdf ----------

def test_footer_contains_escaped_contacts():
    footer = pdf.footer_template({"name": "bovidcars", "contacts": {"manager": "<b>Иван</b>", "phone": "+7"}})
    assert "&lt;b&gt;Иван&lt;/b&gt;" in footer and "pageNumber" in footer


def test_targets_filters_by_slug(tmp_path, monkeypatch):
    for name in ("a.html", "a-no-price.html", "b.html"):
        (tmp_path / name).write_text("")
    monkeypatch.setattr(pdf, "PRINT_DIR", tmp_path)
    assert [p.name for p in pdf.targets(["a"])] == ["a-no-price.html", "a.html"]
    assert len(pdf.targets([])) == 3


def test_footer_includes_company_and_email():
    footer = pdf.footer_template({"name": "bovidcars", "contacts": {
        "manager": "Иван", "company": "Ромашка", "phone": "+7", "email": "i@r.ru"}})
    assert "bovidcars · Иван · «Ромашка» · +7 · i@r.ru" in footer
