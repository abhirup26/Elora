"""Photo policy for the site.

CUSTOMER-FACING IMAGERY = showroom plates (see designs.py). Every saree
always displays its draped mannequin illustration, drawn in its exact
colours, motifs and fabric behaviour — consistent, clean, and true to
the description.

Fetched photos (Wikimedia Commons, colour-gated) are kept ON DISK AS
RESERVE for reference but are NEVER shown to customers. Only images
explicitly pinned with `python -m saree_studio.photos --set <id> <url>`
(e.g. the shop's own product photography) are displayed instead of the
plate. Un-pin with --unset <id>.
"""
import colorsys
import io
import json
import math
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .catalogue import SAREES
from .config import INSTANCE_DIR

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PHOTO_DIR = os.path.join(STATIC_DIR, "photos")
MANIFEST_PATH = os.path.join(INSTANCE_DIR, "photo_manifest.json")
DESIGN_DIR = os.path.join(STATIC_DIR, "designs")

API = "https://commons.wikimedia.org/w/api.php"
WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/media-list/"
UA = {"User-Agent": "ElaraSite/1.0 (personal project; contact: local)"}
ALLOWED_EXT = (".jpg", ".jpeg", ".png")
MAX_BYTES = 15 * 1024 * 1024

QUERIES = {
    1:  ["blue georgette saree", "blue sari", "blue saree"],
    2:  ["maroon sari", "wine saree", "dark red sari", "maroon saree"],
    3:  ["green silk saree", "green sari", "green saree"],
    4:  ["Red cotton saree West Bengal", "Lal par saree", "red cotton sari"],
    5:  ["yellow tant saree", "yellow sari cotton", "Tant saree", "yellow saree"],
    6:  ["orange silk saree", "orange sari", "yellow silk sari"],
    7:  ["red Kanchipuram sari", "Kanchipuram sari", "bridal sari red"],
    8:  ["pink Banarasi sari", "pink sari silk", "Banarasi sari"],
    9:  ["cream sari", "off white silk saree", "white sari"],
    10: ["Chettinad saree", "grey sari", "grey saree"],
    11: ["sky blue saree", "powder blue sari", "light blue saree",
         "pale blue sari", "blue silk sari"],
    12: ["teal saree", "teal sari", "blue green saree"],
    # ---- party (contd.) ----
    13: ["royal blue saree", "blue organza saree", "blue saree", "blue sari"],
    14: ["pink georgette saree", "blush pink saree", "pink saree", "pink sari"],
    15: ["black saree", "black sari", "black silk saree"],
    16: ["magenta saree", "fuchsia saree", "pink saree", "rani pink sari"],
    17: ["teal saree", "teal georgette saree", "blue green saree", "teal sari"],
    18: ["beige saree", "champagne saree", "cream saree", "gold beige sari"],
    19: ["indigo saree", "blue silk saree", "blue sari", "navy blue saree"],
    20: ["coral saree", "peach saree", "orange saree", "salmon pink sari"],
    21: ["purple saree", "violet saree", "aubergine saree", "wine saree"],
    # ---- puja (contd.) ----
    22: ["cream tant saree", "cream saree", "off white saree", "white sari"],
    23: ["jamdani saree", "white saree", "white sari", "white cotton saree"],
    24: ["tussar saree", "tussar silk saree", "golden silk saree", "yellow saree"],
    25: ["green saree", "green cotton saree", "dark green sari", "green handloom saree"],
    26: ["purple saree", "violet sari", "purple silk saree"],
    27: ["saffron saree", "orange saree", "orange sari", "saffron cotton saree"],
    28: ["pink saree", "rose pink sari", "pink cotton saree", "pink tant saree"],
    29: ["ivory saree", "chanderi saree", "cream silk saree", "chanderi sari"],
    30: ["maroon saree", "maroon tussar saree", "dark red saree", "maroon silk saree"],
    # ---- wedding (contd.) ----
    31: ["green silk saree", "green Kanchipuram sari", "green kanjivaram saree",
         "bridal green saree"],
    32: ["blue banarasi saree", "royal blue silk saree", "blue sari", "blue banarasi sari"],
    33: ["plum saree", "purple saree", "violet saree", "purple silk saree"],
    34: ["vermillion saree", "orange silk saree", "saffron saree", "orange sari"],
    35: ["gold saree", "golden silk saree", "yellow silk saree", "gold banarasi saree"],
    36: ["pink silk saree", "rani pink saree", "pink Kanchipuram sari",
         "magenta silk saree"],
    37: ["kasavu saree", "ivory saree", "cream saree", "kerala saree"],
    38: ["black banarasi saree", "black silk saree", "black saree", "black sari"],
    39: ["brown saree", "tussar saree", "bronze saree", "brown silk saree"],
    # ---- office (contd.) ----
    40: ["dark grey saree", "charcoal saree", "grey saree", "black cotton saree"],
    41: ["cream linen saree", "ivory saree", "white linen saree", "white saree"],
    42: ["olive saree", "olive green saree", "mehendi green saree", "green saree"],
    43: ["maroon saree", "wine saree", "maroon silk saree", "maroon chanderi saree"],
    44: ["mustard saree", "mustard yellow saree", "yellow cotton saree", "yellow saree"],
    45: ["grey saree", "grey georgette saree", "silver grey saree", "grey sari"],
    46: ["light grey saree", "grey saree", "silver saree", "ash grey sari"],
    47: ["blue cotton saree", "blue saree", "denim blue saree", "blue sari"],
    48: ["beige saree", "tussar saree", "sand saree", "cream tussar saree"],
}

# Wikipedia articles whose media can backfill a saree (tried in order).
ARTICLES = {
    4:  ["Tant sari", "Sari"],
    5:  ["Tant sari", "Sari"],
    6:  ["Sari"],
    7:  ["Kanchipuram sari", "Sari"],
    8:  ["Banarasi sari", "Sari"],
    9:  ["Kanchipuram sari", "Sari"],
    10: ["Sari"],
    1:  ["Sari"], 2: ["Sari"], 3: ["Sari"], 11: ["Sari"],
    12: ["Chanderi sari", "Sari"],
    22: ["Tant sari", "Jamdani", "Sari"],
    23: ["Jamdani", "Tant sari", "Sari"],
    24: ["Tussar silk", "Sari"],
    25: ["Sari"], 26: ["Sari"], 27: ["Sari"], 28: ["Tant sari", "Sari"],
    29: ["Chanderi sari", "Sari"],
    30: ["Tussar silk", "Sari"],
    31: ["Kanchipuram sari", "Sari"],
    32: ["Banarasi sari", "Sari"],
    33: ["Kanchipuram sari", "Sari"],
    34: ["Kanchipuram sari", "Sari"],
    35: ["Banarasi sari", "Sari"],
    36: ["Kanchipuram sari", "Sari"],
    37: ["Kanchipuram sari", "Sari"],
    38: ["Banarasi sari", "Sari"],
    39: ["Tussar silk", "Sari"],
    40: ["Sari"], 41: ["Sari"], 42: ["Sari"], 43: ["Chanderi sari", "Sari"],
    44: ["Sari"], 45: ["Sari"], 46: ["Sari"], 47: ["Sari"],
    48: ["Tussar silk", "Sari"],
}


# Global politeness limiter — Commons throttles bursts (HTTP 403/429).
_rate_lock = threading.Lock()
_last_call = [0.0]
MIN_INTERVAL = 1.0          # seconds between any two API/file requests


def _get(url, binary=False, retries=4):
    """Rate-limited GET with backoff on throttling. Returns b''/'' on failure."""
    for attempt in range(retries):
        with _rate_lock:
            wait = MIN_INTERVAL - (time.time() - _last_call[0])
            if wait > 0:
                time.sleep(wait)
            _last_call[0] = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < retries - 1:
                time.sleep(45 * (attempt + 1))   # back off hard, retry
                continue
            return b"" if binary else ""
        except Exception:
            return b"" if binary else ""
    return b"" if binary else ""


def _expand_queries(queries):
    """Add saree<->sari spellings of every query (Commons uses both)."""
    out = []
    for q in queries:
        out.append(q)
        if "saree" in q:
            out.append(q.replace("saree", "sari"))
        elif "sari" in q:
            out.append(q.replace("sari", "saree"))
    seen, uniq = set(), []
    for q in out:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def _saree_candidates(saree):
    """All Commons/Wikipedia candidate titles for one saree, in order."""
    out = []
    for q in _expand_queries(QUERIES.get(saree["id"], []))[:4]:
        out += _search_file_titles(q, limit=8)
    for article in ARTICLES.get(saree["id"], []):
        out += _article_media_titles(article)
    return out


def _search_file_titles(query, limit=10):
    try:
        data = json.loads(_get(API + "?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "list": "search",
            "srsearch": query, "srnamespace": "6", "srlimit": str(limit),
        })))
        titles = [h["title"] for h in data.get("query", {}).get("search", [])]
        return [t for t in titles
                if t.lower().endswith(ALLOWED_EXT)
                and not any(b in t.lower() for b in ("map", "logo", "diagram", "chart"))]
    except Exception:
        return []


def _article_media_titles(article, limit=12):
    try:
        data = json.loads(_get(WIKI_REST + urllib.parse.quote(article)))
        titles = []
        for item in data.get("items", []):
            t = item.get("title", "")
            if t.startswith("File:") and t.lower().endswith(ALLOWED_EXT):
                titles.append(t)
        return titles[:limit]
    except Exception:
        return []


def _parse_info(page, title):
    infos = page.get("imageinfo") or []
    if not infos:
        return None
    info = infos[0]
    meta = info.get("extmetadata", {})

    def _field(key):
        return (meta.get(key, {}) or {}).get("value", "")
    return {"title": title,
            "source_url": info.get("descriptionurl", ""),
            "thumb_url": info.get("thumburl") or info.get("url"),
            "artist": _field("Artist"), "license": _field("LicenseShortName")}


def _imageinfo(title):
    """Metadata for a single file (kept for --set)."""
    try:
        data = json.loads(_get(API + "?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "titles": title,
            "prop": "imageinfo", "iiprop": "url|extmetadata|size",
            "iiurlwidth": "1200",
        })))
        for page in data.get("query", {}).get("pages", {}).values():
            parsed = _parse_info(page, title)
            if parsed:
                return parsed
    except Exception:
        pass
    return None


def _imageinfo_batch(titles):
    """Metadata for up to 40 files in ONE API call -> {title: meta}."""
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        try:
            data = json.loads(_get(API + "?" + urllib.parse.urlencode({
                "action": "query", "format": "json",
                "titles": "|".join(chunk),
                "prop": "imageinfo", "iiprop": "url|extmetadata|size",
                "iiurlwidth": "1200",
            })))
            for page in data.get("query", {}).get("pages", {}).values():
                t = page.get("title")
                if t in chunk:
                    parsed = _parse_info(page, t)
                    if parsed:
                        out[t] = parsed
        except Exception:
            pass
    return out


def _valid_image(data):
    return (len(data) > 4096 and len(data) <= MAX_BYTES and
            (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"))


# --------------------------------------------------------------------------
# Colour gate — does the photo LOOK like the described saree?
# --------------------------------------------------------------------------
def _rgb_f(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _hsv(hex_color):
    return colorsys.rgb_to_hsv(*_rgb_f(hex_color))


def _hue_dist(h1, h2):
    d = abs(h1 - h2) % 1.0
    return min(d, 1.0 - d)


def dominant_colour(data):
    """Dominant HSV from the CENTRAL CROP of the photo (the saree region).

    Full-scene shots have backgrounds/floor that swamp a naive average,
    so: crop to the middle of the frame, histogram the hues weighted by
    saturation x value, then take the mean s/v of pixels near the peak.
    """
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None
    w, hpx = im.size
    im = im.crop((int(w * 0.22), int(hpx * 0.14),
                  int(w * 0.78), int(hpx * 0.86)))
    im.thumbnail((90, 90))
    bins = [0.0] * 36
    pixels = []
    for r, g, b in im.getdata():
        hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if v < 0.10 or s < 0.10:
            continue                       # letterbox / grey backdrop
        weight = s * (0.35 + 0.65 * v)
        bins[int(hh * 36) % 36] += weight
        pixels.append((hh, s, v, weight))
    if not pixels or sum(bins) <= 0:
        return None
    peak = max(range(36), key=lambda i: bins[i])
    sel = [p for p in pixels if min(abs(p[0] * 36 - peak), 36 - abs(p[0] * 36 - peak)) <= 1]
    tw = sum(p[3] for p in sel) or 1.0
    mx = sum(math.cos(2 * math.pi * p[0]) * p[3] for p in sel)
    my = sum(math.sin(2 * math.pi * p[0]) * p[3] for p in sel)
    mean_h = (math.atan2(my, mx) / (2 * math.pi)) % 1.0 if (mx or my) else peak / 36
    return {"h": mean_h, "s": sum(p[1] * p[3] for p in sel) / tw,
            "v": sum(p[2] * p[3] for p in sel) / tw}


def colour_matches(saree, data):
    """True when the photo's central dominant colour fits the description.

    Rules: hue-family match; the photo must actually be colourful when a
    colourful saree is described (grey backdrops fool hue math); and a
    muted/dusty described colour rejects overly vivid photos.
    """
    dom = dominant_colour(data)
    if dom is None:
        return False
    e_h, e_s, e_v = _hsv(saree["hex"])
    if e_s < 0.28:                         # described as (near-)neutral
        if e_s >= 0.15:                    # but with a clear hue lean
            if _hue_dist(dom["h"], e_h) > 0.14:
                return False               # e.g. powder blue vs dusty red
            return dom["s"] < e_s + 0.32 and abs(dom["v"] - e_v) < 0.45
        warm_described = e_h < 0.16 or e_h > 0.90
        return (dom["s"] < e_s + 0.32 and abs(dom["v"] - e_v) < 0.45 and
                not (warm_described and 0.45 < dom["h"] < 0.72))
    if dom["s"] < 0.22:                    # photo is essentially grey
        return False
    if e_s < 0.50 and dom["s"] > e_s + 0.30:
        return False                       # described muted, photo vivid
    d = _hue_dist(dom["h"], e_h)
    return d <= 0.10 or (d <= 0.15 and abs(dom["s"] - e_s) < 0.40)


def _download(url):
    try:
        data = _get(url, binary=True)
        return data if _valid_image(data) else None
    except Exception:
        return None


def _save_photo(saree_id, data, meta, pinned=False):
    ext = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
    fname = f"saree-{saree_id}{ext}"
    with open(os.path.join(PHOTO_DIR, fname), "wb") as f:
        f.write(data)
    for old_ext in (".jpg", ".png"):
        if old_ext != ext:
            old = os.path.join(PHOTO_DIR, f"saree-{saree_id}{old_ext}")
            if os.path.exists(old):
                os.remove(old)
    return {"file": fname, "source_url": meta.get("source_url", ""),
            "artist": meta.get("artist", ""), "license": meta.get("license", ""),
            "title": meta.get("title", ""), "has_photo": True,
            "pinned": bool(pinned)}


def _restore_from_disk(manifest):
    """Reserve photos whose manifest entry was lost (never displayed)."""
    for saree in SAREES:
        sid = str(saree["id"])
        if manifest.get(sid, {}).get("has_photo"):
            continue
        for ext in (".jpg", ".png"):
            path = os.path.join(PHOTO_DIR, f"saree-{saree['id']}{ext}")
            if os.path.exists(path) and os.path.getsize(path) > 4096:
                manifest[sid] = {"file": f"saree-{saree['id']}{ext}",
                                 "source_url": "", "artist": "",
                                 "license": "Wikimedia Commons (reserve, not displayed)",
                                 "title": "previously fetched", "has_photo": True,
                                 "pinned": False}
                break
    return manifest


# --------------------------------------------------------------------------
def fetch_all(refresh=False, workers=6):
    """Fetch colour-verified photos for every saree (parallel per saree)."""
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(PHOTO_DIR, exist_ok=True)
    manifest = _restore_from_disk(load_manifest())

    todo = [s for s in SAREES
            if refresh or not manifest.get(str(s["id"]), {}).get("has_photo")]

    # Phase 1 (parallel): candidate discovery + gated downloads.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        cand_lists = list(pool.map(_saree_candidates, todo))

    used = {v.get("title") for v in manifest.values()
            if isinstance(v, dict) and v.get("has_photo")}

    # Phase 1.5: batched metadata lookup — 40 files per API call.
    unique_titles = []
    seen_titles = set()
    for cands in cand_lists:
        for t in cands:
            if t not in used and t not in seen_titles:
                seen_titles.add(t)
                unique_titles.append(t)
    all_meta = {}
    for i in range(0, len(unique_titles), 40):
        all_meta.update(_imageinfo_batch(unique_titles[i:i + 40]))

    def _pick(job):
        saree, candidates = job
        e_h, e_s, _e_v = _hsv(saree["hex"])
        best = None                                # (hue_dist, data, meta)
        seen, checked = set(), 0
        for title in candidates:
            if best and best[0] <= 0.05:           # excellent match already
                break
            if checked >= 40:                      # bound the work per saree
                break
            if title in used or title in seen:
                continue
            seen.add(title)
            meta = all_meta.get(title)
            if not (meta and meta.get("thumb_url")):
                continue
            data = _download(meta["thumb_url"])
            checked += 1
            if not data:
                continue
            dom = dominant_colour(data)
            if dom is None or not colour_matches(saree, data):
                continue                           # colour gate: keep looking
            d = _hue_dist(dom["h"], e_h) if e_s >= 0.28 else 0.0
            if best is None or d < best[0]:
                best = (d, data, meta)
        return saree, best

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_pick, zip(todo, cand_lists)))

    empty = [s["id"] for (s, _b), c in zip(results, cand_lists) if not c]
    if empty:
        print(f"(no candidates for sarees {empty} — API throttled or offline?)")

    # Phase 2 (serial): dedupe winners, save, persist manifest.
    for saree, best in results:
        key = str(saree["id"])
        prev = manifest.get(key, {})
        entry = None
        if best:
            _d, data, meta = best
            if meta.get("title") not in used:
                entry = _save_photo(saree["id"], data, meta)
                used.add(meta.get("title"))
        if entry:
            manifest[key] = entry
        elif not prev.get("has_photo"):             # keep old photo on failure
            manifest[key] = {"has_photo": False}
        manifest["_meta"] = {"updated": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_manifest(manifest)

    return _audit_saved(manifest)


def _audit_saved(manifest):
    """Final check: every photo on disk must still match its description,
    otherwise demote that saree to its design illustration."""
    for saree in SAREES:
        key = str(saree["id"])
        entry = manifest.get(key, {})
        if not entry.get("has_photo"):
            continue
        path = os.path.join(PHOTO_DIR, entry.get("file", ""))
        if not os.path.exists(path):
            entry["has_photo"] = False
            continue
        with open(path, "rb") as f:
            data = f.read()
        if not colour_matches(saree, data):
            os.remove(path)
            manifest[key] = {"has_photo": False,
                             "rejected": "photo colour did not match description"}
    save_manifest(manifest)
    return manifest


def set_from_url(saree_id, url):
    """Pin a saree to a specific image URL (e.g. your own product photo).
    Pinned images ARE displayed on the site."""
    data = _download(url)
    if data is None:
        return False
    meta = {"title": url, "source_url": url, "artist": "", "license": "shop photo"}
    manifest = load_manifest()
    manifest[str(saree_id)] = _save_photo(saree_id, data, meta, pinned=True)
    save_manifest(manifest)
    return True


def unset(saree_id):
    """Remove a pin; the saree returns to its showroom plate."""
    manifest = load_manifest()
    entry = manifest.get(str(saree_id), {})
    if entry:
        entry["pinned"] = False
        entry["license"] = entry.get("license", "") + " (reserve, not displayed)"
        save_manifest(manifest)
        return True
    return False


# --------------------------------------------------------------------------
def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _clean(html):
    import re
    import html as _h
    return _h.unescape(re.sub(r"<[^>]+>", "", html or "")).strip()


def photo_for(saree_id):
    """Template helper. Only PINNED photos display; everything else shows
    the showroom plate."""
    entry = load_manifest().get(str(saree_id), {})
    if entry.get("has_photo") and entry.get("pinned"):
        fname = entry.get("file", "")
        if os.path.exists(os.path.join(PHOTO_DIR, fname)):
            credit = " · ".join(x for x in (_clean(entry.get("artist", "")),
                                            entry.get("license", "")) if x)
            return {"kind": "photo", "url": f"/static/photos/{fname}",
                    "source_url": entry.get("source_url", ""),
                    "credit": credit or "shop photo"}
    return {"kind": "design", "url": f"/static/designs/saree-{saree_id}.svg",
            "source_url": "", "credit": "house showroom plate"}


def ensure_designs():
    from .designs import write_all
    os.makedirs(DESIGN_DIR, exist_ok=True)
    return write_all()


if __name__ == "__main__":
    from .app import create_app
    create_app()
    args = sys.argv[1:]
    if "--set" in args:
        i = args.index("--set")
        ok = set_from_url(int(args[i + 1]), args[i + 2])
        print(f"pinned saree {args[i + 1]}: {'ok — now displayed on the site' if ok else 'download failed'}")
        sys.exit(0)
    if "--unset" in args:
        i = args.index("--unset")
        print(f"un-pinned saree {args[i + 1]}: {'ok' if unset(int(args[i + 1])) else 'was not pinned'}")
        sys.exit(0)

    n = ensure_designs()
    print(f"showroom plates ready: {n}")
    if "--fetch" in args:
        manifest = fetch_all(refresh="--refresh" in args)
        got = [k for k, v in manifest.items() if isinstance(v, dict) and v.get("has_photo")]
        print(f"reserve photos on disk: {len(got)}/48 (colour-verified, not displayed)")
    manifest = load_manifest()
    shown = 0
    for s in SAREES:
        e = manifest.get(str(s["id"]), {})
        if e.get("pinned") and e.get("has_photo"):
            shown += 1
            print(f"  {s['id']:>2} {s['name']:<30} PINNED PHOTO {e['file']}")
        else:
            print(f"  {s['id']:>2} {s['name']:<30} showroom plate (reserve: "
                  f"{'yes' if e.get('has_photo') else 'no'})")
    print(f"displayed pinned photos: {shown}/48 — everything else shows its plate")
