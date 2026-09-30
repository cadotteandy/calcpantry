"""Builds the static site into dist/.

Each calculator is one file in pages/<category>/<slug>.html:

    ---
    { JSON front matter: title, description, h1, intro, faq, related }
    ---
    <calculator form + outputs + script>
    <!-- article -->
    <explanatory article HTML>

Run:  python build.py          (then upload dist/ to any static host)
      python build.py --serve  (build + preview at http://localhost:8000)
"""
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

SITE = {
    "name": "CalcPantry",
    "tagline": "Free calculators for sellers, home projects, pets, hobbies and money",
    "url": "https://calcpantry.com",
    "adsense_client": "ca-pub-6857897091548503",  # loads Google's ad script (Auto ads) on every page
    "adsense_slot": "",                   # ad unit ID from AdSense; the fixed ad spaces stay empty until set
    "contact_email": "kagegarasu@gmail.com",
    "year": date.today().year,
}

CATEGORIES = {
    "reselling": {"name": "Reselling & Marketplace Fees", "short": "Reselling", "icon": "🏷️",
                  "blurb": "Know exactly what you'll take home before you list. Fee and profit calculators for eBay, Poshmark, Mercari and Etsy."},
    "home": {"name": "Home Project Calculators", "short": "Home", "icon": "🏠",
             "blurb": "Figure out how much paint, mulch, gravel, concrete or flooring you need, and what it will cost, before you go to the store."},
    "pets": {"name": "Pet Calculators", "short": "Pets", "icon": "🐾",
             "blurb": "Feeding amounts, age conversions and tank stocking for dogs, cats and fish."},
    "hobbies": {"name": "Hobby & Craft Calculators", "short": "Hobbies", "icon": "🧵",
                "blurb": "3D printing costs, fabric yardage, lumber board feet and coffee brew ratios."},
    "money": {"name": "Money & Side Hustle Calculators", "short": "Money", "icon": "💵",
              "blurb": "Take-home pay from side gigs, freelance rates and lease-versus-buy decisions."},
}

# Serve from a sub-folder (e.g. SITE_BASE=/calcpantry for username.github.io/calcpantry/).
# Leave unset when the site is on its own domain.
BASE = os.environ.get("SITE_BASE", "").rstrip("/")
ROOT_LINK = re.compile(r'((?:href|src|action)=["\'])/(?!/)')

FRONT = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def load_pages():
    pages = []
    for path in sorted((ROOT / "pages").glob("*/*.html")):
        m = FRONT.match(path.read_text(encoding="utf-8"))
        if not m:
            sys.exit(f"Missing front matter: {path}")
        meta = json.loads(m.group(1))
        body = m.group(2)
        calc, _, article = body.partition("<!-- article -->")
        cat = path.parent.name
        if cat not in CATEGORIES:
            sys.exit(f"Unknown category folder: {cat}")
        meta.update(slug=path.stem, category=cat, calc=calc.strip(), article=article.strip(),
                    path=f"/{cat}/{path.stem}/")
        meta.setdefault("faq", [])
        meta.setdefault("related", [])
        for key in ("title", "description", "h1", "intro"):
            if not meta.get(key):
                sys.exit(f"{path}: front matter missing '{key}'")
        pages.append(meta)
    return pages


def structured_data(p):
    """schema.org data so Google understands the page (app + breadcrumbs + FAQ)."""
    url = SITE["url"] + p["path"]
    graph = [
        {"@type": "WebApplication", "name": p["h1"], "url": url,
         "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any",
         "description": p["description"],
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": CATEGORIES[p["category"]]["name"],
             "item": f"{SITE['url']}/{p['category']}/"},
            {"@type": "ListItem", "position": 3, "name": p["h1"], "item": url}]},
    ]
    if p["faq"]:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in p["faq"]]})
    return {"@context": "https://schema.org", "@graph": graph}


def write(rel, html):
    is_file = Path(rel).suffix in (".html", ".xml", ".txt")
    out = DIST / rel.strip("/") if is_file else DIST / rel.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    if BASE and out.suffix == ".html":
        html = ROOT_LINK.sub(rf"\g<1>{BASE}/", html)
    out.write_text(html, encoding="utf-8")


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "assets", DIST / "assets")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["tojson_safe"] = lambda v: json.dumps(v, ensure_ascii=False).replace("</", "<\\/")
    pages = load_pages()
    by_slug = {p["slug"]: p for p in pages}
    by_cat = {c: [p for p in pages if p["category"] == c] for c in CATEGORIES}

    common = {"site": SITE, "categories": CATEGORIES, "by_cat": by_cat}

    for p in pages:
        p["jsonld"] = structured_data(p)
        related = [by_slug[s] for s in p["related"] if s in by_slug]
        # Fill up with same-category pages so every page links onward.
        for other in by_cat[p["category"]]:
            if len(related) >= 4:
                break
            if other is not p and other not in related:
                related.append(other)
        write(p["path"], env.get_template("calculator.html").render(
            page=p, cat=CATEGORIES[p["category"]], related=related, **common))

    for key, cat in CATEGORIES.items():
        write(f"/{key}/", env.get_template("category.html").render(
            cat_key=key, cat=cat, items=by_cat[key], page={"path": f"/{key}/"}, **common))

    write("/", env.get_template("home.html").render(page={"path": "/"}, **common))
    for name in ("about", "privacy", "contact"):
        write(f"/{name}/", env.get_template(f"{name}.html").render(page={"path": f"/{name}/"}, **common))
    write("404.html", env.get_template("404.html").render(page={"path": "/404"}, **common))

    urls = ["/"] + [f"/{k}/" for k in CATEGORIES] + [p["path"] for p in pages] + ["/about/", "/privacy/", "/contact/"]
    today = date.today().isoformat()
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{SITE['url']}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls]
    sitemap.append("</urlset>")
    write("sitemap.xml", "\n".join(sitemap))
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")
    if SITE["adsense_client"]:
        pub = SITE["adsense_client"].replace("ca-", "")
        write("ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")

    print(f"Built {len(pages)} calculators, {len(CATEGORIES)} categories -> {DIST}")


def serve():
    import functools
    import http.server
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    print("Preview: http://localhost:8000  (Ctrl+C to stop)")
    http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        serve()
