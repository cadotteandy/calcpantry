# CalcPantry: calculator website

A static site of free calculators that earns from ads and affiliate links.
No server or database is needed. `build.py` turns `pages/` into plain HTML in `dist/`.

## Preview on your PC

Double-click **Preview Site.bat**, then open http://localhost:8000

## Add or edit a calculator

Each calculator is one file: `pages/<category>/<slug>.html`
- Top: JSON settings (page title, Google description, FAQ, related pages)
- Middle: the calculator form and its script
- After `<!-- article -->`: the explanation Google reads

Copy an existing page, change it, and re-run the preview. The new page
shows up in the menus, home page and sitemap automatically.

## Launch checklist

1. **Pick a name and buy a domain** (~$12/yr at Cloudflare, Namecheap or Porkbun).
   Change `SITE` in `build.py` (name, url, contact email). The logo text is in `templates/base.html`.
2. **Host it free on Cloudflare Pages**
   - Make a free Cloudflare account → Workers & Pages → Create → Pages → *Upload assets*
   - Run `python build.py` and upload the `dist` folder
   - Connect your domain in the Pages project settings
3. **Tell Google it exists**: Google Search Console → add your domain → submit `https://yourdomain.com/sitemap.xml`
4. **Apply for Google AdSense** once the site is live and has content (it has 19 calculators, which is enough).
   After approval, put your `ca-pub-…` ID into `SITE["adsense_client"]` in `build.py`, rebuild and re-upload.
   Ad slots and `ads.txt` switch on automatically.
5. **Add affiliate links** where they fit naturally (e.g. shipping supplies on reseller pages,
   tools on home pages). Amazon Associates is the easy start.

## Keeping it earning

- **Update rates yearly**: fees (reselling pages) and tax figures (money pages). Each page shows "last checked".
- **Add calculators steadily.** Sites with 50+ useful calculators rank far better than ones with 10.
- Check Search Console monthly for the searches people use to find you, then build calculators for related searches.
