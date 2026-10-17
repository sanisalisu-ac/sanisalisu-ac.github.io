#!/usr/bin/env python3
"""Convert the publication list of the LaTeX CV into data/publications.json.

Usage:  python tools/cv_to_json.py path/to/Salisu_CV.tex
Existing entries in data/publications.json keep their manual fields
(pdf, preprint, code, abstract, citations, topics edits) when the DOI or title matches.
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "publications.json"

ACCENTS = {"'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308", "~": "\u0303",
           "c": "\u0327", "u": "\u0306", "v": "\u030C", "=": "\u0304", ".": "\u0307"}


def detex(s: str, keep_math=True) -> str:
    import unicodedata
    s = re.sub(r"\\([c u v])\{(\w)\}".replace(" ", ""), lambda m: unicodedata.normalize("NFC", m.group(2) + ACCENTS[m.group(1)]), s)
    s = re.sub(r"\\(['`^\"~=.])\{?(\w)\}?", lambda m: unicodedata.normalize("NFC", m.group(2) + ACCENTS[m.group(1)]), s)
    s = s.replace("---", "\u2014").replace("--", "\u2013").replace("~", " ")
    s = s.replace("\\,", " ").replace("\\ ", " ").replace("\\&", "&").replace("\\%", "%")
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    if not keep_math:
        s = s.replace("$", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


INITIALS = re.compile(r"^(?:[A-Z][a-z]?\.(?:\s|\\,)*-?\s*)+$|^[A-Z]\.\s?[A-Z]\.$")
ME = "Salisu, S."


def split_authors_title(head: str):
    head = head.replace("\\me", ME)
    toks = [t.strip() for t in head.split(", ")]
    authors, i = [], 0
    while i + 1 < len(toks) and INITIALS.match(toks[i + 1].replace("\\,", "").replace(" ", "")):
        authors.append(detex(f"{toks[i]}, {toks[i+1]}"))
        i += 2
    title = ", ".join(toks[i:]).strip().rstrip(",")
    return authors, detex(title)


TOPIC_RULES = {
    "fixed-point": r"fixed point|enriched|nonexpansive|contraction|contractive|demicontractive|pseudocontractive|proximity|cutters|krasnoselskii",
    "variational": r"variational|inclusion|equilibrium|monotone|extragradient|splitting|proximal|tseng|golden ratio",
    "optimization": r"conjugate gradient|quasi-newton|least-squares|vector optimization|nonlinear equations|gradient method|projected reflected gradient|optimization problems|minimization|riemannian optimization|portfolio",
    "geometry": r"cat\(|cat\$|hadamard|geodesic|hyperbolic|metric spaces|manifold|riemannian",
    "applications": r"supply|classification|learning|image|portfolio|robot|nash|gough|game|bibliometric|hammerstein",
}


def topics_for(title):
    t = title.lower()
    return [k for k, rx in TOPIC_RULES.items() if re.search(rx, t)]


def parse_item(raw: str):
    corr = "\\corr" in raw
    raw = raw.replace("\\corr", "")
    doi = re.search(r"\\doi\{([^}]*)\}", raw)
    links = re.findall(r"\\link\{([^}]*)\}", raw)
    ix = re.search(r"\\ix\{([^}]*)\}", raw)
    body = re.sub(r"\\(doi|link|ix)\{[^}]*\}", "", raw).strip()
    chapter = " in: \\emph{" in body or ", in:" in body
    m = re.search(r",\s*(?:in:\s*)?\\emph\{", body)
    head, tail = body[: m.start()], body[m.end() - len("\\emph{"):]
    authors, title = split_authors_title(head)
    jm = re.match(r"\\emph\{((?:[^{}]|\{[^}]*\})*)\}", tail)
    venue = detex(jm.group(1)) if jm else ""
    rest = tail[jm.end():] if jm else tail
    vol = re.search(r"\\textbf\{([^}]*)\}", rest)
    issue = re.search(r"\\textbf\{[^}]*\}\(([^)]*)\)", rest)
    year = re.search(r"\(((?:19|20)\d{2})\)", rest) or re.search(r"\b((?:19|20)\d{2})\b", rest)
    rest_clean = detex(re.sub(r"\\textbf\{[^}]*\}(\([^)]*\))?", "", rest), keep_math=False)
    rest_clean = re.sub(r"\(\d{4}\)", "", rest_clean).strip(" ,.")
    in_press = "in press" in rest_clean.lower()
    pages = None
    pm = re.search(r"(?:pp\.\s*)?(\d+\s*\u2013\s*\d+|\b\d{1,6}\b|e\d+)\s*$", rest_clean)
    if pm and not chapter:
        pages = pm.group(1).replace(" ", "")
    if chapter:
        pm = re.search(r"pp\.\s*([\d\u2013]+)", rest_clean)
        pages = pm.group(1) if pm else None
    index = quartile = jif = None
    if ix:
        parts = [p.strip() for p in ix.group(1).replace(";", ",").split(",")]
        for p in parts:
            if re.fullmatch(r"Q[1-4]", p): quartile = p
            elif p.startswith("IF"): jif = float(p.split()[1])
            elif p.upper().startswith(("SCIE", "ESCI", "ESC!", "SCOPUS")):
                index = "ESCI" if p.upper().startswith("ESC") else ("Scopus" if p.lower() == "scopus" else p)
            elif "chapter" in p.lower(): pass
    d = doi.group(1) if doi else None
    url = f"https://doi.org/{d}" if d else (links[0].strip() if links else None)
    return {
        "title": title, "authors": authors, "venue": venue,
        "volume": detex(vol.group(1)) if vol else None, "issue": detex(issue.group(1)) if issue else None,
        "pages": pages, "year": int(year.group(1)) if year else None,
        "type": "chapter" if chapter else "article", "status": "in press" if in_press else "published",
        "doi": d, "url": url, "index": index, "quartile": quartile, "impact_factor": jif,
        "first_author": bool(authors) and authors[0] == ME, "corresponding": corr,
        "topics": topics_for(title), "series": venue if chapter else None,
        "source": "cv",
    }


def slug(p):
    key = (p["authors"][0].split(",")[0] if p["authors"] else "x") + str(p["year"]) + re.sub(r"[^a-z]", "", p["title"].lower())[:24]
    return re.sub(r"[^A-Za-z0-9]", "", key).lower()


def main(tex_path):
    tex = pathlib.Path(tex_path).read_text(encoding="utf-8")
    block = tex.split("\\cvsub{Peer-Reviewed Journal Articles and Book Chapter}")[1].split("\\end{enumerate}")[0]
    block = "\n".join(l for l in block.splitlines() if not l.strip().startswith("%"))
    items = [i.strip() for i in block.split("\\item")[1:]]
    pubs = [parse_item(" ".join(i.split())) for i in items]
    old = {}
    if OUT.exists():
        for p in json.loads(OUT.read_text())["publications"]:
            old[(p.get("doi") or p["title"]).lower()] = p
    for p in pubs:
        p["id"] = slug(p)
        prev = old.get((p.get("doi") or p["title"]).lower())
        if prev:
            if prev.get("topics_override"): p["topics"] = prev["topics_override"]
            for k in ("pdf", "preprint", "code", "abstract", "citations", "openalex_citations", "topics_override", "featured", "scholar_url"):
                if k in prev: p[k] = prev[k]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"updated": None, "publications": pubs}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(pubs)} publications to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Salisu_CV.tex")
