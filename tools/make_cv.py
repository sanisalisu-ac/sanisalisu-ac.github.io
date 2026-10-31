#!/usr/bin/env python3
"""Generate the data-driven parts of the CV from the site's data files.

Writes three files that cv/Salisu_CV.tex \\input's:
  cv/generated/metrics.tex       - \\newcommand macros: Scholar figures, publication counts, talk count, update date
  cv/generated/publications.tex  - the numbered list of peer-reviewed publications (from data/publications.json)
  cv/generated/talks.tex         - talks and workshops (from data/talks.json)

So the CV never needs hand-editing for new papers, citation figures or talks: the workflow refreshes the data,
runs this script and compiles the PDF. Everything else in the CV (appointments, grants, referees ...) is edited
directly in cv/Salisu_CV.tex.

Run locally:  python tools/make_cv.py   then   cd cv && pdflatex Salisu_CV.tex
"""
import datetime as dt, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "cv" / "generated"
ME = "Salisu, S."
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]

ACCENTS = {"á": r"\'a", "é": r"\'e", "í": r"\'i", "ó": r"\'o", "ú": r"\'u", "à": r"\`a", "è": r"\`e",
           "ä": r"\"a", "ö": r"\"o", "ü": r"\"u", "ç": r"\c{c}", "ș": r"\c{s}", "ş": r"\c{s}", "ț": r"\c{t}",
           "ţ": r"\c{t}", "ă": r"\u{a}", "â": r"\^a", "î": r"\^i", "ñ": r"\~n", "ł": r"{\l}", "ń": r"\'n",
           "ś": r"\'s", "ż": r"\.z", "ź": r"\'z", "Ș": r"\c{S}", "Ş": r"\c{S}", "–": "--", "—": "---",
           "’": "'", "‘": "`", "“": "``", "”": "''", " ": "~"}


def tex(s):
    """Escape plain text for LaTeX, leaving $...$ math untouched."""
    out = []
    for i, part in enumerate(re.split(r"(\$[^$]*\$)", str(s or ""))):
        if i % 2:
            out.append(part)
            continue
        part = re.sub(r"([&%#_])", r"\\\1", part)
        part = "".join(ACCENTS.get(c, c) for c in part)
        out.append(part)
    return "".join(out)


def abbrev(s):
    """Journal abbreviations: 'J. Optim.' -> 'J.\\ Optim.' so LaTeX does not add sentence spacing."""
    return re.sub(r"\.(?= )", r".\\", tex(s))


def author(a):
    if a == ME:
        return r"\me"
    a = re.sub(r"\.\s(?=[A-Z]\.)", r".\\,", tex(a))  # 'M. S.' -> 'M.\,S.'
    return a


def index_tag(p):
    if p.get("type") == "chapter":
        return r"\ix{Book chapter" + (f"; {p['index']}" if p.get("index") else "") + "}"
    bits = [b for b in (p.get("index"), p.get("quartile")) if b]
    if p.get("impact_factor"):
        bits.append(f"IF {p['impact_factor']}")
    return r"\ix{" + ", ".join(bits) + "}" if bits else ""


def link(p):
    if p.get("doi"):
        return r"\doi{" + p["doi"] + "}"
    if p.get("url"):
        return r"\link{" + p["url"].replace("%", r"\%").replace("#", r"\#") + "}"
    return ""


def pub_item(p):
    authors = ", ".join(author(a) for a in p["authors"])
    title = tex(p["title"]).rstrip(".")
    if p.get("type") == "chapter":
        src = r"in \emph{" + tex(p.get("venue")) + "}"
        if p.get("series"):
            src += ", " + tex(p["series"]) + (r", vol.~" + tex(p["series_volume"]) if p.get("series_volume") else "")
        if p.get("publisher"):
            src += ", " + tex(p["publisher"])
        src += f", {p.get('series_year') or p.get('year')}"
        if p.get("pages"):
            src += r", pp.~" + tex(p["pages"])
    else:
        src = r"\emph{" + abbrev(p.get("venue")) + "}"
        if p.get("volume"):
            src += r" \textbf{" + tex(p["volume"]) + "}" + (f"({tex(p['issue'])})" if p.get("issue") else "")
        src += f" ({p.get('year')})"
        if p.get("pages"):
            src += ", " + tex(p["pages"])
        if p.get("status") == "in press":
            src += ", in press"
    tail = " ".join(x for x in (link(p), index_tag(p), r"\corr" if p.get("corresponding") else "") if x)
    return f"\\item {authors}, {title}, {src}. {tail}".rstrip()


def counts_as_peer_reviewed(p):
    """Rule shared by the CV and the site's counts. Preprints never count. Items that so far exist only on Google
    Scholar (no DOI yet, e.g. conference abstracts or submitted work) count once ORCID/Crossref supply a DOI, or
    when "peer_reviewed": true is set on the entry in data/publications.json."""
    if p.get("peer_reviewed") is not None:
        return bool(p["peer_reviewed"])
    if p.get("status") == "preprint":
        return False
    return not (p.get("source") == "scholar" and not p.get("doi"))


def peer_reviewed(pubs):
    pubs = [p for p in pubs if counts_as_peer_reviewed(p)]
    # newest first; "in press" papers before published ones of the same year; otherwise keep the file's order
    order = {id(p): i for i, p in enumerate(pubs)}
    return sorted(pubs, key=lambda p: (-(p.get("year") or 0), p.get("status") != "in press", order[id(p)]))


def date_label(iso):
    try:
        d = dt.date.fromisoformat(iso)
        m = MONTHS[d.month - 1]
        sep = "\\ " if m.endswith(".") else " "
        return f"{d.day} {m}{sep}{d.year}"
    except (TypeError, ValueError):
        return tex(iso or "")


def talk_item(t, workshop=False):
    when = abbrev(t.get("when") or t.get("date"))
    event = tex(t["event"])
    if t.get("url"):
        event = r"\href{" + t["url"].replace("%", r"\%").replace("#", r"\#") + "}{" + event + "}"
    if workshop:
        return f"\\item {event}, {tex(t.get('place'))}, {when}."
    note = (t.get("note") or "").strip()
    extra, award = "", ""
    if note:
        if "award" in note.lower():
            award = r" --- \textbf{" + tex(note) + "}"
        else:
            extra = f" ({tex(note[0].lower() + note[1:]).replace('P. ', 'P.~')})"
    return f"\\item \\emph{{{tex(t['title'])}}}{extra}. {event}, {tex(t.get('place'))}, {when}{award}."


def main():
    pdata = json.loads((DATA / "publications.json").read_text(encoding="utf-8"))
    metrics = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    talks = json.loads((DATA / "talks.json").read_text(encoding="utf-8"))
    pubs = peer_reviewed(pdata["publications"])
    years = [p["year"] for p in pubs if p.get("year")]
    OUT.mkdir(parents=True, exist_ok=True)

    macros = {
        "scholarcitations": metrics.get("citations"),
        "scholarh": metrics.get("h_index"),
        "scholarten": metrics.get("i10_index"),
        "scholardate": date_label(metrics.get("updated")),
        "npubs": len(pubs),
        "nqone": sum(p.get("quartile") == "Q1" for p in pubs),
        "nlead": sum(bool(p.get("first_author") or p.get("corresponding")) for p in pubs),
        "firstyear": min(years), "lastyear": max(years),
        "ntalks": len(talks["talks"]),
        # the date the CV's content last changed (new data), so the file is not rewritten every day for nothing
        "cvupdated": date_label(max(d for d in (pdata.get("updated"), metrics.get("updated"),
                                                (metrics.get("openalex") or {}).get("updated")) if d)),
    }
    lines = ["% Generated by tools/make_cv.py from data/*.json -- do not edit by hand."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
    (OUT / "metrics.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    body = ["% Generated by tools/make_cv.py from data/publications.json -- do not edit by hand.",
            r"\begin{enumerate}"]
    year = None
    for p in pubs:
        if p.get("year") != year:
            year = p.get("year")
            body.append(f"%% ---- {year}")
        body.append(pub_item(p))
    body.append(r"\end{enumerate}")
    (OUT / "publications.tex").write_text("\n".join(body) + "\n", encoding="utf-8")

    t = ["% Generated by tools/make_cv.py from data/talks.json -- do not edit by hand.",
         r"\begin{enumerate}[label={[T\arabic*]}]"] + [talk_item(x) for x in sorted(talks["talks"], key=lambda x: str(x.get("date") or ""), reverse=True)] + [r"\end{enumerate}"]
    if talks.get("workshops"):
        t += [r"\cvsub{Other Workshops Attended}", r"\begin{itemize}"] + \
             [talk_item(x, workshop=True) for x in talks["workshops"]] + [r"\end{itemize}"]
    (OUT / "talks.tex").write_text("\n".join(t) + "\n", encoding="utf-8")
    print(f"[cv] {len(pubs)} publications, {macros['ntalks']} talks, Scholar {macros['scholarcitations']} citations "
          f"({macros['scholardate']})")


if __name__ == "__main__":
    main()
