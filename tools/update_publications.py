#!/usr/bin/env python3
"""Weekly refresh of data/publications.json and data/metrics.json.

Sources (each optional; a failing source is skipped and nothing is ever deleted):
  1. ORCID public API        - finds new works (DOIs) on the ORCID record.
  2. Crossref                - full metadata for new DOIs; completes "in press" entries.
  3. OpenAlex                - citation counts per DOI and author-level totals (free, no key).
  4. Google Scholar          - profile citations, h-index, i10-index and per-paper counts, tried in this order:
       * SerpApi's Google Scholar Author API, when the SERPAPI_KEY secret is set (reliable; free plan suffices);
       * the public profile page read directly (works when Google does not block the server);
       * the `scholarly` package (last resort).
     Figures typed into the manual run form (SCHOLAR_CITATIONS / SCHOLAR_H / SCHOLAR_I10) override all of these.

If Google Scholar could not be read for more than STALE_DAYS days, a file .scholar-stale is written so the
workflow can raise a warning and open a GitHub issue (which e-mails the site owner).

Run locally:  python tools/update_publications.py [--dry-run]
"""
import argparse, datetime as dt, difflib, json, os, pathlib, re, sys, time
import urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "tools"))
from cv_to_json import topics_for, slug  # noqa: E402

SITE = json.loads((DATA / "site.json").read_text())
ORCID = SITE["orcid"]
SCHOLAR_ID = SITE["scholar_id"]
CONTACT = SITE.get("api_contact_email", "")
UA = "academic-site-updater/1.0" + (f" (mailto:{CONTACT})" if CONTACT else "")
ME_SURNAME = "salisu"
TODAY = dt.date.today().isoformat()
STALE_DAYS = 3
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")
PREPRINT_DOI = ("10.22541/", "10.21203/", "10.48550/", "10.2139/", "10.20944/", "10.31219/")


def log(*a):
    print("[update]", *a, flush=True)


def get_json(url, headers=None, tries=3):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            log(f"retry {url[:80]}: {e}")
            time.sleep(2 * (i + 1))


def norm_title(t):
    t = re.sub(r"<[^>]+>|\$|\\[a-zA-Z]+|[{}]", " ", t or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def similar(a, b):
    return difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def find(pubs, doi=None, title=None, cutoff=0.9):
    if doi:
        for p in pubs:
            if (p.get("doi") or "").lower() == doi.lower():
                return p
    if title:
        best, score = None, 0
        for p in pubs:
            s = similar(p["title"], title)
            if s > score:
                best, score = p, s
        if score >= cutoff:
            return best
    return None


# ---------------------------------------------------------------- ORCID
def orcid_works():
    d = get_json(f"https://pub.orcid.org/v3.0/{ORCID}/works")
    out = []
    for g in d.get("group", []):
        s = g["work-summary"][0]
        ids = (s.get("external-ids") or {}).get("external-id") or []
        doi = next((i["external-id-value"] for i in ids if i.get("external-id-type") == "doi"), None)
        year = ((s.get("publication-date") or {}).get("year") or {}).get("value")
        out.append({"title": s["title"]["title"]["value"], "doi": doi.strip().lower() if doi else None,
                    "year": int(year) if year else None, "type": s.get("type")})
    return out


# ---------------------------------------------------------------- Crossref
def initials(given):
    parts = re.split(r"([\s-])", given or "")
    out = ""
    for p in parts:
        if p == "-":
            out = out.rstrip() + "-"
        elif p.strip():
            out += p[0].upper() + ". "
    return out.strip()


def crossref(doi):
    m = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
    authors = []
    for a in m.get("author", []):
        fam = a.get("family") or a.get("name") or ""
        authors.append(f"{fam}, {initials(a.get('given', ''))}".strip(", "))
    authors = ["Salisu, S." if a.lower().startswith(ME_SURNAME + ",") and a.split(",")[1].strip().startswith("S") else a
               for a in authors]
    date = (m.get("published-print") or m.get("issued") or m.get("published-online") or {}).get("date-parts", [[None]])[0]
    venue = (m.get("short-container-title") or m.get("container-title") or [""])[0]
    title = re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0]).strip()
    kind = "chapter" if m.get("type") in ("book-chapter", "proceedings-article") else "article"
    pages = m.get("page") or m.get("article-number")
    preprint = m.get("type") == "posted-content" or doi.lower().startswith(PREPRINT_DOI)
    if preprint and not venue:
        venue = ((m.get("institution") or [{}])[0].get("name") or m.get("publisher") or "Preprint")
    return {
        "title": title, "authors": authors, "venue": venue, "volume": m.get("volume"), "issue": m.get("issue"),
        "pages": pages.replace("-", "–") if pages else None, "year": date[0] if date else None,
        "type": kind, "status": "preprint" if preprint else ("published" if m.get("volume") or kind == "chapter" else "in press"),
        "doi": doi.lower(), "url": f"https://doi.org/{doi}", "index": None, "quartile": None, "impact_factor": None,
        "first_author": bool(authors) and authors[0] == "Salisu, S.", "corresponding": False,
        "topics": topics_for(title), "series": venue if kind == "chapter" else None,
    }


# ---------------------------------------------------------------- OpenAlex
def openalex(pubs, metrics):
    dois = [p["doi"] for p in pubs if p.get("doi")]
    counts = {}
    for i in range(0, len(dois), 50):
        chunk = "|".join("https://doi.org/" + d for d in dois[i:i + 50])
        d = get_json("https://api.openalex.org/works?per-page=50&select=doi,cited_by_count&filter=doi:" + urllib.parse.quote(chunk, safe=":/|"))
        for w in d.get("results", []):
            counts[(w.get("doi") or "").replace("https://doi.org/", "").lower()] = w.get("cited_by_count", 0)
    for p in pubs:
        if p.get("doi") and p["doi"].lower() in counts:
            p["openalex_citations"] = counts[p["doi"].lower()]
    try:
        a = get_json(f"https://api.openalex.org/authors/orcid:{ORCID}")
        metrics["openalex"] = {"citations": a.get("cited_by_count"), "h_index": (a.get("summary_stats") or {}).get("h_index"),
                               "i10_index": (a.get("summary_stats") or {}).get("i10_index"), "updated": TODAY}
    except Exception as e:  # noqa: BLE001
        log("OpenAlex author lookup skipped:", e)
    log(f"OpenAlex: citation counts for {len(counts)} DOIs")


# ---------------------------------------------------------------- Google Scholar
def scholar_serpapi(key):
    arts, start = [], 0
    while True:
        q = urllib.parse.urlencode({"engine": "google_scholar_author", "author_id": SCHOLAR_ID, "api_key": key,
                                    "num": 100, "start": start, "sort": "pubdate"})
        d = get_json("https://serpapi.com/search.json?" + q)
        if start == 0:
            table = (d.get("cited_by") or {}).get("table", [])
            vals = {k: v.get("all") for row in table for k, v in row.items()}
            totals = {"citations": vals.get("citations"), "h_index": vals.get("h_index"), "i10_index": vals.get("i10_index")}
        page = d.get("articles", [])
        arts += [{"title": a.get("title"), "year": int(a["year"]) if str(a.get("year", "")).isdigit() else None,
                  "venue": a.get("publication"), "authors": a.get("authors"), "link": a.get("link"),
                  "citations": (a.get("cited_by") or {}).get("value") or 0} for a in page]
        if len(page) < 100 or start > 400:
            return totals, arts
        start += 100


def scholar_direct():
    """Read the public Scholar profile page (100 papers per page)."""
    from bs4 import BeautifulSoup  # imported lazily
    totals, arts, start = None, [], 0
    while True:
        url = (f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en&cstart={start}&pagesize=100"
               "&view_op=list_works&sortby=pubdate")
        req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = r.read().decode("utf-8", "replace")
        soup = BeautifulSoup(page, "html.parser")
        if totals is None:
            cells = [c.get_text(strip=True) for c in soup.select("td.gsc_rsb_std")]
            if len(cells) < 6 or not cells[0].isdigit():
                raise RuntimeError("Scholar returned no profile (blocked or CAPTCHA)")
            totals = {"citations": int(cells[0]), "h_index": int(cells[2]), "i10_index": int(cells[4])}
        rows = soup.select("tr.gsc_a_tr")
        for tr in rows:
            a = tr.select_one("a.gsc_a_at")
            if not a:
                continue
            c = tr.select_one("a.gsc_a_ac")
            y = tr.select_one("span.gsc_a_h")
            grey = tr.select("div.gs_gray")
            arts.append({"title": a.get_text(strip=True),
                         "year": int(y.get_text(strip=True)) if y and y.get_text(strip=True).isdigit() else None,
                         "venue": grey[1].get_text(strip=True) if len(grey) > 1 else None,
                         "authors": grey[0].get_text(strip=True) if grey else None,
                         "link": "https://scholar.google.com" + a.get("href", ""),
                         "citations": int(c.get_text(strip=True)) if c and c.get_text(strip=True).isdigit() else 0})
        if len(rows) < 100 or start > 400:
            return totals, arts
        start += 100
        time.sleep(3)


def scholar_manual():
    vals = {k: os.environ.get(e, "").strip() for k, e in
            (("citations", "SCHOLAR_CITATIONS"), ("h_index", "SCHOLAR_H"), ("i10_index", "SCHOLAR_I10"))}
    vals = {k: int(v) for k, v in vals.items() if v.isdigit()}
    return vals if "citations" in vals else None


def scholar_scholarly():
    from scholarly import scholarly  # imported lazily: optional dependency
    a = scholarly.fill(scholarly.search_author_id(SCHOLAR_ID), sections=["basics", "indices", "publications"])
    totals = {"citations": a.get("citedby"), "h_index": a.get("hindex"), "i10_index": a.get("i10index")}
    arts = [{"title": p["bib"].get("title"), "year": int(p["bib"]["pub_year"]) if str(p["bib"].get("pub_year", "")).isdigit() else None,
             "venue": p["bib"].get("citation"), "authors": None,
             "link": f"https://scholar.google.com/citations?view_op=view_citation&citation_for_view={p.get('author_pub_id')}",
             "citations": p.get("num_citations", 0)} for p in a.get("publications", [])]
    return totals, arts


def scholar(pubs, metrics, add_new):
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if os.environ.get("GITHUB_EVENT_NAME") == "push" and metrics.get("updated") == TODAY and not scholar_manual():
        log("Google Scholar already read today; skipped on this edit to save SerpApi searches")
        return 0
    methods = ([("SerpApi", lambda: scholar_serpapi(key))] if key else []) + \
              [("profile page", scholar_direct), ("scholarly", scholar_scholarly)]
    totals, arts = None, []
    for name, fn in methods:
        try:
            totals, arts = fn()
            if totals and totals.get("citations") is not None:
                log(f"Google Scholar read via {name}")
                metrics["scholar_method"] = name
                break
            totals = None
        except Exception as e:  # noqa: BLE001
            log(f"Google Scholar via {name} failed:", repr(e)[:200])
    manual = scholar_manual()
    if manual:
        log("Google Scholar figures entered by hand:", manual)
        metrics["scholar_method"] = "entered by hand"
        totals = {**(totals or {}), **manual}
    if not totals:
        log("Google Scholar skipped (kept previous figures)")
        return 0
    if totals.get("citations") is not None:
        metrics.update({k: v for k, v in totals.items() if v is not None})
        metrics["source"] = "Google Scholar"
        metrics["updated"] = TODAY
    added = 0
    for a in arts:
        if not a["title"]:
            continue
        p = find(pubs, title=a["title"], cutoff=0.88)
        if p:
            p["citations"] = a["citations"]
            p.setdefault("scholar_url", a["link"])
        elif add_new and a.get("year") and a["year"] >= dt.date.today().year - 1:
            # A recent Scholar item with no DOI match: add it so it appears at once; ORCID/Crossref complete it later.
            authors = [x.strip() for x in (a.get("authors") or "").split(",") if x.strip()]
            authors = [("Salisu, S." if x.lower().endswith(ME_SURNAME) else
                        (x.split()[-1] + ", " + " ".join(w[0] + "." for w in x.split()[:-1])).strip(", ")) for x in authors]
            entry = {"title": a["title"], "authors": authors or ["Salisu, S."], "venue": (a.get("venue") or "").split(",")[0],
                     "volume": None, "issue": None, "pages": None, "year": a["year"], "type": "article",
                     "status": "preprint" if not (a.get("venue") or "").strip() or
                               re.search(r"arxiv|preprint|ssrn|researchsquare|authorea", (a.get("venue") or "").lower())
                               else "published",
                     "doi": None, "url": a["link"], "index": None, "quartile": None,
                     "impact_factor": None, "first_author": bool(authors) and authors[0] == "Salisu, S.",
                     "corresponding": False, "topics": topics_for(a["title"]), "series": None,
                     "citations": a["citations"], "source": "scholar", "added": TODAY}
            entry["id"] = slug(entry)
            pubs.insert(0, entry)
            added += 1
            log("added from Scholar:", a["title"][:90])
    log(f"Scholar: totals {totals}, matched {len(arts) - added} items, added {added}")
    return added


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-scholar-additions", action="store_true", help="only refresh Scholar counts, never add items")
    args = ap.parse_args()

    pdata = json.loads((DATA / "publications.json").read_text())
    pubs = pdata["publications"]
    metrics = json.loads((DATA / "metrics.json").read_text())
    before = json.dumps(pdata, sort_keys=True), json.dumps(metrics, sort_keys=True)

    # 1-2. ORCID -> new DOIs -> Crossref
    try:
        works = orcid_works()
        log(f"ORCID: {len(works)} works on record")
        for w in works:
            hit = find(pubs, doi=w["doi"], title=w["title"])
            if hit:
                if w["doi"] and not hit.get("doi"):  # e.g. an item first picked up from Scholar
                    try:
                        c = crossref(w["doi"])
                        for k in ("venue", "volume", "issue", "pages", "year", "doi", "url", "type", "status", "authors"):
                            if c.get(k):
                                hit[k] = c[k]
                        log("completed with DOI:", hit["title"][:80])
                    except Exception as e:  # noqa: BLE001
                        log("Crossref failed for", w["doi"], e)
                continue
            if not w["doi"]:
                log("ORCID work without DOI skipped:", w["title"][:80])
                continue
            try:
                entry = crossref(w["doi"])
            except Exception as e:  # noqa: BLE001
                log("Crossref failed for", w["doi"], e)
                continue
            if not any(a.split(",")[0].lower() == ME_SURNAME for a in entry["authors"]):
                log("skipped (author not found in Crossref record):", w["doi"])
                continue
            entry.update({"source": "orcid", "added": TODAY})
            entry["id"] = slug(entry)
            pubs.insert(0, entry)
            log("added from ORCID/Crossref:", entry["title"][:90])
    except Exception as e:  # noqa: BLE001
        log("ORCID skipped:", e)

    # complete entries that were in press
    for p in pubs:
        if p.get("doi") and p.get("status") != "preprint" and (p.get("status") == "in press" or not p.get("volume")) \
                and p.get("type") != "chapter":
            try:
                c = crossref(p["doi"])
                if c.get("volume"):
                    for k in ("volume", "issue", "pages", "year"):
                        if c.get(k):
                            p[k] = c[k]
                    p["status"] = "published"
                    log("now published:", p["title"][:80])
            except Exception as e:  # noqa: BLE001
                log("Crossref refresh failed for", p["doi"], e)

    # 3. OpenAlex
    try:
        openalex(pubs, metrics)
    except Exception as e:  # noqa: BLE001
        log("OpenAlex skipped:", e)

    # 4. Google Scholar
    scholar(pubs, metrics, add_new=not args.no_scholar_additions)

    pdata["publications"] = pubs
    changed = (json.dumps(pdata, sort_keys=True), json.dumps(metrics, sort_keys=True)) != before
    if changed:
        pdata["updated"] = TODAY
    try:
        age = (dt.date.today() - dt.date.fromisoformat(metrics.get("updated", "2000-01-01"))).days
    except ValueError:
        age = 999
    stale = ROOT / ".scholar-stale"
    if age > STALE_DAYS:
        stale.write_text(f"{age}\n")
        log(f"WARNING: Google Scholar figures are {age} days old")
    elif stale.exists():
        stale.unlink()
    if args.dry_run:
        log("dry run: changes", "found" if changed else "none")
        return
    (DATA / "publications.json").write_text(json.dumps(pdata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (DATA / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log("done:", "data changed" if changed else "no changes")


if __name__ == "__main__":
    main()
