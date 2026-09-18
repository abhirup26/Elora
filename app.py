"""Flask app — Elara saree studio with AI stylist."""
import os

from flask import Flask, jsonify, render_template, request

from . import catalogue as cat
from . import photos as photo_store
from . import stylist
from .config import DEBUG, HOST, PORT, SECRET_KEY
from .designs import design_label

app = Flask(__name__)
app.secret_key = SECRET_KEY


def _with_img(saree):
    s = dict(saree)
    s["img"] = photo_store.photo_for(s["id"])
    s["design"] = design_label(s["id"])
    return s


def _with_img_list(sarees):
    return [_with_img(s) for s in sarees]


@app.context_processor
def inject_globals():
    return {"CATEGORIES": cat.CATEGORIES}


@app.route("/")
def home():
    featured = _with_img_list(cat.get_sarees()[:6])
    return render_template("index.html", featured=featured)


@app.route("/collection")
def collection():
    category = request.args.get("category") or None
    material = request.args.get("material") or None
    sarees = _with_img_list(cat.get_sarees(category=category, material=material))
    all_materials = sorted(cat.MATERIAL_NOTES.keys())
    active = next((c for c in cat.CATEGORIES if c["key"] == category), None)
    return render_template("collection.html", sarees=sarees,
                           all_materials=all_materials,
                           active_category=active,
                           sel_category=category, sel_material=material)


@app.route("/saree/<int:saree_id>")
def saree_detail(saree_id):
    saree = cat.get_saree(saree_id)
    if saree is None:
        return render_template("404.html"), 404
    saree = _with_img(saree)
    related = [s for s in _with_img_list(cat.get_sarees(category=saree["category"]))
               if s["id"] != saree_id][:3]
    try:
        pick = stylist.recommend_belt(saree_id, saree["category"])["recommendations"][0]
    except Exception:
        pick = None
    return render_template("saree.html", saree=saree, related=related, belt_pick=pick)


@app.route("/api/photo-attribution")
def photo_attribution():
    """Public attribution for every photo shown on the site."""
    items = []
    for s in cat.SAREES:
        img = photo_store.photo_for(s["id"])
        if img["kind"] == "photo":
            items.append({"saree": s["name"], "url": img["url"],
                          "source_url": img["source_url"], "credit": img["credit"]})
    return jsonify({"count": len(items), "images": items})


# --------------------------------------------------------------------------
# AI stylist
# --------------------------------------------------------------------------
@app.route("/stylist")
def stylist_page():
    sarees = _with_img_list(cat.get_sarees())
    body_types = {k: v for k, v in cat.BODY_TYPES.items()}
    return render_template("stylist.html", sarees=sarees, body_types=body_types)


@app.route("/api/stylist/belt", methods=["POST"])
def api_belt():
    data = request.get_json(silent=True) or {}
    saree_id = data.get("saree_id")
    occasion = data.get("occasion", "party")
    if not saree_id or occasion not in ("party", "puja", "wedding", "office"):
        return jsonify({"error": "saree_id and a valid occasion are required"}), 400
    result = stylist.recommend_belt(saree_id, occasion)
    if result is None:
        return jsonify({"error": "unknown saree_id"}), 404
    return jsonify(result)


@app.route("/api/stylist/body", methods=["POST"])
def api_body():
    data = request.get_json(silent=True) or {}
    key = stylist.parse_body_type(data.get("shoulders"), data.get("waist"),
                                  data.get("hips"), data.get("height"))
    if key is None:
        return jsonify({"error": "shoulders, waist and hips (inches) are required"}), 400
    advice = stylist.body_type_advice(key, data.get("height"))
    advice["matched_key"] = key
    return jsonify(advice)


@app.route("/body-type")
def body_type_page():
    return render_template("bodytype.html", body_types=cat.BODY_TYPES)


# --------------------------------------------------------------------------
# Customization studio
# --------------------------------------------------------------------------
@app.route("/customize")
def customize_page():
    sarees = cat.get_sarees()
    return render_template("customize.html", pricing=cat.CUSTOM_PRICING,
                           sarees=sarees)


def _compute_price(track_key, form):
    track = cat.CUSTOM_PRICING[track_key]
    price = track["base"]
    choices = {}
    for opt in track["options"]:
        val = form.get(opt["key"], "")
        choices[opt["key"]] = val
        for ckey, _label, add in opt["choices"]:
            if ckey == val:
                price += add
                break
    return price, choices


@app.route("/api/customize/price", methods=["POST"])
def api_custom_price():
    data = request.get_json(silent=True) or {}
    track = data.get("item")
    if track not in cat.CUSTOM_PRICING:
        return jsonify({"error": "unknown item"}), 400
    price, choices = _compute_price(track, data.get("form", {}))
    return jsonify({"price": price, "choices": choices})


@app.route("/api/customize/request", methods=["POST"])
def api_custom_request():
    data = request.get_json(silent=True) or {}
    track = data.get("item")
    if track not in cat.CUSTOM_PRICING:
        return jsonify({"error": "unknown item"}), 400
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if len(name) < 2 or len(phone) < 8:
        return jsonify({"error": "Please share your name and a valid phone number."}), 400
    price, choices = _compute_price(track, data.get("form", {}))
    saree_id = data.get("saree_id")
    req_id = cat.save_custom_request(track, saree_id, name, phone,
                                     (data.get("notes") or "").strip(),
                                     choices, price)
    return jsonify({"ok": True, "request_id": req_id, "price": price,
                    "track_label": cat.CUSTOM_PRICING[track]["label"]})


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "elara"})


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


def create_app():
    cat.init_db()
    photo_store.ensure_designs()   # SVG design illustrations (if missing)
    return app


if __name__ == "__main__":
    create_app()
    print(f"Elara -> http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
