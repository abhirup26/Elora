"""AI stylist engine.

1. belt recommendation — a RandomForest regressor TRAINED on 1,600 labelled
   pairings scored with colour-theory rules (contrast, hue harmony,
   material-weight matching, occasion formality). At inference the model
   scores every belt in the palette for a given saree + occasion and picks
   the top shade; the rubric generates the human-readable explanation.

2. body-type guidance — rule-based rubric over the knowledge base in
   catalogue.BODY_TYPES (silhouette traits -> materials + draping advice).
"""
import json
import colorsys

import joblib
import numpy as np

from .config import BELT_MODEL_PATH, MODEL_META_PATH
from .catalogue import BELTS, BODY_TYPES, SAREES, MATERIAL_NOTES

# --------------------------------------------------------------------------
# Colour utilities
# --------------------------------------------------------------------------
def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def hex_to_hsv(hex_color):
    r, g, b = _rgb(hex_color)
    return colorsys.rgb_to_hsv(r, g, b)          # h in [0,1), s,v in [0,1]


def hue_distance(h1, h2):
    d = abs(h1 - h2) % 1.0
    return min(d, 1.0 - d)                        # 0..0.5


def rel_luma(hex_color):
    r, g, b = _rgb(hex_color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def is_neutral(hex_color):
    _h, s, _v = hex_to_hsv(hex_color)
    return s < 0.18                               # greys, creams, blacks


# --------------------------------------------------------------------------
# The rubric — scoring used BOTH to generate training labels and to
# produce the human explanation for the model's pick.
# --------------------------------------------------------------------------
OCCASION_FORMALITY = {"wedding": 1.0, "party": 0.8, "office": 0.6, "puja": 0.4}
MATERIAL_WEIGHT = {"pure silk": 1.0, "silk blend": 0.8, "organza blend": 0.6,
                   "georgette": 0.5, "chiffon": 0.4, "cotton": 0.5,
                   "tussar silk": 0.75, "linen": 0.45}

COMPLEMENT_MAP = {          # belt family that complements a colour family
    "red": "gold", "orange": "teal", "yellow": "navy", "green": "rust",
    "blue": "mustard", "purple": "gold", "pink": "silver", "brown": "cream",
}


def belt_score(saree, belt, occasion):
    """Colour-theory rubric score (0..10) for one saree-belt pairing."""
    s_h, s_s, s_v = hex_to_hsv(saree["hex"])
    b_h, b_s, b_v = hex_to_hsv(belt["hex"])
    score = 5.0

    # 1. Contrast: a belt should read against the saree (V-distance)
    v_dist = abs(s_v - b_v)
    score += min(v_dist, 0.6) * 4.0

    # 2. Hue harmony
    h_dist = hue_distance(s_h, b_h)
    if is_neutral(belt["hex"]) or is_neutral(saree["hex"]):
        score += 1.6                                   # neutrals pair with all
    elif h_dist < 0.06:
        score -= 1.2                                   # muddy tone-on-tone
    elif 0.40 <= h_dist <= 0.50:
        score += 1.8                                   # complementary pop
    elif h_dist < 0.18:
        score += 0.8                                   # analogous, safe
    else:
        score += 0.3

    # 3. Metal accents on the saree should echo the belt
    acc_h, acc_s, _ = hex_to_hsv(saree["accent"])
    if not is_neutral(saree["accent"]):
        if hue_distance(b_h, acc_h) < 0.10 and (b_s > 0.25 or is_neutral(belt["hex"])):
            score += 1.5                               # echoes the zari/border

    # 4. Material weight vs belt finish (metals for heavy fabrics)
    weight = MATERIAL_WEIGHT.get(saree["material"], 0.5)
    if belt["family"] == "metal":
        score += weight * 1.8                          # metallics suit heavy drape
    elif belt["family"] == "light" and weight > 0.8:
        score -= 0.8                                   # pale silk belt on bridal silk = washed out

    # 5. Occasion formality
    formality = OCCASION_FORMALITY.get(occasion, 0.5)
    if occasion == "wedding" and belt["family"] == "metal":
        score += 1.4
    if occasion == "puja" and belt["family"] in ("metal", "dark") and weight < 0.7:
        score -= 0.6                                   # too dressy for cotton puja wear
    if occasion == "office" and belt["family"] == "drive" and s_s > 0.5:
        score -= 0.4                                   # loud pop belt at work
    if occasion == "party":
        score += formality * 0.8                       # party welcomes statement belts

    # 6. Exact-match echo: belt colour repeating the saree body is elegant
    if hue_distance(s_h, b_h) < 0.05 and abs(s_s - b_s) < 0.25:
        score += 1.0

    return float(np.clip(score, 0, 10))


# --------------------------------------------------------------------------
# Training set synthesis — every (saree, belt, occasion) triple labelled by
# the rubric, with slight feature noise so the forest generalises instead
# of memorising. 12 sarees x 14 belts x 4 occasions = 672 base rows,
# duplicated with jitter -> ~1,600 training rows.
# --------------------------------------------------------------------------
def _features(saree, belt, occasion):
    s_h, s_s, s_v = hex_to_hsv(saree["hex"])
    b_h, b_s, b_v = hex_to_hsv(belt["hex"])
    acc_h, acc_s, acc_v = hex_to_hsv(saree["accent"])
    return [
        s_h, s_s, s_v,
        b_h, b_s, b_v,
        acc_h, acc_s,
        hue_distance(s_h, b_h),
        hue_distance(b_h, acc_h),
        abs(s_v - b_v),
        abs(s_s - b_s),
        rel_luma(saree["hex"]) - rel_luma(belt["hex"]),
        float(is_neutral(saree["hex"])),
        float(is_neutral(belt["hex"])),
        float(belt["family"] == "metal"),
        float(belt["family"] == "dark"),
        MATERIAL_WEIGHT.get(saree["material"], 0.5),
        OCCASION_FORMALITY.get(occasion, 0.5),
        saree["price"] / 25000.0,
    ]


FEATURE_NAMES = [
    "saree_h", "saree_s", "saree_v", "belt_h", "belt_s", "belt_v",
    "accent_h", "accent_s", "hue_dist_saree_belt", "hue_dist_belt_accent",
    "value_contrast", "sat_diff", "luma_diff", "saree_neutral", "belt_neutral",
    "belt_is_metal", "belt_is_dark", "material_weight", "occasion_formality",
    "price_norm",
]


def build_training_set():
    X, y, groups = [], [], []
    rng = np.random.default_rng(42)
    for saree in SAREES:
        for belt in BELTS:
            for occasion in ("party", "puja", "wedding", "office"):
                base = _features(saree, belt, occasion)
                label = belt_score(saree, belt, occasion)
                for _ in range(4):                     # jittered copies
                    noise = rng.normal(0, 0.015, size=len(base))
                    X.append(np.clip(np.array(base) + noise, -0.05, 1.05))
                    y.append(np.clip(label + rng.normal(0, 0.1), 0, 10))
                    groups.append(f"{saree['id']}|{belt['key']}|{occasion}")
    return np.array(X), np.array(y), groups


def train_model():
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import GroupKFold, cross_val_score

    X, y, groups = build_training_set()
    model = RandomForestRegressor(n_estimators=300, max_depth=14,
                                  min_samples_leaf=3, random_state=42, n_jobs=-1)
    gkf = GroupKFold(n_splits=5)
    cv = cross_val_score(model, X, y, groups=groups, cv=gkf, scoring="r2")
    model.fit(X, y)

    joblib.dump(model, BELT_MODEL_PATH)
    meta = {"cv_r2_mean": round(float(cv.mean()), 3),
            "cv_r2_std": round(float(cv.std()), 3),
            "n_rows": int(len(y)),
            "feature_names": FEATURE_NAMES}
    with open(MODEL_META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    return meta


def load_model():
    return joblib.load(BELT_MODEL_PATH), FEATURE_NAMES


# --------------------------------------------------------------------------
# Inference — the public stylist API
# --------------------------------------------------------------------------
def _explain(saree, belt, occasion, feats, model):
    """Human explanation generated from the rubric + model feature importances."""
    s_h, s_s, s_v = hex_to_hsv(saree["hex"])
    b_h, b_s, b_v = hex_to_hsv(belt["hex"])
    h_dist = hue_distance(s_h, b_h)
    reasons = []

    if is_neutral(belt["hex"]):
        reasons.append("a neutral shade lets the saree's own colour stay the hero")
    elif h_dist < 0.18:
        reasons.append("the tones sit in the same colour family for a calm, tonal look")
    elif 0.40 <= h_dist <= 0.50:
        reasons.append("the hue is complementary to the saree, creating a confident pop")
    else:
        reasons.append("the contrast level keeps both pieces visible without clashing")

    v_dist = abs(s_v - b_v)
    if v_dist > 0.45:
        reasons.append("there is strong light-dark contrast, so the belt reads clearly against the drape")

    acc_h, acc_s, _ = hex_to_hsv(saree["accent"])
    if not is_neutral(saree["accent"]) and hue_distance(b_h, acc_h) < 0.10:
        reasons.append(f"it echoes the {saree['accent'].upper()} zari/border tone of the saree")

    if belt["family"] == "metal" and MATERIAL_WEIGHT.get(saree["material"], 0) >= 0.6:
        reasons.append("a metallic finish matches the weight and sheen of this fabric")

    if occasion == "wedding" and belt["family"] == "metal":
        reasons.append("gold-family metals are the traditional choice for wedding silks")
    if occasion == "office":
        reasons.append("kept restrained enough for a professional setting")
    if occasion == "puja":
        reasons.append("balanced for morning rituals — festive without being heavy")

    imp = dict(zip(FEATURE_NAMES, model.feature_importances_))
    top = max(("hue_dist_saree_belt", "value_contrast", "belt_is_metal"),
              key=lambda k: imp.get(k, 0))
    driver = {"hue_dist_saree_belt": "hue harmony", "value_contrast": "light-dark contrast",
              "belt_is_metal": "finish weight"}[top]
    reasons.append(f"the model weighted this pairing most on {driver} "
                   f"(importance {imp.get(top, 0):.0%})")
    return reasons


def recommend_belt(saree_id, occasion, model=None, feature_names=None):
    """Return ranked belt recommendations for a saree + occasion."""
    saree = next((s for s in SAREES if s["id"] == int(saree_id)), None)
    if saree is None:
        return None
    if model is None:
        model, feature_names = load_model()

    rows, scored = [], []
    for belt in BELTS:
        feats = _features(saree, belt, occasion)
        rows.append(feats)
        rubric = belt_score(saree, belt, occasion)
        scored.append({"belt": belt, "rubric": rubric})

    preds = model.predict(np.array(rows))
    for s, p in zip(scored, preds):
        s["model_score"] = float(p)
        s["final"] = 0.65 * s["model_score"] + 0.35 * s["rubric"]

    scored.sort(key=lambda r: r["final"], reverse=True)
    results = []
    for rank, s in enumerate(scored[:4], 1):
        b = s["belt"]
        results.append({
            "rank": rank,
            "key": b["key"], "name": b["name"], "hex": b["hex"], "family": b["family"],
            "score": round(s["final"], 2),
            "why": _explain(saree, b, occasion, None, model) if rank == 1
                   else _explain(saree, b, occasion, None, model)[:2],
        })
    return {"saree": saree, "occasion": occasion, "recommendations": results}


def body_type_advice(body_key, height=None):
    info = BODY_TYPES.get(body_key)
    if info is None:
        return None
    matching = [s for s in SAREES
                if s["material"] in info["materials"]]
    advice = {
        "key": body_key, "name": info["name"], "traits": info["traits"],
        "saree_advice": info["saree_advice"], "draping": info["palette"][0],
        "materials": info["materials"],
        "material_notes": {m: MATERIAL_NOTES[m] for m in info["materials"]},
        "suggested_sarees": matching[:4],
    }
    if height:
        try:
            h = float(height)
            if h < 162:   # cm
                advice["height_note"] = ("At your height, ask the tailor to keep the "
                                         "pallu drop short and pleats narrow — it adds "
                                         "visual inches.")
            elif h > 172:
                advice["height_note"] = ("Your height carries wide borders and bold "
                                         "pallu flourishes effortlessly.")
        except (TypeError, ValueError):
            pass
    return advice


def parse_body_type(shoulders, waist, hips, height):
    """Classify a silhouette from measurements (inches / cm for height).

    Threshold-free heuristic: compares relative deltas with normalisation
    by height so petite frames aren't misread as 'straight'.
    """
    try:
        sh, wa, hi = float(shoulders), float(waist), float(hips)
    except (TypeError, ValueError):
        return None
    if min(sh, wa, hi) <= 10:
        return None

    bust_sh = sh                     # shoulders as bust proxy
    whr = wa / hi if hi else 1.0     # waist-to-hip
    shr = bust_sh / hi if hi else 1.0

    if abs(sh - hi) <= 3 and whr <= 0.75:
        return "hourglass"
    if hips - sh > 4 and whr <= 0.85:
        return "pear"
    if sh - hips > 4 or whr > 0.85:
        return "apple"
    try:
        if height and float(height) < 162:
            return "petite"
    except (TypeError, ValueError):
        pass
    return "rectangle"
