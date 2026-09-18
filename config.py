"""Global configuration for the saree studio site."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

# --- Database ---
DB_PATH = os.environ.get("SS_DB_PATH", os.path.join(INSTANCE_DIR, "saree_studio.db"))

# --- Flask ---
SECRET_KEY = os.environ.get("SS_SECRET_KEY", "dev-secret-change-me")
DEBUG = os.environ.get("SS_DEBUG", "0") == "1"   # reloader off by default (stable pid)

# --- Server ---
HOST = os.environ.get("SS_HOST", "127.0.0.1")    # 0.0.0.0 to expose on LAN
PORT = int(os.environ.get("SS_PORT", "5002"))

# --- ML ---
MODELS_DIR = os.path.join(BASE_DIR, "ml")
os.makedirs(MODELS_DIR, exist_ok=True)
BELT_MODEL_PATH = os.path.join(MODELS_DIR, "belt_pairing.joblib")
MODEL_META_PATH = os.path.join(MODELS_DIR, "model_meta.json")
