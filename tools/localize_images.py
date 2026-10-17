#!/usr/bin/env python3
"""Download every external image (gallery and portrait) into the repository, resized for the web,
and point data/*.json at the local copies. Run once from the workflow (input "localize_images")
or locally:  pip install pillow && python tools/localize_images.py
After this the site no longer depends on the old WordPress site at all.
"""
import io, json, pathlib, re, urllib.request
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, IMG = ROOT / "data", ROOT / "assets" / "img"


def fetch(url):
    big = url.split("?")[0] + ("?w=1600" if "wordpress.com" in url else "")
    req = urllib.request.Request(big, headers={"User-Agent": "academic-site-localizer/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(r.read()))).convert("RGB")


def save(im, path, width, quality):
    im = im.copy()
    im.thumbnail((width, width * 2))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path.relative_to(ROOT).as_posix()


def main():
    g = json.loads((DATA / "gallery.json").read_text())
    done = failed = 0
    for a in g["albums"]:
        for i, im in enumerate(a["images"]):
            if not im["src"].startswith("http"):
                continue
            stem = f"{i + 1:02d}-" + re.sub(r"[^a-z0-9]+", "-", im["src"].split("/")[-1].split("?")[0].rsplit(".", 1)[0].lower())[:40]
            try:
                pic = fetch(im["src"])
                im["src"] = save(pic, IMG / "gallery" / a["id"] / f"{stem}.jpg", 1600, 82)
                im["thumb"] = save(pic, IMG / "gallery" / a["id"] / f"{stem}-t.jpg", 600, 78)
                done += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                print("failed:", im["src"], e)
    (DATA / "gallery.json").write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s = json.loads((DATA / "site.json").read_text())
    if s.get("photo", "").startswith("http"):
        try:
            s["photo"] = save(fetch(s["photo"]), IMG / "profile.jpg", 700, 85)
            (DATA / "site.json").write_text(json.dumps(s, indent=2) + "\n")
        except Exception as e:  # noqa: BLE001
            print("portrait failed:", e)
    print(f"localized {done} images, {failed} failed")


if __name__ == "__main__":
    main()
