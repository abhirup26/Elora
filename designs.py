"""Showroom-plate saree illustrations (SVG).

Every saree gets a consistent boutique product plate: a dress-form
mannequin wearing the drape — blouse in the saree's accent tone, pleated
skirt in the body fabric with its woven motif, zari + border band at the
hem, and the pallu sash falling over the shoulder. Flowy materials
(georgette / chiffon / organza) get a wavy hem; structured ones a crisp
A-line. A fabric swatch chip sits beside the figure.

Files are written to static/designs/saree-<id>.svg by write_all(). These
plates ARE the customer-facing product imagery; fetched photos are held
in reserve and only shown when explicitly pinned.
"""
import math
import os

from .catalogue import SAREES

DESIGN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "static", "designs")

# per-saree: (body motif, border motif)
MOTIF_MAP = {
    1: ("sparkle", "temple"),    # Midnight Georgette — scattered sparkles
    2: ("sequins", "stripes"),   # Wine Sequin Chiffon
    3: ("zari_dots", "temple"),  # Emerald Silk Blend
    4: ("checks", "temple"),     # Lal Par Cotton — temple border classic
    5: ("fish", "thread"),       # Haldi Tant — fish motifs (tant hallmark)
    6: ("paisley", "temple"),    # Marigold Silk Blend
    7: ("window", "temple"),     # Bridal Kanjivaram — korvai checks
    8: ("jaal", "floral"),       # Rose-Gold Banarasi — jangla jaal
    9: ("checks", "butta"),      # Ivory Pearl Kanjivaram
    10: ("checks", "solid"),     # Slate Chettinad — korvai squares
    11: ("stripes", "stripes"),  # Powder-Blue Organza — minimal stripes
    12: ("butta", "thread"),     # Deep Teal Chanderi — gold buttas
    # ---- party (contd.) ----
    13: ("butta", "thread"),     # Royal-Blue Organza — gold butti scatter
    14: ("sparkle", "stripes"),  # Blush Georgette — gold lamé shimmer
    15: ("sequins", "stripes"),  # Onyx Sequin Chiffon — sequin falls
    16: ("zari_dots", "temple"), # Fuchsia Silk Blend — gold-leaf border
    17: ("sparkle", "floral"),   # Peacock Teal Georgette
    18: ("sequins", "thread"),   # Champagne Chiffon — antique brass
    19: ("checks", "stripes"),   # Indigo Silk Blend — silver checks
    20: ("stripes", "butta"),    # Coral Organza — whisper of gold
    21: ("sparkle", "temple"),   # Aubergine Georgette
    # ---- puja (contd.) ----
    22: ("fish", "temple"),      # Cream Tant — red temple border
    23: ("paisley", "thread"),   # Jamdani white-on-white
    24: ("zari_dots", "thread"), # Golden Tussar
    25: ("checks", "solid"),     # Forest-Green Cotton — cream band
    26: ("butta", "floral"),     # Royal-Purple — gold buttis
    27: ("stripes", "stripes"),  # Saffron Cotton — dobby border
    28: ("fish", "thread"),      # Rose Tant — fish border
    29: ("butta", "thread"),     # Ivory Chanderi — muted gold buttas
    30: ("jaal", "temple"),      # Maroon Tussar — gold jaal
    # ---- wedding (contd.) ----
    31: ("window", "temple"),    # Emerald Kanjivaram — korvai checks
    32: ("jaal", "floral"),      # Royal-Blue Banarasi — silver jangla
    33: ("window", "butta"),     # Plum Kanchipuram
    34: ("checks", "temple"),    # Vermillion Kanjivaram — korvai
    35: ("butta", "floral"),     # Golden Banarasi — meenakari buttas
    36: ("zari_dots", "temple"), # Rani-Pink — rudraksha border
    37: ("checks", "solid"),     # Ivory-and-Red Kanjivaram
    38: ("jaal", "floral"),      # Onyx-Gold Banarasi
    39: ("paisley", "thread"),   # Bronze Tussar — gold thread
    # ---- office (contd.) ----
    40: ("stripes", "solid"),    # Charcoal Linen — silver selvedge
    41: ("checks", "thread"),    # Ivory Linen — olive border
    42: ("checks", "stripes"),   # Olive Cotton
    43: ("butta", "thread"),     # Wine Chanderi — gold buttas
    44: ("checks", "solid"),     # Mustard Chettinad — slate korvai
    45: ("stripes", "stripes"),  # Smoke-Grey Georgette
    46: ("stripes", "solid"),    # Powder-Grey Chiffon — navy edge
    47: ("checks", "stripes"),   # Denim-Blue Cotton
    48: ("zari_dots", "thread"), # Sand Tussar — antique brass
}

FLOWY = {"georgette", "chiffon", "organza blend"}

BODY_LABELS = {
    "sparkle": "scattered sparkle", "sequins": "sequin scatter",
    "zari_dots": "zari dot grid", "checks": "check weave",
    "fish": "fish motifs", "paisley": "paisley buttis",
    "window": "korvai window checks", "jaal": "jangla jaal vines",
    "butta": "gold buttas", "stripes": "matte stripes",
}
BORDER_LABELS = {
    "temple": "temple border", "stripes": "zari twin stripes",
    "thread": "thread border", "floral": "floral border",
    "butta": "butta border", "solid": "solid korvai band",
}


def design_label(saree_id):
    body, border = MOTIF_MAP.get(saree_id, ("checks", "temple"))
    return f"{BODY_LABELS[body].capitalize()} with a {BORDER_LABELS[border]}"


# ------------------------------------------------------------------ helpers
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(t):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in t)


def shade(hexc, f):
    """Mix toward white (f>0) or black (f<0)."""
    r, g, b = _rgb(hexc)
    target = (255, 255, 255) if f > 0 else (0, 0, 0)
    t = abs(f)
    return _hex(tuple(c * (1 - t) + o * t for c, o in zip((r, g, b), target)))


def blend(h1, h2):
    a, b = _rgb(h1), _rgb(h2)
    return _hex(tuple((x + y) / 2 for x, y in zip(a, b)))


# ------------------------------------------------------------------ motifs
def _body_pattern(kind, accent):
    if kind == "sparkle":
        star = ('<path d="M0 -9 L2.2 -2.2 L9 0 L2.2 2.2 L0 9 L-2.2 2.2 L-9 0 '
                'L-2.2 -2.2 Z" fill="{a}" opacity="0.75"/>'
                '<circle r="1.6" fill="#FFF" opacity="0.9"/>')
        return 90, 90, (star.format(a=accent) +
                        f'<g transform="translate(62,38) scale(0.6)">{star.format(a=accent)}</g>' +
                        f'<g transform="translate(30,66) scale(0.75)">{star.format(a=accent)}</g>')
    if kind == "sequins":
        seq = (f'<circle r="3" fill="{accent}"/>'
               f'<circle cx="-1" cy="-1" r="1" fill="#FFFFFF" opacity="0.85"/>')
        return 26, 26, (f'<g transform="translate(8,8)">{seq}</g>'
                        f'<g transform="translate(21,21) scale(0.8)">{seq}</g>')
    if kind == "zari_dots":
        return 60, 60, (f'<circle cx="16" cy="16" r="4.5" fill="none" stroke="{accent}" '
                        f'stroke-width="2"/><circle cx="16" cy="16" r="1.4" fill="{accent}"/>'
                        f'<circle cx="46" cy="46" r="2.4" fill="{accent}" opacity="0.8"/>')
    if kind == "checks":
        return 56, 56, (f'<rect width="56" height="2.4" fill="{accent}" opacity="0.45"/>'
                        f'<rect width="2.4" height="56" fill="{accent}" opacity="0.45"/>')
    if kind == "fish":
        fish = (f'<path d="M2 11 C8 3 22 3 28 11 C22 19 8 19 2 11 Z" fill="none" '
                f'stroke="{accent}" stroke-width="1.8"/>'
                f'<path d="M28 11 L36 5 L34 11 L36 17 Z" fill="{accent}"/>'
                f'<circle cx="8" cy="10" r="1.3" fill="{accent}"/>')
        return 110, 66, (f'<g transform="translate(6,6)">{fish}</g>'
                         f'<g transform="translate(62,38) scale(-0.72,0.72)">{fish}</g>')
    if kind == "paisley":
        drop = (f'<path d="M4 20 C4 9 15 3 24 9 C33 15 30 30 18 30 C9 30 4 26 4 20 Z" '
                f'fill="none" stroke="{accent}" stroke-width="2"/>'
                f'<path d="M12 21 C12 15 18 12 22 15" fill="none" '
                f'stroke="{accent}" stroke-width="1.4"/>')
        return 84, 84, (f'<g transform="translate(10,8) rotate(18 14 16)">{drop}</g>'
                        f'<circle cx="70" cy="70" r="3" fill="{accent}" opacity="0.85"/>')
    if kind == "window":
        return 84, 84, (f'<rect x="2" y="2" width="80" height="80" fill="none" '
                        f'stroke="{accent}" stroke-width="3" opacity="0.8"/>'
                        f'<circle cx="42" cy="42" r="5" fill="{accent}" opacity="0.9"/>')
    if kind == "jaal":
        vine = (f'<path d="M0 30 C22 8 44 52 66 30 C76 20 84 26 92 22" fill="none" '
                f'stroke="{accent}" stroke-width="1.8"/>'
                f'<ellipse cx="30" cy="16" rx="5" ry="2.6" fill="{accent}" '
                f'transform="rotate(-30 30 16)"/>'
                f'<ellipse cx="58" cy="42" rx="5" ry="2.6" fill="{accent}" '
                f'transform="rotate(-30 58 42)"/>'
                f'<circle cx="90" cy="44" r="3" fill="{accent}"/>'
                f'<circle cx="10" cy="52" r="2.2" fill="{accent}"/>')
        return 96, 72, vine + f'<g transform="translate(48,36)">{vine}</g>'
    if kind == "butta":
        petals = "".join(
            f'<circle cx="{20 + 14 * math.cos(i * 0.785):.1f}" '
            f'cy="{20 + 14 * math.sin(i * 0.785):.1f}" r="2" fill="{accent}"/>'
            for i in range(8))
        return 76, 76, (f'<circle cx="20" cy="20" r="9" fill="none" stroke="{accent}" '
                        f'stroke-width="2"/><circle cx="20" cy="20" r="3.2" fill="{accent}"/>'
                        + petals)
    if kind == "stripes":
        return 34, 34, (f'<rect width="7" height="34" fill="{accent}" opacity="0.30"/>')
    raise ValueError(kind)


def _border_pattern(kind, accent):
    if kind == "temple":
        t = (f'<path d="M4 30 L14 4 L24 30" fill="none" stroke="{accent}" '
             f'stroke-width="2.4"/><path d="M9 30 L14 17 L19 30" fill="{accent}" '
             f'opacity="0.8"/>')
        return 42, 34, t
    if kind == "floral":
        petal = "".join(
            f'<ellipse cx="19" cy="{8 + 9 * (i % 2)}" rx="3" ry="6" fill="{accent}" '
            f'opacity="0.85" transform="rotate({i * 72} 19 19)"/>'
            for i in range(5))
        return 42, 38, petal + f'<circle cx="19" cy="19" r="3" fill="{shade(accent, 0.5)}"/>'
    if kind == "butta":
        return 44, 36, (f'<circle cx="12" cy="18" r="5" fill="none" stroke="{accent}" '
                        f'stroke-width="2"/><circle cx="12" cy="18" r="1.8" fill="{accent}"/>'
                        f'<circle cx="32" cy="18" r="2" fill="{accent}"/>')
    if kind == "stripes":
        return 24, 30, (f'<rect x="4" y="0" width="3.5" height="30" fill="{accent}"/>'
                        f'<rect x="14" y="0" width="1.8" height="30" fill="{accent}" '
                        f'opacity="0.75"/>')
    if kind == "thread":
        return 26, 30, (f'<rect x="0" y="6" width="26" height="2.2" fill="{accent}"/>'
                        f'<rect x="0" y="20" width="26" height="2.2" fill="{accent}" '
                        f'opacity="0.8"/>')
    return None                                     # solid band


# ------------------------------------------------------------------ plate
def design_svg(saree):
    sid, hexc, accent = saree["id"], saree["hex"], saree["accent"]
    body_kind, border_kind = MOTIF_MAP[sid]
    deep = shade(hexc, -0.38)
    mid = shade(hexc, 0.16)
    blouse = shade(accent, -0.18)
    blouse_d = shade(accent, -0.45)
    pallu = shade(blend(hexc, accent), -0.10)
    band = shade(accent, -0.22)
    gold_line = shade(accent, 0.35)
    bronze = "#7D6A4F"
    bronze_d = "#5C4C36"

    bw, bh, body_motif = _body_pattern(body_kind, accent)
    bp = _border_pattern(border_kind, gold_line)
    border_pattern_svg = ""
    if bp:
        pw, ph, motif = bp
        border_pattern_svg = (f'<pattern id="bord" width="{pw}" height="{ph}" '
                              f'patternUnits="userSpaceOnUse">{motif}</pattern>')

    flowy = saree["material"] in FLOWY
    if flowy:                       # soft wavy hem
        skirt = ("M226 344 L374 344 C380 470 398 558 428 638 "
                 "Q 402 656 372 644 Q 342 632 312 648 Q 282 664 252 646 "
                 "Q 222 632 198 648 Q 184 656 176 640 "
                 "C 204 558 220 470 226 344 Z")
    else:                           # crisp A-line
        skirt = ("M226 344 L374 344 C380 470 396 566 424 648 "
                 "L176 648 C204 566 220 470 226 344 Z")

    pleats = "".join(
        f'<path d="M{300 + i * 22} 350 L{300 + i * 36} 640" fill="none" '
        f'stroke="#FFFFFF" stroke-width="6" opacity="0.12"/>'
        f'<path d="M{300 + i * 22 + 8} 350 L{300 + i * 36 + 8} 640" fill="none" '
        f'stroke="#000000" stroke-width="2" opacity="0.06"/>'
        for i in (-3, -2, -1, 0, 1, 2, 3))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 780" role="img" aria-label="{saree["name"]} — draped saree, {saree["material"]}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#F8F2E8"/><stop offset="1" stop-color="#EFE3D0"/>
    </linearGradient>
    <linearGradient id="body" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{mid}"/><stop offset="0.55" stop-color="{hexc}"/><stop offset="1" stop-color="{deep}"/>
    </linearGradient>
    <linearGradient id="blouse" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{blouse}"/><stop offset="1" stop-color="{blouse_d}"/>
    </linearGradient>
    <linearGradient id="pallu" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{shade(pallu, 0.14)}"/><stop offset="1" stop-color="{shade(pallu, -0.16)}"/>
    </linearGradient>
    <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.30"/>
      <stop offset="0.4" stop-color="#FFFFFF" stop-opacity="0.03"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.12"/>
    </linearGradient>
    <pattern id="mot" width="{bw}" height="{bh}" patternUnits="userSpaceOnUse">{body_motif}</pattern>
    {border_pattern_svg}
    <clipPath id="sk"><path d="{skirt}"/></clipPath>
  </defs>

  <rect width="600" height="780" fill="url(#bg)"/>
  <ellipse cx="300" cy="716" rx="215" ry="20" fill="#000" opacity="0.10"/>

  <!-- stand -->
  <rect x="295" y="470" width="10" height="220" fill="{bronze}"/>
  <ellipse cx="300" cy="694" rx="74" ry="13" fill="{bronze_d}"/>
  <ellipse cx="300" cy="689" rx="74" ry="12" fill="{bronze}"/>

  <!-- pleated skirt -->
  <g>
    <path d="{skirt}" fill="url(#body)" stroke="{shade(hexc, -0.5)}" stroke-opacity="0.35" stroke-width="1.5"/>
    <g clip-path="url(#sk)">
      <rect x="150" y="330" width="300" height="330" fill="url(#mot)"/>
      {''.join(pleats)}
      <rect x="150" y="604" width="300" height="6" fill="{gold_line}"/>
      <rect x="150" y="610" width="300" height="52" fill="{band}"/>
      <rect x="150" y="610" width="300" height="52" fill="url(#bord)"/>
      <rect x="150" y="330" width="300" height="330" fill="url(#sheen)"/>
    </g>
  </g>

  <!-- waist belt -->
  <rect x="222" y="330" width="156" height="15" rx="7" fill="{band}"/>
  <rect x="222" y="330" width="156" height="4" rx="2" fill="{gold_line}" opacity="0.9"/>

  <!-- blouse torso -->
  <path d="M262 170 C254 224 256 282 268 338 L332 338 C344 282 346 224 338 170 C318 158 282 158 262 170 Z"
        fill="url(#blouse)"/>
  <path d="M300 162 L300 338" stroke="{shade(blouse_d, 0.25)}" stroke-width="2" opacity="0.5"/>
  <circle cx="300" cy="252" r="3.4" fill="{gold_line}" opacity="0.9"/>

  <!-- fabric-covered neck + stand cap -->
  <rect x="291" y="124" width="18" height="46" fill="{blouse_d}"/>
  <circle cx="300" cy="118" r="17" fill="{bronze}"/>
  <circle cx="300" cy="113" r="4" fill="{bronze_d}"/>

  <!-- pallu: shoulder flap, sash across chest, hanging panel -->
  <path d="M336 150 L384 170 L350 192 Z" fill="url(#pallu)"/>
  <path d="M348 158 L384 174 L334 342 L302 336 Z" fill="url(#pallu)"/>
  <path d="M348 158 L384 174" stroke="{gold_line}" stroke-width="2.5" opacity="0.9"/>
  <path d="M302 336 L334 342" stroke="{gold_line}" stroke-width="2.5" opacity="0.9"/>
  <path d="M302 340 L336 346 L358 648 L318 654 Z" fill="url(#pallu)"/>
  <g clip-path="url(#sk)">
    <path d="M302 340 L336 346 L358 660 L318 660 Z" fill="url(#mot)" opacity="0.9"/>
  </g>
  <path d="M336 346 L358 648" stroke="{gold_line}" stroke-width="3" opacity="0.85"/>
  <path d="M302 340 L318 654" stroke="{gold_line}" stroke-width="3" opacity="0.85"/>

  <!-- fabric swatch chip -->
  <g>
    <rect x="452" y="672" width="114" height="70" rx="10" fill="#FFFFFF"
          stroke="#E7DCCC" stroke-width="1.5"/>
    <rect x="460" y="680" width="58" height="54" fill="url(#body)"/>
    <rect x="460" y="680" width="58" height="54" fill="url(#mot)"/>
    <rect x="518" y="680" width="40" height="54" fill="{band}"/>
    <rect x="518" y="680" width="40" height="54" fill="url(#bord)"/>
  </g>
</svg>'''


def write_all():
    os.makedirs(DESIGN_DIR, exist_ok=True)
    for s in SAREES:
        path = os.path.join(DESIGN_DIR, f"saree-{s['id']}.svg")
        with open(path, "w") as f:
            f.write(design_svg(s))
    return len(SAREES)
