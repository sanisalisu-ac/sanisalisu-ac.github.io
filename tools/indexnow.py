#!/usr/bin/env python3
"""Tell Bing, Yandex, Seznam, Naver and other IndexNow search engines that the site changed.
Runs after each deployment; free, no account needed. (Google is notified through the sitemap
submitted once in Google Search Console.)"""
import json, os, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
site = json.loads((ROOT / "data" / "site.json").read_text())
base = os.environ.get("SITE_URL", site.get("url", "")).rstrip("/")
key = site.get("indexnow_key")
if not key or not base:
    raise SystemExit("IndexNow: no key or site URL; skipped")
urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "_site" / "sitemap.xml").read_text())
body = json.dumps({"host": base.split("//")[1].split("/")[0], "key": key,
                   "keyLocation": f"{base}/{key}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow:", r.status, f"({len(urls)} URLs submitted)")
except Exception as e:  # noqa: BLE001
    print("IndexNow: not accepted this time:", e)
