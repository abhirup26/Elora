"""Catalogue: sarees (category + material + photo), belt palette, body-type knowledge.

Photo policy: images are CSS-rendered fabric swatches (gradient + sheen + border),
so the site works fully offline with zero image assets while still showing each
saree's real colour and material character.
"""
import json
import os
import sqlite3

from .config import DB_PATH

# --------------------------------------------------------------------------
# Saree catalogue — 4 wear-categories x 3 materials each = 12 products.
# hex = dominant colour, accent = border/zari tone (used by the swatch CSS
# and by the colour-distance math in the stylist).
# --------------------------------------------------------------------------
SAREES = [
    # ---------------- Party wear ----------------
    {"id": 1, "name": "Midnight Georgette Drape", "category": "party", "material": "georgette",
     "hex": "#1F2A5A", "accent": "#C9A227", "price": 4850,
     "blurb": "Flowy georgette with a self-tone shimmer — falls in soft flutes, made for evening lights.",
     "occasion": "Cocktails, sangeet, evening dinners"},
    {"id": 2, "name": "Wine Sequin Chiffon", "category": "party", "material": "chiffon",
     "hex": "#6E1E3C", "accent": "#E8B4C8", "price": 5250,
     "blurb": "Feather-light chiffon scattered with sequins; the wine tone photographs beautifully at night.",
     "occasion": "Receptions, birthday soirees"},
    {"id": 3, "name": "Emerald Silk Blend", "category": "party", "material": "silk blend",
     "hex": "#0F6B4F", "accent": "#F2D06B", "price": 6400,
     "blurb": "A silk-blend body with enough structure to hold pleats sharp — emerald with antique-gold zari.",
     "occasion": "Engagements, festive evenings"},
    # ---------------- Puja wear ----------------
    {"id": 4, "name": "Lal Par Cotton", "category": "puja", "material": "cotton",
     "hex": "#B3232B", "accent": "#F5E6C8",     "price": 1950,
     "blurb": "Handloom cotton in auspicious red with a cream Temple-border — breathes through long rituals.",
     "occasion": "Daily puja, Durga Ashtami, Satyanarayan katha"},
    {"id": 5, "name": "Haldi Tant", "category": "puja", "material": "cotton",
     "hex": "#D9A400", "accent": "#7A4A00", "price": 1750,
     "blurb": "Bengal tant cotton in turmeric yellow with a woven fish motif border.",
     "occasion": "Haldi, Saraswati puja, morning aarti"},
    {"id": 6, "name": "Marigold Silk Blend", "category": "puja", "material": "silk blend",
     "hex": "#E07B00", "accent": "#8B0000", "price": 3900,
     "blurb": "Marigold-orange with a deep maroon pallu — the classic festive-temple pairing.",
     "occasion": "Navratri, Lakshmi puja, house-warming"},
    # ---------------- Wedding wear ----------------
    {"id": 7, "name": "Bridal Kanjivaram", "category": "wedding", "material": "pure silk",
     "hex": "#8E0E2B", "accent": "#D4AF37",     "price": 24500,
     "blurb": "Pure mulberry silk with broad temple border and a korvai pallu in gold zari.",
     "occasion": "The wedding day, reception stage"},
    {"id": 8, "name": "Rose-Gold Banarasi", "category": "wedding", "material": "pure silk",
     "hex": "#C46A72", "accent": "#F0E6D2", "price": 19800,
     "blurb": "Banarasi katan silk with jangla jaal brocade — rose-gold that flatters evening mandap light.",
     "occasion": "Wedding, sangeet night"},
    {"id": 9, "name": "Ivory Pearl Kanjivaram", "category": "wedding", "material": "pure silk",
     "hex": "#F4EDE1", "accent": "#B08D57", "price": 22600,
     "blurb": "Ivory silk with antique-gold checks — the modern minimalist bridal choice.",
     "occasion": "Muhurtham, Christian-Hindu fusion weddings"},
    # ---------------- Office wear ----------------
    {"id": 10, "name": "Slate Chettinad Cotton", "category": "office", "material": "cotton",
     "hex": "#4E5A6B", "accent": "#C0C7D1", "price": 1650,
     "blurb": "Crisp Chettinad cotton in slate grey — wrinkle-tolerant through a 9-hour day.",
     "occasion": "Daily office, client meetings"},
    {"id": 11, "name": "Powder-Blue Organza Blend", "category": "office", "material": "organza blend",
     "hex": "#A8C4E0", "accent": "#3E5F8A", "price": 2950,
     "blurb": "Organza blend with a matte finish — quiet authority in a pastel wash.",
     "occasion": "Presentations, seminars"},
    {"id": 12, "name": "Deep Teal Chanderi", "category": "office", "material": "silk blend",
     "hex": "#175E54", "accent": "#E8DCC3", "price": 3400,
     "blurb": "Chanderi silk-cotton, feather-light with a muted gold butta — formal without stiffness.",
     "occasion": "Interviews, board reviews"},
    # ---------------- Party wear (contd.) ----------------
    {"id": 13, "name": "Royal-Blue Organza Blend", "category": "party", "material": "organza blend",
     "hex": "#27408B", "accent": "#C9A227", "price": 3150,
     "blurb": "Crisp royal-blue organza with a gold butti scatter — architectural drape for cocktail hours.",
     "occasion": "Cocktails, engagement parties"},
    {"id": 14, "name": "Blush Shimmer Georgette", "category": "party", "material": "georgette",
     "hex": "#C4879B", "accent": "#F2D06B", "price": 4650,
     "blurb": "Blush georgette shot with fine gold lamé — a soft-glam choice that glows under warm lights.",
     "occasion": "Receptions, sangeet"},
    {"id": 15, "name": "Onyx-Gold Sequin Chiffon", "category": "party", "material": "chiffon",
     "hex": "#17161A", "accent": "#C9A227", "price": 5450,
     "blurb": "Jet-black chiffon with gold sequin falls — the little-black-dress of sarees.",
     "occasion": "Evening soirées, New Year dinners"},
    {"id": 16, "name": "Fuchsia Silk Blend", "category": "party", "material": "silk blend",
     "hex": "#B03060", "accent": "#F2D06B", "price": 5900,
     "blurb": "Electric fuchsia with a gold-leaf border; holds a sharp pleat all night.",
     "occasion": "Birthday soirees, club evenings"},
    {"id": 17, "name": "Peacock Teal Georgette", "category": "party", "material": "georgette",
     "hex": "#0E7C7B", "accent": "#C9A227", "price": 4450,
     "blurb": "Teal flutes with antique-gold sparkle motifs — jewel tones that flatter every skin tone.",
     "occasion": "Cocktail nights"},
    {"id": 18, "name": "Champagne-Gold Chiffon", "category": "party", "material": "chiffon",
     "hex": "#D4C29A", "accent": "#8B6B3D", "price": 4950,
     "blurb": "Champagne drape with antique-brass sequin work — quiet luxury for late evenings.",
     "occasion": "Anniversary dinners"},
    {"id": 19, "name": "Indigo Silk Blend", "category": "party", "material": "silk blend",
     "hex": "#2E3A87", "accent": "#C0C0C0", "price": 5600,
     "blurb": "Deep indigo with silver zari checks — pairs beautifully with the stylist's silver belt picks.",
     "occasion": "Sangeet, evening parties"},
    {"id": 20, "name": "Coral Organza Blend", "category": "party", "material": "organza blend",
     "hex": "#F08080", "accent": "#F2D06B", "price": 3350,
     "blurb": "Coral organza with a whisper of gold — weightless volume for summer nights.",
     "occasion": "Brunch parties, mehendi nights"},
    {"id": 21, "name": "Aubergine Georgette", "category": "party", "material": "georgette",
     "hex": "#3B1F3E", "accent": "#C9A227", "price": 4250,
     "blurb": "Deep aubergine with gold sparkles — the under-the-radar colour of the season.",
     "occasion": "Dinner dances"},
    # ---------------- Puja wear (contd.) ----------------
    {"id": 22, "name": "Cream Tant with Red Border", "category": "puja", "material": "cotton",
     "hex": "#EFE3C8", "accent": "#B3232B", "price": 1850,
     "blurb": "Off-white tant with the classic red temple border — Bengal's everyday puja drape.",
     "occasion": "Daily puja, annaprashasan"},
    {"id": 23, "name": "Jamdani White-on-White", "category": "puja", "material": "cotton",
     "hex": "#F2EEE4", "accent": "#9AA7B0", "price": 3250,
     "blurb": "Hand-woven jamdani motifs in white on white — understated, airy, reverent.",
     "occasion": "Durga puja mornings, pandal hopping"},
    {"id": 24, "name": "Golden Tussar", "category": "puja", "material": "tussar silk",
     "hex": "#C8A951", "accent": "#8B4513", "price": 3750,
     "blurb": "Natural gold tussar with a raw, honeyed texture — a puja staple from the east.",
     "occasion": "Lakshmi puja, family pujas"},
    {"id": 25, "name": "Forest-Green Cotton", "category": "puja", "material": "cotton",
     "hex": "#1E5631", "accent": "#F5E6C8", "price": 1650,
     "blurb": "Cool green handloom with a cream border — breathes through the longest rituals.",
     "occasion": "Daily puja, vrata mornings"},
    {"id": 26, "name": "Royal-Purple Silk Blend", "category": "puja", "material": "silk blend",
     "hex": "#5B2C6F", "accent": "#F2D06B", "price": 3950,
     "blurb": "Purple with gold buttis — the colour of devotion in eastern traditions.",
     "occasion": "Kali puja, Diwali evenings"},
    {"id": 27, "name": "Saffron Cotton", "category": "puja", "material": "cotton",
     "hex": "#EE7422", "accent": "#7A1F1F", "price": 1550,
     "blurb": "Saffron handloom with a maroon dobby border — the monk-tone for long kathas.",
     "occasion": "Satyanarayan puja, house pujas"},
    {"id": 28, "name": "Rose Tant", "category": "puja", "material": "cotton",
     "hex": "#D46A8E", "accent": "#7A4A00", "price": 1700,
     "blurb": "Rose-pink tant with a fine fish-border weave — soft, summery, auspicious.",
     "occasion": "Saraswati puja"},
    {"id": 29, "name": "Ivory Chanderi", "category": "puja", "material": "silk blend",
     "hex": "#EDE6D6", "accent": "#B08D57", "price": 3050,
     "blurb": "Ivory chanderi with muted-gold buttas — light as prayer, dressy enough for the photo after.",
     "occasion": "Puja followed by family lunch"},
    {"id": 30, "name": "Maroon Tussar", "category": "puja", "material": "tussar silk",
     "hex": "#6E1B2E", "accent": "#C9A227", "price": 4150,
     "blurb": "Deep maroon tussar with gold jaal — festive mornings with a rich fall.",
     "occasion": "Ashtami, Navami mornings"},
    # ---------------- Wedding wear (contd.) ----------------
    {"id": 31, "name": "Emerald Bridal Kanjivaram", "category": "wedding", "material": "pure silk",
     "hex": "#0C5C3D", "accent": "#D4AF37", "price": 23900,
     "blurb": "Bridal green with a broad gold temple border — the south Indian heirloom in a rarer tone.",
     "occasion": "Muhurtham, receptions"},
    {"id": 32, "name": "Royal-Blue Banarasi", "category": "wedding", "material": "pure silk",
     "hex": "#1F2A5A", "accent": "#C0C0C0", "price": 18700,
     "blurb": "Midnight-blue katan with silver jangla jaal — a moonlit take on the wedding classic.",
     "occasion": "Wedding, sangeet"},
    {"id": 33, "name": "Plum Kanchipuram", "category": "wedding", "material": "pure silk",
     "hex": "#4A235A", "accent": "#D4AF37", "price": 21400,
     "blurb": "Deep plum silk with gold checks — regal, warm, photographs like a jewel.",
     "occasion": "Reception stage"},
    {"id": 34, "name": "Vermillion Kanjivaram", "category": "wedding", "material": "pure silk",
     "hex": "#BF360C", "accent": "#6B0F1A", "price": 22800,
     "blurb": "Vermillion body with a maroon korvai border — the flame-tone bridal pick.",
     "occasion": "Pheras, haldi-day rituals"},
    {"id": 35, "name": "Golden Banarasi", "category": "wedding", "material": "pure silk",
     "hex": "#C9A227", "accent": "#6B0F1A", "price": 19600,
     "blurb": "Antique-gold katan with maroon meenakari buttas — for brides who want the sun itself.",
     "occasion": "Wedding day"},
    {"id": 36, "name": "Rani-Pink Kanchipuram", "category": "wedding", "material": "pure silk",
     "hex": "#C2185B", "accent": "#D4AF37", "price": 22100,
     "blurb": "Rani pink with a gold rudraksha border — bold, joyful, unmistakably bridal.",
     "occasion": "Muhurtham, wedding lunch"},
    {"id": 37, "name": "Ivory-and-Red Kanjivaram", "category": "wedding", "material": "pure silk",
     "hex": "#F4EDE1", "accent": "#B3232B", "price": 21800,
     "blurb": "Ivory silk with a rich red korvai border — the Kerala-bride classic, woven heavier.",
     "occasion": "South Indian weddings, engagement"},
    {"id": 38, "name": "Onyx-Gold Banarasi", "category": "wedding", "material": "pure silk",
     "hex": "#1B1B1F", "accent": "#C9A227", "price": 20800,
     "blurb": "Black katan with gold jaal — the contemporary bride's reception statement.",
     "occasion": "Reception, cocktail mandap"},
    {"id": 39, "name": "Bronze Tussar Bridal", "category": "wedding", "material": "tussar silk",
     "hex": "#7B4A1F", "accent": "#D4AF37", "price": 12900,
     "blurb": "Honey-bronze tussar with gold thread work — an heirloom look at a gentler price.",
     "occasion": "Engagement, ring ceremony"},
    # ---------------- Office wear (contd.) ----------------
    {"id": 40, "name": "Charcoal Linen", "category": "office", "material": "linen",
     "hex": "#3B3F46", "accent": "#C0C7D1", "price": 2250,
     "blurb": "Charcoal linen with a silver selvedge — sharp lines that stay crisp through long days.",
     "occasion": "Daily office, performance reviews"},
    {"id": 41, "name": "Ivory Linen", "category": "office", "material": "linen",
     "hex": "#EDE7DA", "accent": "#8A8F5C", "price": 2150,
     "blurb": "Ivory linen with an olive border — quiet confidence for humid months.",
     "occasion": "Workdays, seminars"},
    {"id": 42, "name": "Olive Cotton", "category": "office", "material": "cotton",
     "hex": "#6B7A3F", "accent": "#E8DCC3", "price": 1550,
     "blurb": "Olive handloom cotton with cream accents — an earthy neutral for every meeting.",
     "occasion": "Daily wear"},
    {"id": 43, "name": "Wine Chanderi", "category": "office", "material": "silk blend",
     "hex": "#722F37", "accent": "#E8DCC3", "price": 3450,
     "blurb": "Wine chanderi with gold buttas — boardroom-ready richness without the weight.",
     "occasion": "Client presentations"},
    {"id": 44, "name": "Mustard Chettinad", "category": "office", "material": "cotton",
     "hex": "#C69214", "accent": "#4E5A6B", "price": 1750,
     "blurb": "Mustard Chettinad with a slate korvai band — bright, structured, professional.",
     "occasion": "Office, campus events"},
    {"id": 45, "name": "Smoke-Grey Georgette", "category": "office", "material": "georgette",
     "hex": "#8E9AA6", "accent": "#C0C0C0", "price": 2850,
     "blurb": "Smoke-grey georgette with a silver trim — the soft-power drape.",
     "occasion": "Conferences"},
    {"id": 46, "name": "Powder-Grey Chiffon", "category": "office", "material": "chiffon",
     "hex": "#B9BEC9", "accent": "#3E5F8A", "price": 2650,
     "blurb": "Featherweight grey chiffon with a navy edge — layers neatly under blazers.",
     "occasion": "Interviews"},
    {"id": 47, "name": "Denim-Blue Cotton", "category": "office", "material": "cotton",
     "hex": "#4A6FA5", "accent": "#C0C7D1", "price": 1650,
     "blurb": "Denim-blue handloom with a grey border — the friendliest colour in the office row.",
     "occasion": "Daily wear, field visits"},
    {"id": 48, "name": "Sand Tussar", "category": "office", "material": "tussar silk",
     "hex": "#D9C79A", "accent": "#8B6B3D", "price": 3350,
     "blurb": "Sand-gold tussar with an antique-brass border — warm neutrals for client-facing days.",
     "occasion": "Meetings, off-sites"},
]

CATEGORIES = [
    {"key": "party",   "label": "Party Wear",   "tagline": "Shimmer, drape & after-dark colours",
     "icon": "✦"},
    {"key": "puja",    "label": "Puja Wear",    "tagline": "Breathable cottons in auspicious tones",
     "icon": "🪔"},
    {"key": "wedding", "label": "Wedding Wear", "tagline": "Heirloom silks with real zari",
     "icon": "💍"},
    {"key": "office",  "label": "Office Wear",  "tagline": "Structured, wrinkle-tolerant, quiet colours",
     "icon": "💼"},
]

MATERIAL_NOTES = {
    "georgette":     {"feel": "Flowy, slightly sheer, crepe-like twist",
                      "care": "Dry clean; cool iron inside-out",
                      "season": "All-season evening favourite",
                      "drape": "Soft flutes; hugs curves gently",
                      "best_for": "Evening events where movement photographs well"},
    "chiffon":       {"feel": "Feather-light, sheer, slippery-smooth",
                      "care": "Dry clean; never wring",
                      "season": "Summer & humid evenings",
                      "drape": "Fluid waterfall drape; zero bulk",
                      "best_for": "Petite frames — adds no volume at all"},
    "silk blend":    {"feel": "Silk hand-feel with synthetic resilience",
                      "care": "Gentle hand wash or dry clean",
                      "season": "Festive autumn–winter",
                      "drape": "Holds pleats sharp, pallu stays put",
                      "best_for": "Structured looks that survive long events"},
    "pure silk":     {"feel": "Mulberry-skin softness with real zari weight",
                      "care": "Dry clean only; store in muslin, refold quarterly",
                      "season": "Wedding season & winter",
                      "drape": "Majestic, sculptural pleats",
                      "best_for": "Heirloom occasions — the saree outlives trends"},
    "cotton":        {"feel": "Cool, crisp, increasingly soft with washes",
                      "care": "Machine-wash gentle; starch the border",
                      "season": "Summer & humid months",
                      "drape": "Sharp knife pleats; can crease",
                      "best_for": "Long hours — puja marathons and 9-hour workdays"},
    "organza blend": {"feel": "Crisp, translucent, whisper-light",
                      "care": "Dry clean; steam only",
                      "season": "All-season (layered)",
                      "drape": "Architectural, holds its own shape",
                      "best_for": "Adding presence without weight — great for smaller frames"},
    "tussar silk":   {"feel": "Raw, textured, honey-gold with natural slubs",
                      "care": "Dry clean; store folded in muslin",
                      "season": "Autumn–winter & puja season",
                      "drape": "Full-bodied with a soft crispness",
                      "best_for": "Festive mornings and heirloom looks on a gentler budget"},
    "linen":         {"feel": "Cool, dry-handed, elegantly rumpled",
                      "care": "Gentle machine wash; press while damp",
                      "season": "Summer",
                      "drape": "Structured, sharp-edged pleats",
                      "best_for": "Long workdays in the heat"},
}

# --------------------------------------------------------------------------
# Belt palette — 14 shades the stylist can recommend.
# families: light/dark drive contrast; neutral/metal/drive colour.
# --------------------------------------------------------------------------
BELTS = [
    {"key": "gold",        "name": "Antique Gold",   "hex": "#C9A227", "family": "metal"},
    {"key": "rose_gold",   "name": "Rose Gold",      "hex": "#B76E79", "family": "metal"},
    {"key": "silver",      "name": "Polished Silver","hex": "#C0C0C0", "family": "metal"},
    {"key": "antique_brass","name": "Antique Brass", "hex": "#8B6B3D", "family": "metal"},
    {"key": "cream",       "name": "Cream Silk",     "hex": "#F2E9D8", "family": "light"},
    {"key": "ivory",       "name": "Ivory Pearl",    "hex": "#F4EDE1", "family": "light"},
    {"key": "maroon",      "name": "Deep Maroon",    "hex": "#6B0F1A", "family": "dark"},
    {"key": "navy",        "name": "Midnight Navy",  "hex": "#1F2A5A", "family": "dark"},
    {"key": "emerald",     "name": "Emerald Green",  "hex": "#0F6B4F", "family": "drive"},
    {"key": "teal",        "name": "Peacock Teal",   "hex": "#175E54", "family": "drive"},
    {"key": "rust",        "name": "Burnt Rust",     "hex": "#8B3A0F", "family": "drive"},
    {"key": "mustard",     "name": "Mustard Silk",   "hex": "#D9A400", "family": "drive"},
    {"key": "black",       "name": "Onyx Black",     "hex": "#17161A", "family": "dark"},
    {"key": "blush",       "name": "Blush Pink",     "hex": "#E8B4C8", "family": "light"},
]

# --------------------------------------------------------------------------
# Body-type knowledge base — the rubric the stylist quotes from.
# --------------------------------------------------------------------------
BODY_TYPES = {
    "pear": {
        "name": "Pear (triangle)",
        "traits": "Hips wider than shoulders; defined waist.",
        "saree_advice": "Cotton and organza blends keep the upper body crisp while the pallu falls straight — drape pleats toward the side to balance the hip line. Avoid bulky border bands at the hem.",
        "materials": ["cotton", "organza blend", "silk blend"],
        "palette": ["A-line drape, thin border, pallu pinned high on the shoulder"],
    },
    "apple": {
        "name": "Apple (inverted)",
        "traits": "Fuller midriff; shoulders broader than hips.",
        "saree_advice": "Georgette and chiffon skim the middle without adding structure; skip stiff cotton at the waist and let the pallu fall open over the arm to lengthen the torso.",
        "materials": ["georgette", "chiffon", "silk blend"],
        "palette": ["Open pallu, low-pleat drape, soft flowy fall"],
    },
    "hourglass": {
        "name": "Hourglass",
        "traits": "Shoulders and hips balanced; small waist.",
        "saree_advice": "Pure silk and silk blends honour the waist-to-hip ratio — a defined waist-belt over the pleats works beautifully. Most materials flatter; the choice becomes about occasion, not silhouette.",
        "materials": ["pure silk", "silk blend", "chiffon"],
        "palette": ["Waist-defined drape with a styled belt over the pleats"],
    },
    "rectangle": {
        "name": "Rectangle (athletic)",
        "traits": "Straight shoulder-to-hip line; little waist definition.",
        "saree_advice": "Heavy silks and wide borders create the curves the cut itself doesn't — organza blends add structure at the shoulder. Use bold borders and pleated pallus to carve dimension.",
        "materials": ["pure silk", "silk blend", "organza blend"],
        "palette": ["Bold wide border, heavily pleated pallu, structured blouse"],
    },
    "petite": {
        "name": "Petite (short frame)",
        "traits": "Height under 5'4\"; compact frame.",
        "saree_advice": "Chiffon and georgette add zero visual weight — keep borders slim and motifs small so the eye travels vertically. Skip bulky kanjivaram pleats that shorten the line.",
        "materials": ["chiffon", "georgette", "cotton"],
        "palette": ["Slim border, small motifs, high-waist pleats to elongate"],
    },
}

# --------------------------------------------------------------------------
# Customization pricing — three independent tracks.
# --------------------------------------------------------------------------
CUSTOM_PRICING = {
    "blouse": {
        "label": "Pre-stitched Blouse",
        "desc": "Lined, boned at the side, concealed side-zip, hook-and-eye finish. Ready in 4–6 days.",
        "base": 900,
        "options": [
            {"key": "fit",  "label": "Fit",           "type": "select",
             "choices": [("regular", "Regular fit", 0), ("semi", "Semi-fitted", 200), ("tailored", "Fully tailored", 450)]},
            {"key": "sleeve", "label": "Sleeve",      "type": "select",
             "choices": [("sleeveless", "Sleeveless", 0), ("cap", "Cap sleeve", 150), ("full", "Full sleeve", 350), ("bell", "Bell sleeve", 500)]},
            {"key": "neck", "label": "Neckline",      "type": "select",
             "choices": [("round", "Round", 0), ("v", "V-neck", 100), ("boat", "Boat neck", 250), ("sweetheart", "Sweetheart", 400)]},
            {"key": "lining", "label": "Lining",      "type": "radio",
             "choices": [("none", "No lining", 0), ("cotton", "Cotton lining", 150), ("silk", "Silk lining", 400)]},
            {"key": "embroidery", "label": "Embroidery", "type": "radio",
             "choices": [("none", "None", 0), ("aari", "Aari work", 1200), ("zardosi", "Zardosi work", 2200)]},
        ],
        "fields": [
            {"key": "bust", "label": "Bust (inches)", "type": "number", "required": True},
            {"key": "waist", "label": "Waist (inches)", "type": "number", "required": True},
        ],
    },
    "saree_fall_pico": {
        "label": "Saree Fall & Pico",
        "desc": "Fall stitched with a rolled hem (pico) on all open edges — crisp pleats, no fraying.",
        "base": 350,
        "options": [
            {"key": "fall_type", "label": "Fall material", "type": "select",
             "choices": [("cotton_fall", "Cotton fall", 0), ("satin_fall", "Satin fall", 150), ("opaque_fall", "Opaque premium fall", 300)]},
            {"key": "pico", "label": "Pico stitch", "type": "radio",
             "choices": [("yes", "Yes, all edges", 200), ("no", "Fall only", 0)]},
            {"key": "length", "label": "Length adjust", "type": "radio",
             "choices": [("none", "Keep as-is", 0), ("trim", "Trim to my height", 250)]},
        ],
        "fields": [
            {"key": "height", "label": "Your height (inches, if trimming)", "type": "number", "required": False},
        ],
    },
    "belt": {
        "label": "Couple Belt (custom)",
        "desc": "Hand-finished belt in the shade your AI stylist pairs with the saree — groom's strap and bride's waist-belt from the same hide/dye lot.",
        "base": 800,
        "options": [
            {"key": "shade", "label": "Shade", "type": "select",
             "choices": [("stylist", "Let the AI stylist pick", 0)] + [(b["key"], b["name"], 0) for b in BELTS]},
            {"key": "buckle", "label": "Buckle", "type": "select",
             "choices": [("matte", "Matte pin", 0), ("gold", "Gold-tone", 250), ("silver", "Silver-tone", 250), ("engraved", "Engraved initial", 600)]},
            {"key": "width", "label": "Width", "type": "select",
             "choices": [("slim", "Slim 2.5 cm", 0), ("classic", "Classic 3.5 cm", 100), ("wide", "Wide 4.5 cm", 200)]},
            {"key": "personalise", "label": "Personalisation", "type": "radio",
             "choices": [("none", "None", 0), ("emboss", "Emboss couple initials", 350), ("date", "Emboss date", 350)]},
        ],
        "fields": [
            {"key": "waist", "label": "Waist (inches)", "type": "number", "required": True},
        ],
    },
}


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS custom_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type  TEXT NOT NULL,          -- blouse | saree_fall_pico | belt
    saree_id   INTEGER,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL,
    notes      TEXT,
    choices    TEXT NOT NULL,          -- JSON
    price      INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def get_sarees(category=None, material=None):
    rows = [dict(s) for s in SAREES]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if material:
        rows = [r for r in rows if r["material"] == material]
    for r in rows:
        r["material_info"] = MATERIAL_NOTES[r["material"]]
    return rows


def get_saree(saree_id):
    for s in SAREES:
        if s["id"] == saree_id:
            d = dict(s)
            d["material_info"] = MATERIAL_NOTES[s["material"]]
            return d
    return None


def materials_for_category(category):
    return sorted({s["material"] for s in SAREES if s["category"] == category})


def save_custom_request(item_type, saree_id, name, phone, notes, choices, price):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO custom_requests (item_type, saree_id, name, phone, notes, choices, price)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item_type, saree_id, name, phone, notes,
             json.dumps(choices), price))
        return cur.lastrowid
