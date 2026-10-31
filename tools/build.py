#!/usr/bin/env python3
"""Build the static site into _site/.

    pip install jinja2
    python tools/build.py            # builds _site/
    python -m http.server -d _site   # preview at http://localhost:8000

Everything the site shows comes from data/*.json and templates/*.html.
"""
import datetime as dt, html, json, os, pathlib, re, shutil
from email.utils import format_datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


SITE = load("site")
SITE_URL = os.environ.get("SITE_URL", SITE.get("url", "")).rstrip("/")
ME = "Salisu, S."

TOPICS = {
    "fixed-point": ("Fixed point theory",
                    "Existence and uniqueness of fixed points, and the structure of the operators behind them: enriched, "
                    "averaged, demicontractive and multivalued mappings, studied through geodesic perturbation techniques."),
    "variational": ("Variational inequalities and monotone inclusions",
                    "Extragradient, Tseng-type, golden-ratio, reflected and splitting methods, with inertial, relaxed and "
                    "adaptive step rules, for monotone, pseudo-monotone and non-monotone problems."),
    "optimization": ("Numerical optimization",
                     "Conjugate-gradient, spectral and quasi-Newton methods for smooth, vector and Riemannian optimization, "
                     "and derivative-light methods for nonlinear equations."),
    "geometry": ("Nonlinear and geodesic settings",
                 "Carrying convex analysis beyond linear spaces: CAT(0) and Hadamard spaces, hyperbolic spaces and "
                 "Riemannian manifolds, where projections, midpoints and inequalities must be rebuilt from geometry."),
    "applications": ("Applications",
                     "Blood supply-chain networks, extreme learning machines for classification, image restoration, robot "
                     "manipulators, portfolio selection and Nash equilibria in oligopolistic markets."),
}


def initials_first(a):
    if "," not in a:
        return a
    sur, ini = [x.strip() for x in a.split(",", 1)]
    return f"{ini} {sur}"


def tex_to_html_title(t):
    """Keep $...$ for KaTeX; escape the rest."""
    return html.escape(t, quote=False)


def plain(t):
    return re.sub(r"[${}\\_^]", "", t)


def bibtex(p):
    key = re.sub(r"[^A-Za-z]", "", p["authors"][0].split(",")[0]) + str(p.get("year") or "") + \
        re.sub(r"[^a-z]", "", (p["title"].split() or ["x"])[0].lower())
    kind = "incollection" if p.get("type") == "chapter" else "article"
    f = {"author": " and ".join(p["authors"]), "title": "{" + p["title"] + "}"}
    if kind == "article":
        f["journal"] = p.get("venue")
    else:
        f["booktitle"] = p.get("venue")
        f["series"] = "Lecture Notes in Computer Science"
    for k_src, k in (("volume", "volume"), ("issue", "number"), ("pages", "pages"), ("year", "year"), ("doi", "doi")):
        if p.get(k_src):
            f[k] = str(p[k_src]).replace("–", "--")
    if not p.get("doi") and p.get("url"):
        f["url"] = p["url"]
    if p.get("status") == "in press":
        f["note"] = "In press"
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f.items() if v)
    return f"@{kind}{{{key},\n{body}\n}}"


def prepare_pubs():
    data = load("publications")
    pubs = sorted(data["publications"], key=lambda p: -(p.get("year") or 0))  # stable: keeps CV order within a year
    today = dt.date.today()
    n = len(pubs)
    for i, p in enumerate(pubs):
        p["num"] = n - i
        p["authors_html"] = ", ".join(
            f'<span class="me">{html.escape(initials_first(a))}</span>' if a == ME else html.escape(initials_first(a))
            for a in p["authors"])
        p["title_html"] = tex_to_html_title(p["title"])
        p["plain_title"] = plain(p["title"])
        bits = []
        if p.get("volume"):
            bits.append(f"<b>{html.escape(str(p['volume']))}</b>" + (f"({html.escape(str(p['issue']))})" if p.get("issue") else ""))
        if p.get("pages"):
            bits.append(("pp. " if p.get("type") == "chapter" else "") + html.escape(str(p["pages"])))
        p["venue_html"] = f"<em>{html.escape(p.get('venue') or '')}</em>" + (" " + ", ".join(bits) if bits else "") + \
            (f" ({p['year']})" if p.get("year") else "") + (", in press" if p.get("status") == "in press" else "")
        if p.get("type") == "chapter":
            p["venue_html"] = "In " + p["venue_html"] + ", Lecture Notes in Computer Science, Springer"
        p["is_q1"] = p.get("quartile") == "Q1"
        p["role"] = "first" if p.get("first_author") else ("corresponding" if p.get("corresponding") else "")
        added = p.get("added")
        p["is_new"] = bool(added) and (today - dt.date.fromisoformat(added)).days <= 90
        p["search"] = " ".join([p["plain_title"], " ".join(p["authors"]), p.get("venue") or "", str(p.get("year") or ""),
                                p.get("doi") or ""]).lower()
        p["bib"] = bibtex(p)
        p["scholar"] = "https://scholar.google.com/scholar?q=" + re.sub(r"\s+", "+", p["plain_title"])
    years = sorted({p["year"] for p in pubs if p.get("year")}, reverse=True)
    groups = [(y, [p for p in pubs if p.get("year") == y]) for y in years]
    return data, pubs, groups


def main():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    data, pubs, groups = prepare_pubs()
    metrics = load("metrics")
    try:
        metrics["updated_label"] = dt.date.fromisoformat(metrics["updated"]).strftime("%-d %B %Y")
    except (KeyError, ValueError):
        metrics["updated_label"] = metrics.get("updated", "")
    talks = load("talks")
    gallery = load("gallery")
    news = load("news")["news"]

    by_year = {}
    for p in pubs:
        by_year[p["year"]] = by_year.get(p["year"], 0) + 1
    yrs = sorted(by_year)
    peak = max(by_year.values())
    yearbars = [{"year": y, "n": by_year[y], "pct": round(100 * by_year[y] / peak)} for y in yrs]

    topics = []
    for key, (label, blurb) in TOPICS.items():
        members = [p for p in pubs if key in p["topics"]]
        lead = [p for p in members if p["role"]][:3] or members[:3]
        topics.append({"key": key, "label": label, "blurb": blurb, "count": len(members), "examples": lead})

    peer = [p for p in pubs if p.get("status") != "preprint"]  # same counting rule as the CV (tools/make_cv.py)
    stats = {
        "total": len(peer),
        "q1": sum(p["is_q1"] for p in peer),
        "lead": sum(bool(p["role"]) for p in peer),
        "first_year": min(yrs), "last_year": max(yrs),
        "talks": len(talks["talks"]),
        "coauthors": len({a for p in pubs for a in p["authors"] if a != ME}),
    }
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
    for a in gallery["albums"]:
        d = a["date"]
        a["year_label"] = d[:4] if len(d) == 10 else d.replace("-", "–")
        a["date_label"] = a.get("date_label") or (f"{int(d[8:])} {months[int(d[5:7]) - 1]} {d[:4]}" if len(d) == 10 else a["year_label"])
        for j, im in enumerate(a["images"]):
            src = im["src"]
            ext = src.startswith("http")
            im["thumb"] = im.get("thumb") or (src + "?w=600" if ext and "wordpress.com" in src else src)
            im["full"] = src + "?w=1600" if ext and "wordpress.com" in src else src
            im["alt"] = im.get("alt") or f"{a['title']}, photograph {j + 1} of {len(a['images'])}"

    external = {re.match(r"https://[^/]+", u).group(0) for u in
                [im["src"] for a in gallery["albums"] for im in a["images"]] + [SITE.get("photo", "")]
                if u.startswith("https://")}
    img_src = " ".join(sorted(external))
    now = dt.datetime.now(dt.timezone.utc)
    ctx = dict(img_src=img_src, site=SITE, site_url=SITE_URL, pubs=pubs, groups=groups, stats=stats, metrics=metrics, talks=talks,
               gallery=gallery, news=news, topics=topics, topic_labels={k: v[0] for k, v in TOPICS.items()},
               yearbars=yearbars, recent=pubs[:6], updated=data.get("updated"), build_date=now.strftime("%d %B %Y"),
               year=now.year)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    pages = ["index", "research", "publications", "talks", "teaching", "code", "gallery", "cv", "contact", "404"]
    for name in pages:
        html_out = env.get_template(f"{name}.html").render(page=name, **ctx)
        (OUT / f"{name}.html").write_text(html_out, encoding="utf-8")

    shutil.copytree(ROOT / "assets", OUT / "assets")
    shutil.copytree(DATA, OUT / "data")
    for extra in ("CNAME",):
        if (ROOT / extra).exists():
            shutil.copy(ROOT / extra, OUT / extra)
    (OUT / ".nojekyll").write_text("")
    (OUT / "data" / "bibtex.json").write_text(json.dumps({p["id"]: p["bib"] for p in pubs}, ensure_ascii=False), encoding="utf-8")

    # downloads: BibTeX, RSS, sitemap, robots
    (OUT / "publications.bib").write_text("\n\n".join(p["bib"] for p in pubs) + "\n", encoding="utf-8")
    items = []
    for p in pubs[:30]:
        link = p.get("url") or f"{SITE_URL}/publications.html"
        items.append(f"<item><title>{html.escape(p['plain_title'])}</title><link>{html.escape(link)}</link>"
                     f"<guid isPermaLink=\"false\">{html.escape(p['id'])}</guid>"
                     f"<description>{html.escape(', '.join(initials_first(a) for a in p['authors']) + '. ' + (p.get('venue') or '') + ' ' + str(p.get('year') or ''))}</description></item>")
    (OUT / "feed.xml").write_text(
        f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<rss version=\"2.0\"><channel><title>Sani Salisu: publications</title>"
        f"<link>{SITE_URL}/publications.html</link><description>New papers by Sani Salisu</description>"
        f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>{''.join(items)}</channel></rss>\n", encoding="utf-8")
    urls = "".join(f"<url><loc>{SITE_URL}/{'' if n == 'index' else n + '.html'}</loc><lastmod>{now.date()}</lastmod></url>"
                   for n in pages if n != "404")
    (OUT / "sitemap.xml").write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">{urls}</urlset>\n")
    if SITE.get("indexnow_key"):
        (OUT / f"{SITE['indexnow_key']}.txt").write_text(SITE["indexnow_key"])
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"built {len(pages)} pages, {len(pubs)} publications -> {OUT}")


if __name__ == "__main__":
    main()
