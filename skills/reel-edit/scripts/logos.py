"""Official brand logos for a reel: real app icons, never letter tiles, never a parent brand's mark.

python3 logos.py <project> key="App name|Seller" ... key=https://product.site ...
  gemini="Google Gemini|Google LLC"   -> App Store icon (iTunes Search API, artworkUrl512 -> 512x512 PNG)
  edits="Edits: Video Editor|Instagram, Inc."
  swishy=https://www.swishy.ai         -> the site's own apple-touch-icon / largest icon, else its inline <svg> logo

Saves assets/logos/app/<key>.png|.svg and assets/logos/app/_sheet.png (look at it before building).
Rules learned 17 Nov 2026 (reel 18): the Instagram logo is NOT the Edits app; Meta's infinity is NOT Meta AI;
a 48 px favicon scaled up looks broken, so the script falls back to the site's vector logo and warns when small.
The marks belong to their owners: use them only to refer to the product.
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}


def get(u, binary=False):
    d = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read()
    return d if binary else d.decode("utf8", "ignore")


def app_icon(name, seller, out):
    for country in ("in", "us"):
        q = urllib.parse.urlencode({"term": name, "entity": "software", "country": country, "limit": 15})
        res = json.loads(get("https://itunes.apple.com/search?" + q))["results"]
        hits = [r for r in res if name.lower() in r["trackName"].lower() and (not seller or r["sellerName"] == seller)]
        if hits:
            r = hits[0]
            art = r["artworkUrl512"].rsplit("/", 1)[0] + "/512x512bb.png"
            open(out + ".png", "wb").write(get(art, True))
            return f'{r["trackName"]} | {r["sellerName"]}'
    raise SystemExit(f"no App Store match for {name!r} / {seller!r}: print the search results and pick the exact trackName + sellerName")


def site_icon(site, out):
    html = get(site)
    cands = []
    for t in re.findall(r'<link[^>]+rel="[^"]*icon[^"]*"[^>]*>', html):
        h = re.search(r'href="([^"]+)"', t); sz = re.search(r'sizes="(\d+)', t)
        if h: cands.append((("apple" in t) * 1000 + int(sz.group(1) if sz else 32), urllib.parse.urljoin(site, h.group(1))))
    cands.sort(reverse=True)
    if cands and cands[0][0] >= 128:
        u = cands[0][1]; ext = ".svg" if u.split("?")[0].endswith(".svg") else ".png"
        open(out + ext, "wb").write(get(u, True)); return f"site icon {u}"
    svgs = re.findall(r"<svg.*?</svg>", html, re.S)
    if svgs:   # usually the header logo comes first; check the sheet
        open(out + ".svg", "w").write(svgs[0]); return "inline <svg> #0 from the page (CHECK the sheet; recolour currentColor with the brand colour)"
    if cands:
        u = cands[0][1]; open(out + ".png", "wb").write(get(u, True)); return f"WARNING small icon only ({cands[0][0]} px): {u}"
    raise SystemExit(f"no icon found on {site}")


def main():
    P = os.path.abspath(sys.argv[1]); D = os.path.join(P, "assets/logos/app"); os.makedirs(D, exist_ok=True)
    keys = []
    for arg in sys.argv[2:]:
        k, v = arg.split("=", 1); out = os.path.join(D, k); keys.append(k)
        if v.startswith("http"): print(k, "->", site_icon(v, out))
        else:
            name, _, seller = v.partition("|"); print(k, "->", app_icon(name.strip(), seller.strip(), out))
    # contact sheet (PNG ones; SVGs render via the browser at build time)
    pngs = [os.path.join(D, k + ".png") for k in keys if os.path.exists(os.path.join(D, k + ".png"))]
    if pngs:
        args = sum([["-i", p] for p in pngs], [])
        flt = "".join(f"[{i}]scale=120:120[s{i}];" for i in range(len(pngs))) + "".join(f"[s{i}]" for i in range(len(pngs))) + f"hstack=inputs={len(pngs)}" if len(pngs) > 1 else "[0]scale=120:120"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", flt, os.path.join(D, "_sheet.png")])
        print("sheet ->", os.path.join(D, "_sheet.png"))


if __name__ == "__main__":
    main()
