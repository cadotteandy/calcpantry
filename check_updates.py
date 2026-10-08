"""Checks whether any calculator's figures may need updating.

  python check_updates.py            # check everything, write update-report.md
  python check_updates.py --accept   # after updating pages: save today's source
                                     # figures as the new baseline

Two checks:

1. Sources changed. Every URL in a page's "sources" (plus any extra "watch"
   URLs in its front matter) is fetched, and the figures on it (dollar amounts,
   percentages, cents, temperatures) are compared with the last saved
   baseline. New or vanished figures usually mean a fee, rate or limit moved.
   Some sites block scripts (USDA FSIS, Etsy, SSA); those are listed to check
   by hand.

2. Review due. Each page's "updated" month is compared with how often that
   kind of page should be re-checked:
     yearly-rate pages (taxes, mileage)  every January
     reselling fee pages                 every 3 months
     pages that cite sources             every 6 months
     everything else                     every 12 months

The baseline lives in update-watch.json (committed, so it survives between
machines). Nothing here changes any page: it only reports.
"""
import argparse
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / "update-watch.json"
REPORT = ROOT / "update-report.md"
FRONT = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.S)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

# Pages whose figures are set once a year (new IRS/SSA numbers each January).
YEARLY = {"side-hustle-tax-calculator", "gig-driver-earnings-calculator", "freelance-rate-calculator"}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                      "august", "september", "october", "november", "december"], 1)}
# Figures worth tracking: $1.23, 13.6%, 72.5¢, 165 °F, 0.30 USD-style amounts.
FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?\s?¢|\d+(?:\.\d+)?\s?°\s?[FC]")


def load_pages():
    pages = []
    for path in sorted((ROOT / "pages").glob("*/*.html")):
        m = FRONT.match(path.read_text(encoding="utf-8"))
        if not m:
            continue
        meta = json.loads(m.group(1))
        meta["slug"], meta["category"] = path.stem, path.parent.name
        pages.append(meta)
    return pages


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en"})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text)


def figures(text):
    norm = lambda s: re.sub(r"\s+", "", s).replace(",", "")
    return sorted({norm(f) for f in FIGURE.findall(text)})


def parse_month(s):
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", s or "")
    if m and m.group(1).lower() in MONTHS:
        return date(int(m.group(2)), MONTHS[m.group(1).lower()], 1)
    return None


def months_between(a, b):
    return (b.year - a.year) * 12 + b.month - a.month


def review_due(page, today):
    checked = parse_month(page.get("updated", ""))
    if not checked:
        return "no \"updated\" date"
    if page["slug"] in YEARLY:
        if checked.year < today.year:
            return f"yearly figures, last checked {page['updated']} (new IRS/SSA numbers come out each year)"
        return None
    limit = 3 if page["category"] == "reselling" else 6 if page.get("sources") else 12
    age = months_between(checked, today)
    return f"last checked {page['updated']} ({age} months ago; review every {limit})" if age >= limit else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accept", action="store_true", help="save current source figures as the new baseline")
    ap.add_argument("--no-fetch", action="store_true", help="only check review dates, don't fetch sources")
    args = ap.parse_args()
    today = date.today()
    pages = load_pages()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}

    # url -> pages that use it
    watch = {}
    for p in pages:
        for src in p.get("sources", []) + p.get("watch", []):
            if src.get("url"):
                watch.setdefault(src["url"], {"name": src.get("name", src["url"]), "pages": []})["pages"].append(p["slug"])

    changed, blocked, new = [], [], []
    if not args.no_fetch:
        for i, (url, info) in enumerate(sorted(watch.items()), 1):
            print(f"[{i}/{len(watch)}] {info['name']}", flush=True)
            try:
                figs = figures(fetch_text(url))
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                blocked.append((url, info, getattr(e, "code", None) or str(e)[:60]))
                continue
            digest = hashlib.sha256("\n".join(figs).encode()).hexdigest()[:16]
            old = state.get(url)
            if old is None:
                new.append((url, info))
            elif old["digest"] != digest:
                added = sorted(set(figs) - set(old["figures"]))
                removed = sorted(set(old["figures"]) - set(figs))
                changed.append((url, info, added, removed, old["checked"]))
            if args.accept or old is None:
                state[url] = {"digest": digest, "figures": figs, "checked": today.isoformat()}
        STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    due = [(p, why) for p in pages if (why := review_due(p, today))]

    # Report
    out = [f"# Calculator update check, {today:%B %d, %Y}", ""]
    out.append(f"{len(pages)} calculators, {len(watch)} source pages watched.")
    out.append("")
    out.append("## Sources whose figures changed")
    if args.no_fetch:
        out.append("Skipped (--no-fetch).")
    elif not changed:
        out.append("None. Every reachable source shows the same figures as last time.")
    for url, info, added, removed, since in changed:
        out.append(f"- **[{info['name']}]({url})**, changed since {since}. Used by: {', '.join(info['pages'])}")
        if added:
            out.append(f"  - New figures: {', '.join(added[:25])}{' …' if len(added) > 25 else ''}")
        if removed:
            out.append(f"  - Gone: {', '.join(removed[:25])}{' …' if len(removed) > 25 else ''}")
    if changed:
        out.append("")
        out.append("Open each source, update the calculator and its \"updated\" month if a real figure moved, "
                   "then run `python check_updates.py --accept`. Some changes are just page layout or examples.")
    out.append("")
    out.append("## Check these sources by hand (the site blocks scripts; open them in your browser)")
    if not blocked:
        out.append("None.")
    for url, info, err in blocked:
        out.append(f"- [{info['name']}]({url}) ({err}). Used by: {', '.join(info['pages'])}")
    if new:
        out.append("")
        out.append("## Newly watched (baseline saved today)")
        for url, info in new:
            out.append(f"- [{info['name']}]({url})")
    out.append("")
    out.append("## Calculators due for a review")
    if not due:
        out.append("None.")
    for p, why in sorted(due, key=lambda x: (x[0]["category"], x[0]["slug"])):
        out.append(f"- **{p.get('short') or p['h1']}** (`pages/{p['category']}/{p['slug']}.html`): {why}")
    no_source = [p for p in pages if p["slug"].endswith("-fee-calculator") and not p.get("sources")]
    if no_source:
        out.append("")
        out.append("## Fee calculators with no source to watch")
        out.append("Check these marketplaces' fee pages by hand, or add a `sources`/`watch` URL to the page:")
        out.append(", ".join(p.get("short") or p["h1"] for p in no_source))
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")

    print()
    print(f"Changed sources: {len(changed)}   Check by hand: {len(blocked)}   Reviews due: {len(due)}")
    print(f"Report: {REPORT}")
    return 1 if changed or due else 0


if __name__ == "__main__":
    sys.exit(main())
