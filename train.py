"""Train the belt-pairing model: python -m saree_studio.train"""
from .stylist import train_model

if __name__ == "__main__":
    meta = train_model()
    print("Belt-pairing model trained.")
    print("  rows:", meta["n_rows"])
    print("  CV R2:", meta["cv_r2_mean"], "+/-", meta["cv_r2_std"])
