# Sani Salisu — academic website

A fast, secure, self-updating academic site, hosted free on GitHub Pages.

- **Pages:** Home, Research, Publications, Talks, Teaching, Code & examples, Gallery, CV, Contact.
- **Publications** are searchable and filterable (topic, Q1, first/corresponding author), each with DOI,
  one-click BibTeX, a **Request PDF** form and a Google Scholar link. Full BibTeX and an RSS feed are generated.
- **Auto-updates every Monday:** new papers are pulled from ORCID + Crossref, "in press" papers are completed
  when they get a volume, citation counts come from OpenAlex and Google Scholar. No manual work.
- **Security:** no server, no database, no third-party scripts or fonts (KaTeX and fonts are self-hosted),
  a strict Content-Security-Policy, email addresses hidden from harvesters, spam honeypots on forms,
  HTTPS enforced by GitHub, Dependabot keeping the build tools patched.
- **Cost:** nothing. GitHub Pages and GitHub Actions are free for public repositories.

---

## 1. Put it online (about 10 minutes, once)

1. Create a free account at <https://github.com> (turn on two-factor authentication under
   *Settings → Password and authentication*).
2. Create a **new public repository** named exactly **`sanisalisu-ac.github.io`**
   (replace with your GitHub username). This gives the address `https://sanisalisu-ac.github.io`.
3. Upload the contents of this folder: on the new repository page choose **uploading an existing file**,
   drag in *everything inside this folder* (including the hidden `.github` folder; on macOS press
   Cmd+Shift+. in Finder to show it), and click **Commit changes**.
   If you use Git: `git init && git add . && git commit -m "Site" && git branch -M main &&
   git remote add origin https://github.com/sanisalisu-ac/sanisalisu-ac.github.io.git && git push -u origin main`.
4. In the repository go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
5. Go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**
   (lets the weekly update save new papers).
6. Open the **Actions** tab, select **Build and deploy site**, click **Run workflow** and run it. After 3–4 minutes your site is live. This first run also copies all
   gallery photos and your portrait off WordPress, so the old site can be retired.
7. Edit `data/site.json`: set `"url"` to your address and `"github_user"` to your username.

### Optional extras

| Want | Do this |
|---|---|
| Requests and messages delivered straight to your inbox (instead of opening the visitor's mail app) | Create a free form at <https://formspree.io> (50 submissions/month free), copy its ID (the part after `/f/`) into `"formspree_id"` in `data/site.json`. |
| Reliable Google Scholar numbers every week | Google Scholar blocks most cloud servers. Create a free key at <https://serpapi.com> (free plan: 100 searches/month; the site uses about 5), then add it under **Settings → Secrets and variables → Actions → New repository secret** with the name `SERPAPI_KEY`. Without it the site still tries Scholar and always updates OpenAlex. |
| Your own domain (e.g. `sanisalisu.com`) | Buy the domain, add a file `CNAME` containing just the domain, and follow GitHub's custom-domain guide. Tick **Enforce HTTPS**. |
| Google Search indexing | Add the site in Google Search Console and submit `sitemap.xml`. |
| New papers appear automatically | Keep your **ORCID** record current. Easiest: in ORCID, *Works → Add → Search & link → Crossref Metadata Search* and allow Crossref to auto-update your record. |

## 2. Everyday updates

All content lives in plain text files in `data/`. Edit them on github.com (click the file, then the pencil),
commit, and the site rebuilds itself within minutes.

| To change… | Edit |
|---|---|
| Publications (add PDF/preprint/code links, fix details, mark as featured) | `data/publications.json` |
| Talks | `data/talks.json` |
| News on the home page | `data/news.json` |
| Gallery albums and captions | `data/gallery.json` (images go in `assets/img/gallery/<album-id>/`) |
| Email, Formspree ID, photo, GitHub username | `data/site.json` |
| Page text (research themes, teaching, CV page) | `templates/*.html` |
| The downloadable CV | `cv/Salisu_CV.tex` (compiled automatically on every push; add `cv/SaniPhotograph.png` for the photo) |

A publication entry looks like this; only `title`, `authors` and `year` are required:

```json
{
  "id": "salisu2027newresult",
  "title": "A new result on enriched mappings in CAT(0) spaces",
  "authors": ["Salisu, S.", "Berinde, V."],
  "venue": "J. Fixed Point Theory Appl.", "volume": "29", "issue": "1", "pages": "12", "year": 2027,
  "type": "article", "status": "published",
  "doi": "10.1007/xxxxx", "url": "https://doi.org/10.1007/xxxxx",
  "index": "SCIE", "quartile": "Q1", "impact_factor": 1.1,
  "first_author": true, "corresponding": false,
  "topics": ["fixed-point", "geometry"],
  "pdf": "assets/papers/salisu2027.pdf", "preprint": null, "code": "https://github.com/..."
}
```

Topics: `fixed-point`, `variational`, `optimization`, `geometry`, `applications`.
Put an `"added": "YYYY-MM-DD"` date to show a **New** badge for 90 days.

To rebuild the whole list from the LaTeX CV: `python tools/cv_to_json.py cv/Salisu_CV.tex`
(keeps any `pdf`, `code`, `citations` fields already present).

## 3. Preview on your own computer (optional)

```bash
pip install -r requirements.txt
bash tools/vendor.sh            # needs Node.js; fetches KaTeX and fonts
python tools/build.py
python -m http.server -d _site  # open http://localhost:8000
```

## How it works

```
data/*.json  ─┐
templates/   ─┼─ tools/build.py ─► _site/ (plain HTML/CSS/JS) ─► GitHub Pages
assets/      ─┘
ORCID / Crossref / OpenAlex / Scholar ─► tools/update_publications.py (weekly) ─► data/
```

## Privacy notes

Date of birth and phone numbers are deliberately left off the website and out of the web edition of the CV
(`cv/Salisu_CV.tex`). Referees are listed by name only on the web page.
