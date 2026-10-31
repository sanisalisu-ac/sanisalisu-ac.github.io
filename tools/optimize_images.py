#!/usr/bin/env python3
"""Tidy content added through the browser editor (admin/), so editing never needs technical care.

For every gallery album:
  * gives the album an ID from its title if it has none (and keeps IDs unique);
  * moves newly uploaded photos from assets/img/uploads/ into assets/img/gallery/<album-id>/,
    turns them the right way up, resizes them to at most 1600 px (JPEG) and makes a 600 px thumbnail;
  * also shrinks any oversized photo and recreates any missing thumbnail.
Also normalises paths written by the editor ("/assets/..." -> "assets/...") in talks, events and news,
and keeps talks, workshops and news in reverse chronological order.

Run by the workflow on every build; safe to run locally:  python tools/optimize_images.py
"""
import json, pathlib, re
from PIL import Image, ImageOps

try:  # iPhone photos (HEIC); optional
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, IMG = ROOT / "data", ROOT / "assets" / "img"
UPLOADS = IMG / "uploads"
FULL, THUMB, MAX_BYTES = 1600, 600, 700_000


def rel(p):
    return (p or "").lstrip("/") if isinstance(p, str) else p


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48] or "album"


def save(im, path, width, quality):
    im = im.copy()
    im.thumbnail((width, width * 2))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path.relative_to(ROOT).as_posix()


def process_image(entry, album_id, index):
    """Return True if the entry changed."""
    src = rel(entry.get("src"))
    if not src or src.startswith("http"):
        return False
    path = ROOT / src
    if not path.exists():
        print("missing photo:", src)
        return False
    thumb = rel(entry.get("thumb"))
    in_uploads = UPLOADS in path.parents
    too_big = path.stat().st_size > MAX_BYTES or path.suffix.lower() not in (".jpg", ".jpeg")
    needs_thumb = not thumb or not (ROOT / thumb).exists()
    if not (in_uploads or too_big or needs_thumb):
        if entry.get("src") != src or entry.get("thumb") != thumb:
            entry["src"], entry["thumb"] = src, thumb
            return True
        return False
    pic = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    folder = IMG / "gallery" / album_id
    if in_uploads or too_big:
        stem = f"{index + 1:02d}-" + slugify(path.stem)[:40]
        target = folder / f"{stem}.jpg"
        n = 2
        while target.exists() and target != path:
            target = folder / f"{stem}-{n}.jpg"
            n += 1
        entry["src"] = save(pic, target, FULL, 82)
        if path != target:
            path.unlink()
        path = target
    entry["thumb"] = save(pic, path.with_name(path.stem + "-t.jpg"), THUMB, 78)
    print("photo ready:", entry["src"])
    return True


def by_date_desc(items):
    return sorted(items, key=lambda x: str(x.get("date") or ""), reverse=True)


def main():
    changed = set()

    g = json.loads((DATA / "gallery.json").read_text(encoding="utf-8"))
    seen = set()
    for a in g["albums"]:
        year = str(a.get("date", ""))[:4]
        title = a.get("title", "")
        aid = (a.get("id") or "").strip() or slugify(title if year in title else f"{title} {year}")
        base, n = aid, 2
        while aid in seen:
            aid, n = f"{base}-{n}", n + 1
        seen.add(aid)
        if a.get("id") != aid:
            a["id"] = aid
            changed.add("gallery")
        for k in ("cover",):
            if a.get(k) in (None, ""):
                a[k] = 0
        a["images"] = [im for im in (a.get("images") or []) if im.get("src")]
        for i, im in enumerate(a["images"]):
            try:
                if process_image(im, aid, i):
                    changed.add("gallery")
            except Exception as e:  # noqa: BLE001
                print("could not process", im.get("src"), e)
    if "gallery" in changed:
        (DATA / "gallery.json").write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for name, lists, fields in (("talks", ("talks", "workshops"), ("slides", "url")),
                                ("news", ("news",), ("link",)),
                                ("events", ("events",), ("url",))):
        f = DATA / f"{name}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        before = json.dumps(d, sort_keys=True)
        for key in lists:
            items = d.get(key) or []
            for it in items:
                for fld in fields:
                    if isinstance(it.get(fld), str) and it[fld].startswith("/assets/"):
                        it[fld] = rel(it[fld])
                    if it.get(fld) == "":
                        it[fld] = None
            d[key] = sorted(items, key=lambda x: str(x.get("start") or "")) if key == "events" else by_date_desc(items)
        if json.dumps(d, sort_keys=True) != before:
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed.add(name)
    print("tidied:", ", ".join(sorted(changed)) or "nothing to do")


if __name__ == "__main__":
    main()
