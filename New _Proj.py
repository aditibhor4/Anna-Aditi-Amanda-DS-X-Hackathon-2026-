"""
TERIA: rapid microbial testing, starting with cosmetics.
Hackachusetts 2026, Healthcare & Biotech track (challenge H4).

ONE-FILE VERSION. Everything the app needs is in this file, plus your dataset:
put "possibly helpful data set.zip" (or the .tsv inside it) in the SAME folder as this file.

SETUP (once, in the terminal):
    python3 -m pip install streamlit pandas numpy plotly pillow

RUN (either way works):
    python3 -m streamlit run teria_app.py
    or press the Run button: the file starts Streamlit for you.

PAGES
    Home            landing page (matches the Lovable design)
    Evidence        real data: FDA adverse event reports + Open Beauty Facts products
    Test a product  add a product (label photo / dataset / shelf), simulated strip, 0-100 score
    Scan          photo reader for the test card + formula check
    My shelf      demo user's products, toss-by dates, results
    Lab           researcher dashboard (simulated experiments)
    Find product  search the real Open Beauty Facts dataset
    About         pitch and roadmap
"""
import glob
import io
import math
import os
import random
import re
import subprocess
import sys
import zipfile
import zlib
from datetime import date, datetime

# ---------------------------------------------------------------------------
# If someone runs "python teria_app.py" (or presses Run), relaunch with Streamlit.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        from streamlit import runtime
        inside_streamlit = runtime.exists()
    except Exception:
        inside_streamlit = False
    if not inside_streamlit:
        # Install anything missing (first run only), then start the app with Streamlit.
        needed = {"streamlit": "streamlit", "pandas": "pandas", "numpy": "numpy", "plotly": "plotly", "PIL": "pillow"}
        missing = []
        for module, package in needed.items():
            try:
                __import__(module)
            except ImportError:
                missing.append(package)
        if missing:
            print(f"First run: installing {', '.join(missing)}. This takes a minute or two...")
            cmd = [sys.executable, "-m", "pip", "install", *missing]
            if subprocess.call(cmd) != 0 and subprocess.call(cmd + ["--user"]) != 0:
                sys.exit("Install failed. Copy the error above and ask for help.")
        if sys.platform == "darwin":
            try:
                __import__("ocrmac")
            except ImportError:   # Apple's built-in text recognition, for reading labels (optional)
                print("Installing ocrmac for the label reader...")
                if subprocess.call([sys.executable, "-m", "pip", "install", "ocrmac"]) != 0:
                    subprocess.call([sys.executable, "-m", "pip", "install", "--user", "ocrmac"])
        print("Starting Teria. Your browser will open. Press Ctrl+C here to stop.")
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today()

# ===========================================================================
# 1. DATA
# ===========================================================================

# REAL: openFDA cosmetic adverse event reports (api.fda.gov/cosmetic/event.json), pulled 2026-10-24.
# total_reports = reports naming a product with that word; infection_mentions = infection-related reaction terms.
FDA = pd.DataFrame([
    {"category": "mascara",    "eye_area": True,  "total_reports": 144,  "infection_mentions": 60},
    {"category": "deodorant",  "eye_area": False, "total_reports": 309,  "infection_mentions": 100},
    {"category": "tattoo ink", "eye_area": False, "total_reports": 571,  "infection_mentions": 184},
    {"category": "eyeliner",   "eye_area": True,  "total_reports": 72,   "infection_mentions": 20},
    {"category": "lotion",     "eye_area": False, "total_reports": 553,  "infection_mentions": 40},
    {"category": "shampoo",    "eye_area": False, "total_reports": 2100, "infection_mentions": 57},
])

# SIMULATED: product catalog and one demo user's shelf
PRODUCTS = {
    "p01": {"name": "Volumizing Mascara", "category": "mascara", "base": "water", "packaging": "tube_wand", "pao": 3, "eye": True},
    "p02": {"name": "Liquid Eyeliner", "category": "eyeliner", "base": "water", "packaging": "tube_wand", "pao": 6, "eye": True},
    "p03": {"name": "Eye Cream", "category": "eye cream", "base": "water", "packaging": "jar", "pao": 6, "eye": True},
    "p04": {"name": "Liquid Foundation", "category": "foundation", "base": "water", "packaging": "pump", "pao": 12, "eye": False},
    "p05": {"name": "Cream Foundation", "category": "foundation", "base": "oil", "packaging": "jar", "pao": 12, "eye": False},
    "p06": {"name": "Liquid Concealer", "category": "concealer", "base": "water", "packaging": "tube_wand", "pao": 12, "eye": True},
    "p07": {"name": "Daily Moisturizer", "category": "moisturizer", "base": "water", "packaging": "pump", "pao": 12, "eye": False},
    "p08": {"name": "Rich Night Cream", "category": "moisturizer", "base": "water", "packaging": "jar", "pao": 12, "eye": False},
    "p09": {"name": "Lip Gloss", "category": "lip gloss", "base": "oil", "packaging": "tube_wand", "pao": 12, "eye": False},
    "p10": {"name": "Lip Balm Pot", "category": "lip balm", "base": "oil", "packaging": "jar", "pao": 12, "eye": False},
    "p11": {"name": "Face Oil", "category": "face oil", "base": "oil", "packaging": "dropper", "pao": 6, "eye": False},
    "p12": {"name": "Vitamin C Serum", "category": "serum", "base": "water", "packaging": "dropper", "pao": 6, "eye": False},
    "p13": {"name": "Micellar Water", "category": "cleanser", "base": "water", "packaging": "bottle", "pao": 12, "eye": True},
    "p14": {"name": "Cream Blush", "category": "blush", "base": "oil", "packaging": "jar", "pao": 12, "eye": False},
    "p15": {"name": "Powder Blush", "category": "blush", "base": "powder", "packaging": "compact", "pao": 24, "eye": False},
    "p16": {"name": "Eyeshadow Palette", "category": "eyeshadow", "base": "powder", "packaging": "compact", "pao": 24, "eye": True},
    "p17": {"name": "Sunscreen SPF 50", "category": "sunscreen", "base": "water", "packaging": "tube", "pao": 12, "eye": False},
    "p18": {"name": "Sheet Mask Essence", "category": "mask", "base": "water", "packaging": "jar", "pao": 6, "eye": False},
    "p19": {"name": "Body Lotion", "category": "lotion", "base": "water", "packaging": "pump", "pao": 12, "eye": False},
    "p20": {"name": "Brow Gel", "category": "brow gel", "base": "water", "packaging": "tube_wand", "pao": 6, "eye": True},
}
SHELF = [
    {"id": "p01", "opened": "2026-05-02", "test": {"date": "2026-10-20", "result": "contaminated", "signal": 0.74}},
    {"id": "p04", "opened": "2026-06-15", "test": {"date": "2026-10-20", "result": "clean", "signal": 0.18}},
    {"id": "p08", "opened": "2026-01-10", "test": {"date": "2026-10-18", "result": "unclear", "signal": 0.47}},
    {"id": "p09", "opened": "2026-08-01", "test": None},
    {"id": "p11", "opened": "2026-03-22", "test": {"date": "2026-10-15", "result": "clean", "signal": 0.29}},
    {"id": "p13", "opened": "2026-09-05", "test": {"date": "2026-10-21", "result": "clean", "signal": 0.12}},
    {"id": "p15", "opened": "2025-07-01", "test": None},
    {"id": "p03", "opened": "2026-07-28", "test": {"date": "2026-10-22", "result": "unreadable", "signal": None,
                                                    "reason": "Photo too dark"}},
]

# Result levels (PLACEHOLDER thresholds: real cutoffs need lab calibration against plate counts)
RESULTS = {
    "clean":        {"label": "Likely clean", "color": "green", "max": 0.35,
                     "advice": "No sign of contamination. Keep tracking the toss-by date."},
    "unclear":      {"label": "Unclear", "color": "amber", "max": 0.60,
                     "advice": "Borderline result. Retest in a few days, or replace it if it's near its toss-by date."},
    "contaminated": {"label": "Possible contamination", "color": "red", "max": 1.01,
                     "advice": "Stop using this product, especially near the eyes or broken skin."},
    "unreadable":   {"label": "Unreadable, retake photo", "color": "gray", "max": None, "advice": "Retake the photo."},
}

# ===========================================================================
# 2. FORMULA RULES (also used to analyze the Open Beauty Facts dataset)
# ===========================================================================
PRESERVATIVES = [
    "phenoxyethanol", "paraben", "sodium benzoate", "potassium sorbate", "benzoic acid", "sorbic acid",
    "benzyl alcohol", "dehydroacetic acid", "chlorphenesin", "methylisothiazolinone",
    "methylchloroisothiazolinone", "dmdm hydantoin", "imidazolidinyl urea", "diazolidinyl urea",
    "sodium hydroxymethylglycinate", "triclosan", "formaldehyde", "salicylic acid",
    "sodium levulinate", "levulinic acid", "sodium anisate", "anisic acid", "caprylyl glycol",
    "ethylhexylglycerin", "piroctone olamine", "zinc pyrithione", "benzalkonium chloride",
    "glyceryl caprylate", "pentylene glycol", "alcohol denat",
]


def preservatives_found(ingredients):
    text = str(ingredients or "").lower()
    return [p for p in PRESERVATIVES if p in text]


def is_water_based(ingredients):
    """Water listed first or second = water-based (microbes need water to grow)."""
    parts = [p.strip() for p in re.split(r"[,;]", str(ingredients or "").lower()) if p.strip()]
    return any(re.search(r"aqua|water|\beau\b", p) for p in parts[:2])


def formula_risk(ingredients, base_override=None):
    """How risky a formula is and how often to test it.

    base_override (optional "water"/"oil"/"powder") lets the user's chosen formula base decide whether
    the product is treated as water-based, instead of only guessing from the ingredient text.
    """
    has_text = bool(str(ingredients or "").strip())
    if not has_text and base_override is None:
        return {"level": "unknown", "water": False, "found": [], "days": None, "advice": "Paste an ingredient list to check it."}
    found = preservatives_found(ingredients)
    water = (base_override == "water") if base_override else is_water_based(ingredients)
    if water and not found:
        return {"level": "higher", "water": True, "found": [], "days": 14,
                "advice": "Water-based with no recognized preservative. Test every 2 weeks once opened, and keep it out of the bathroom."}
    if water:
        return {"level": "typical", "water": True, "found": found, "days": 30,
                "advice": "Water-based but preserved. Test monthly, and sooner if it smells or looks different."}
    return {"level": "lower", "water": False, "found": found, "days": 90,
            "advice": "Little or no water, so microbes struggle to grow. Test if it's past its toss-by date."}


def guess_base(ingredients):
    """Infer a product's base (water / oil / powder) from its ingredient list.

    Used when the user adds their own product, since other pages rely on PRODUCTS[id]["base"].
    Water-first formulas are "water"; talc/mica/starch-led formulas are "powder"; otherwise "oil".
    """
    text = str(ingredients or "").lower()
    if is_water_based(ingredients):
        return "water"
    if re.search(r"\btalc\b|\bmica\b|silica|starch|kaolin|\bstearate\b", text):
        return "powder"
    if re.search(r"\boil\b|\bhuile\b|butter|cera\b|wax|cire\b|glyceride|caprylic/capric", text):
        return "oil"
    return "water"   # safest default: assume microbes can grow unless we see a clear oil/powder base


def toss_by(opened, months):
    d = datetime.strptime(opened, "%Y-%m-%d").date()
    m = d.month - 1 + months
    return date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


# ===========================================================================
# 3. STATISTICS (no SciPy needed)
# ===========================================================================
def wilson_ci(k, n, z=1.96):
    """95% confidence interval for a rate k/n."""
    if n == 0:
        return 0.0, 0.0
    p = min(k / n, 1.0)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def chi_square_2x2(a, b, c, d):
    """Chi-square test (with Yates correction) on [[a, b], [c, d]]. Returns p-value."""
    n = a + b + c + d
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom == 0:
        return 1.0
    chi2 = n * max(0, abs(a * d - b * c) - n / 2) ** 2 / denom
    return math.erfc(math.sqrt(chi2 / 2))


# ===========================================================================
# 4. OPEN BEAUTY FACTS DATASET (real)
# ===========================================================================
SELF_PRESERVING = {"soap", "toothpaste"}   # high pH / sugar alcohols: resist microbes without preservatives
TYPES = [  # (type, keywords in English/French, eye area?) - first match wins
    ("mascara", ["mascara"], True),
    ("eyeliner / eye pencil", ["eye-liner", "eyeliner", "crayon yeux", "khol", "khôl", "kohl"], True),
    ("eye cream", ["contour des yeux", "contour yeux", "eye cream"], True),
    ("foundation", ["fond de teint", "foundation", "bb cream", "cc cream"], False),
    ("lip product", ["rouge à lèvres", "lipstick", "baume à lèvres", "baume lèvres", "lip balm", "gloss"], False),
    ("conditioner", ["après-shampoing", "apres-shampoing", "après shampoing", "conditioner", "après-shampooing"], False),
    ("shampoo", ["shampoing", "shampooing", "shampoo"], False),
    ("shower gel", ["gel douche", "shower gel", "douche", "body wash"], False),
    ("deodorant", ["déodorant", "deodorant", "deo ", "anti-transpirant"], False),
    ("toothpaste", ["dentifrice", "toothpaste"], False),
    ("sunscreen", ["solaire", "sunscreen", "spf", "écran"], False),
    ("cleanser / micellar water", ["micellaire", "micellar", "démaquillant", "demaquillant", "nettoyant", "cleanser"], False),
    ("soap", ["savon", "soap"], False),
    ("body lotion", ["lait corps", "lait pour le corps", "body lotion", "lait hydratant", "body milk"], False),
    ("face cream", ["crème visage", "creme visage", "face cream", "crème de jour", "crème de nuit", "soin visage",
                    "day cream", "night cream", "crème hydratante", "moisturi"], False),
    ("hand cream", ["crème mains", "creme mains", "hand cream"], False),
    ("cream (other)", ["crème", "creme", "cream"], False),
]


def product_type(text):
    t = str(text).lower()
    for name, words, _ in TYPES:
        if any(w in t for w in words):
            return name
    return None


def find_dataset():
    """Look next to this file for the .tsv, or a .zip that contains it."""
    for path in glob.glob(os.path.join(HERE, "**", "*.tsv"), recursive=True):
        if "beauty" in os.path.basename(path).lower():
            return path
    for path in glob.glob(os.path.join(HERE, "**", "*.zip"), recursive=True):
        try:
            with zipfile.ZipFile(path) as z:
                if any(n.endswith(".tsv") for n in z.namelist()):
                    return path
        except zipfile.BadZipFile:
            continue
    return None


@st.cache_data(show_spinner="Loading Open Beauty Facts products...")
def load_obf(path):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            name = [n for n in z.namelist() if n.endswith(".tsv")][0]
            raw = io.BytesIO(z.read(name))
    else:
        raw = path
    df = pd.read_csv(raw, sep="\t", low_memory=False, on_bad_lines="skip", dtype=str)
    df = df[df.ingredients_text.notna() & (df.ingredients_text.str.len() > 10)].copy()
    text = (df.product_name.fillna("") + " " + df.generic_name.fillna("") + " " +
            df.categories_en.fillna("") + " " + df.categories.fillna(""))
    df["type"] = text.map(product_type)
    df["water_based"] = df.ingredients_text.map(is_water_based)
    df["has_preservative"] = df.ingredients_text.map(lambda s: bool(preservatives_found(s)))
    df["unpreserved_water"] = df.water_based & ~df.has_preservative
    labels = df.labels_en.fillna("").str.lower()
    df["natural_label"] = labels.str.contains("organic|bio|ecocert|cosmebio|natural|natrue")
    df["paraben_free_label"] = labels.str.contains("without paraben|paraben free|sans paraben")
    df["risk_level"] = df.ingredients_text.map(lambda s: formula_risk(s)["level"])
    return df


def obf_findings(df):
    pool = df[df.water_based & ~df.type.isin(SELF_PRESERVING)]
    a = int((pool.natural_label & ~pool.has_preservative).sum())
    b = int((pool.natural_label & pool.has_preservative).sum())
    c = int((~pool.natural_label & ~pool.has_preservative).sum())
    d = int((~pool.natural_label & pool.has_preservative).sum())
    labels = pd.DataFrame([
        {"group": "Organic / natural label", "pct": a / (a + b), "n": a + b},
        {"group": "No such label", "pct": c / (c + d), "n": c + d},
        {"group": "'Without paraben' label", "pct": 1 - pool[pool.paraben_free_label].has_preservative.mean(),
         "n": int(pool.paraben_free_label.sum())},
        {"group": "No paraben-free label", "pct": 1 - pool[~pool.paraben_free_label].has_preservative.mean(),
         "n": int((~pool.paraben_free_label).sum())},
    ])
    g = df[df.type.notna() & ~df.type.isin(SELF_PRESERVING)].groupby("type")
    by_type = pd.DataFrame({"products": g.size(), "pct_unpreserved_water": g.unpreserved_water.mean()}).reset_index()
    by_type = by_type[by_type.products >= 15].sort_values("pct_unpreserved_water")
    return {"rate_natural": a / (a + b), "rate_other": c / (c + d), "p": chi_square_2x2(a, b, c, d),
            "labels": labels, "by_type": by_type, "pool_n": len(pool)}


# ===========================================================================
# 5. PHOTO READER (numpy only)
# ===========================================================================
CLEAN_RGB = np.array([245, 232, 150], np.float32)    # pale yellow
CONTAM_RGB = np.array([150, 25, 95], np.float32)     # deep magenta
WHITE_REF = (0.14, 0.24, 0.24, 0.36)                 # where the white square is (fractions x1, y1, x2, y2)
TEST_PATCH = (0.55, 0.34, 0.78, 0.66)                # where the test patch is


def crop(img, box):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    return img[int(y1 * h):int(y2 * h), int(x1 * w):int(x2 * w)]


def sharpness(img):
    """Variance of the Laplacian: sharp photos have strong edges, blurry ones don't."""
    g = img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114
    lap = g[1:-1, :-2] + g[1:-1, 2:] + g[:-2, 1:-1] + g[2:, 1:-1] - 4 * g[1:-1, 1:-1]
    return float(lap.var())


def read_strip(img_rgb):
    """img_rgb: numpy array (H, W, 3). Returns status, signal 0-1, reason, colors."""
    img = img_rgb.astype(np.float32)
    white = crop(img, WHITE_REF).reshape(-1, 3).mean(axis=0)
    if white.mean() < 120:
        return {"status": "unreadable", "signal": None, "reason": "Photo too dark. Move to better light and retake."}
    if sharpness(img) < 40:
        return {"status": "unreadable", "signal": None, "reason": "Photo too blurry. Hold the phone still and retake."}
    raw = np.median(crop(img, TEST_PATCH).reshape(-1, 3), axis=0)
    patch = np.clip(raw * (255.0 / np.maximum(white, 1.0)), 0, 255)       # white balance
    direction = CONTAM_RGB - CLEAN_RGB
    t = float(np.dot(patch - CLEAN_RGB, direction) / np.dot(direction, direction))
    return {"status": "ok", "signal": round(min(max(t, 0.0), 1.0), 3), "reason": None,
            "raw_rgb": [int(v) for v in raw], "patch_rgb": [int(v) for v in patch]}


def classify(signal):
    for key in ["clean", "unclear", "contaminated"]:
        if signal < RESULTS[key]["max"]:
            return key
    return "contaminated"


def make_card(t, light=(1.0, 1.0, 1.0), brightness=1.0, blur=False, seed=0):
    """Draw a simulated test card photo. t: 0 = clean color, 1 = contaminated color."""
    rng = np.random.default_rng(seed)
    img = np.full((500, 800, 3), 225, np.float32)
    img[60:440, 60:740] = 250                       # card
    img[110:190, 100:200] = 255                     # white reference
    img[210:290, 100:200] = 128                     # gray reference
    img[310:390, 100:200] = 20                      # black reference
    img[150:350, 420:640] = CLEAN_RGB + (CONTAM_RGB - CLEAN_RGB) * t   # test patch
    img[148:152, 418:642] = img[348:352, 418:642] = 90                 # patch border
    img[148:352, 418:422] = img[148:352, 638:642] = 90
    img = img * np.array(light, np.float32) * brightness + rng.normal(0, 6, img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    if blur:
        small = Image.fromarray(img).resize((60, 38), Image.BILINEAR)
        img = np.array(small.resize((800, 500), Image.BILINEAR))
    return img


SAMPLES = {
    "Clean": dict(t=0.05),
    "Clean, warm light": dict(t=0.10, light=(1.0, 0.92, 0.78)),
    "Unclear": dict(t=0.45),
    "Contaminated": dict(t=0.90),
    "Contaminated, cool light": dict(t=0.85, light=(0.85, 0.93, 1.0)),
    "Too dark": dict(t=0.80, brightness=0.25),
    "Blurry": dict(t=0.20, blur=True),
}

# ===========================================================================
# 6. SIMULATED LAB EXPERIMENTS (researcher dashboard)
# ===========================================================================
@st.cache_data
def make_experiments(n=300, seed=42):
    rng = random.Random(seed)
    ids = list(PRODUCTS)
    rows = []
    for i in range(1, n + 1):
        p = PRODUCTS[rng.choice(ids)]
        storage = rng.choice(["bathroom", "bedroom", "bag", "fridge"])
        days = rng.randint(7, 540)
        prob = 0.15 + 0.15 * (p["packaging"] == "jar") + 0.10 * (p["base"] == "water") - 0.10 * (p["base"] == "powder")
        prob += 0.10 * (storage == "bathroom") - 0.08 * (storage == "fridge") + min(days / 365, 1) * 0.20
        contaminated = rng.random() < max(0.02, min(prob, 0.9))
        if contaminated:   # hidden pattern: oil-based samples give a weaker signal
            signal = rng.gauss(0.64 if p["base"] == "oil" else 0.80, 0.12)
        else:
            signal = rng.gauss(0.28, 0.14)
        signal = round(min(max(signal, 0), 1), 3)
        rows.append({"product_type": p["category"], "base": p["base"], "packaging": p["packaging"],
                     "storage": storage, "signal": signal, "contaminated": contaminated,
                     "test_positive": signal >= 0.60})
    return pd.DataFrame(rows)


# ===========================================================================
# 6a. SIMULATED COMMUNITY SUBMISSIONS (kept separate from research data)
# ===========================================================================
# IMPORTANT: this is opt-in, aggregated, SIMULATED data standing in for what users
# might voluntarily submit. It is deliberately kept separate from the Open Beauty
# Facts research data and the FDA data. We report "positive results among submitted
# tests" with sample counts, and never rank brands or imply population-wide rates.
@st.cache_data
def make_community(seed=7):
    rng = random.Random(seed)
    rows = []
    for pid, p in PRODUCTS.items():
        # Plausible submission volume and positive share, driven by the same
        # risk factors used elsewhere, with noise. No real people involved.
        submissions = rng.randint(8, 140)
        base_rate = 0.12 + 0.10 * (p["base"] == "water") + 0.08 * (p["packaging"] == "jar") \
            - 0.08 * (p["base"] == "powder") + (0.06 if p.get("eye") else 0)
        base_rate = max(0.03, min(base_rate + rng.uniform(-0.05, 0.05), 0.6))
        positives = sum(1 for _ in range(submissions) if rng.random() < base_rate)
        rows.append({"category": p["category"], "base": p["base"], "eye": p.get("eye", False),
                     "submissions": submissions, "positives": positives})
    df = pd.DataFrame(rows)
    # Aggregate to category level only (never individual products / brands).
    g = df.groupby(["category", "eye"], as_index=False).agg(
        submissions=("submissions", "sum"), positives=("positives", "sum"))
    g["positive_share"] = g.positives / g.submissions
    return g.sort_values("positive_share", ascending=False)


# ===========================================================================
# 6b. GUIDED SAMPLING (packaging-specific instructions)
# ===========================================================================
# How to take a clean sample from each packaging type. Keep instructions generic
# and safe; they do not promise accuracy and apply to the simulated test card.
PACKAGING_STEPS = {
    "tube_wand": {
        "label": "Tube with wand (mascara, liquid liner, gloss)",
        "steps": [
            "Wash and dry your hands before you start.",
            "Pull the wand out once. Do not pump it: pumping pushes air and microbes in.",
            "Wipe the very tip of the wand along the test strip's swab pad for about 2 seconds.",
            "Close the product right away so it does not dry out.",
        ],
    },
    "jar": {
        "label": "Open jar (creams, balms, masks)",
        "steps": [
            "Wash and dry your hands, or use a clean spatula.",
            "Take a small amount from just below the surface, not the very top layer.",
            "Spread a thin film across the test strip's swab pad.",
            "Close the lid firmly and store away from heat and steam.",
        ],
    },
    "pump": {
        "label": "Pump bottle (foundation, lotion, moisturizer)",
        "steps": [
            "Wash and dry your hands.",
            "Wipe the pump nozzle, then dispense one small pump onto the swab pad.",
            "Discard the first pump onto a tissue if the product has not been used in a while.",
            "Wipe the nozzle clean afterward.",
        ],
    },
    "dropper": {
        "label": "Dropper (serums, face oils)",
        "steps": [
            "Wash and dry your hands.",
            "Release one or two drops directly onto the swab pad without touching it with the dropper.",
            "Avoid letting the dropper tip touch the strip, your skin, or the counter.",
            "Return the dropper to the bottle and close it.",
        ],
    },
    "bottle": {
        "label": "Open-mouth bottle (micellar water, toners)",
        "steps": [
            "Wash and dry your hands.",
            "Tip a small amount onto the swab pad, or onto a clean cotton pad and press it to the pad.",
            "Do not dip the strip into the bottle.",
            "Cap the bottle right away.",
        ],
    },
    "tube": {
        "label": "Squeeze tube (sunscreen, some creams)",
        "steps": [
            "Wash and dry your hands.",
            "Wipe the opening, then squeeze a small amount onto the swab pad.",
            "Avoid touching the strip with the tube opening.",
            "Wipe the opening and re-cap.",
        ],
    },
    "compact": {
        "label": "Powder compact (powder blush, eyeshadow)",
        "steps": [
            "Powders are lower risk because microbes struggle to grow without water.",
            "Press the swab pad lightly onto the powder surface, or use a clean dry brush.",
            "If the strip needs moisture to develop, follow the kit's wetting step.",
            "Close the compact to keep it dry.",
        ],
    },
}
DEFAULT_STEPS = {
    "label": "General",
    "steps": [
        "Wash and dry your hands before sampling.",
        "Take a small, fresh sample without touching the applicator to skin or surfaces.",
        "Transfer it to the test strip's swab pad.",
        "Close the product right away.",
    ],
}


def sampling_guide(product_id):
    """Return packaging-specific sampling instructions for a product."""
    pkg = PRODUCTS[product_id]["packaging"]
    return PACKAGING_STEPS.get(pkg, DEFAULT_STEPS)


# ===========================================================================
# 6c. AI EXPLAINER (rule-based, offline, source-cited)
# ===========================================================================
# This "AI" explains results and summarizes patterns Teria has ALREADY calculated.
# Boundaries, enforced by only ever reading from calculated values and fixed text:
#   - It does NOT measure contamination (the photo reader does that).
#   - It does NOT diagnose conditions or give medical advice.
#   - It does NOT invent expiration dates (those come from the PAO symbol).
#   - It never calls a product "safe"; it reports the calculated result and limits.
#   - Every claim is tied to a named source (your test, the label, FDA, Open Beauty Facts).
AI_DISCLAIMER = (
    "I explain results and data Teria already calculated. I do not measure contamination, "
    "diagnose health conditions, or decide expiration dates, and I never call a product safe."
)


def explain_result(product_id, test):
    """Plain-language explanation of a saved or fresh scan result. Sources: the user's test + the label."""
    p = PRODUCTS[product_id]
    lines = []
    if not test or test.get("result") is None:
        return ["This product has not been tested yet, so I have no result to explain. "
                "Run a scan on the Scan page first."]
    res = RESULTS.get(test["result"], {})
    label = res.get("label", test["result"])
    if test["result"] == "unreadable":
        lines.append(f"**Your test (source: your scan):** the photo could not be read. "
                     f"{test.get('reason') or 'Please retake it in better light.'} "
                     "No measurement was made, so there is nothing to interpret yet.")
        return lines
    sig = test.get("signal")
    lines.append(
        f"**Your test (source: your scan):** the strip color gave a signal of "
        f"{sig:.2f} on a 0-1 scale, where 0 is the clean color and 1 is the contaminated color. "
        f"Teria read that as \"{label}\"."
    )
    if test["result"] == "clean":
        lines.append("A low signal means no sign of contamination was detected. "
                     "This is not a guarantee the product is safe: the strip can miss some contamination, "
                     "and oil-based products in particular give a weaker signal.")
    elif test["result"] == "unclear":
        lines.append("A middling signal sits between the clean and contaminated colors. "
                     "The result is inconclusive, not a verdict. Retesting in a few days usually helps.")
    elif test["result"] == "contaminated":
        lines.append("A high signal leans toward the contaminated color. "
                     "This is a reason to stop using the product, especially near the eyes or broken skin. "
                     "It is a screening signal, not a lab-confirmed diagnosis.")
    lines.append(f"_{res.get('advice', '')}_")
    # Expiration note kept separate from contamination, per our safeguards.
    return lines


def explain_toss_by(product_id, opened):
    """Explain the toss-by date. Source: the product's period-after-opening (PAO) symbol."""
    p = PRODUCTS[product_id]
    tb = toss_by(opened, p["pao"])
    status = "already past" if tb < TODAY else "still ahead"
    return [
        f"**Toss-by date (source: the open-jar PAO symbol on the label):** this product's symbol says "
        f"{p['pao']} months after opening. You opened it on {opened}, so the toss-by date is {tb} "
        f"({status}).",
        "This is a manufacturer guideline about how long the formula is designed to last once opened. "
        "It is separate from the contamination test: an in-date product can still test positive, and vice versa. "
        "I do not invent or adjust this date.",
    ]


def explain_formula(ingredients):
    """Explain a formula-risk result. Source: keyword checks on the ingredient list."""
    r = formula_risk(ingredients)
    if r["level"] == "unknown":
        return ["Paste an ingredient list and I will explain its risk level. "
                "I only read the words in the list; I do not test the actual product."]
    found = ", ".join(r["found"]) if r["found"] else "none that Teria recognizes"
    lines = [
        f"**Formula check (source: keyword scan of the ingredient list):** this formula looks "
        f"**{r['level']} risk**.",
        f"Water listed near the top: {'yes' if r['water'] else 'no'}. "
        f"Recognized preservatives: {found}.",
        "Microbes need water to grow, so water-based formulas with no recognized preservative are the "
        "riskiest once opened; oil- or powder-based formulas resist growth.",
        f"Suggested testing cadence: about every {r['days']} days once opened." if r["days"] else "",
        "This is based only on the words in the list, which may be incomplete, and is not a measurement "
        "of the actual product.",
    ]
    return [ln for ln in lines if ln]


def explain_fda():
    """Summarize the FDA finding Teria calculated. Source: openFDA cosmetic adverse event reports."""
    f = FDA.copy()
    eye = f[f.eye_area][["infection_mentions", "total_reports"]].sum()
    other = f[~f.eye_area][["infection_mentions", "total_reports"]].sum()
    eye_rate = eye.infection_mentions / eye.total_reports * 100
    other_rate = other.infection_mentions / other.total_reports * 100
    ratio = eye_rate / other_rate
    return [
        f"**FDA finding (source: openFDA cosmetic adverse event reports, pulled 2026-10-24):** across "
        f"{int(f.total_reports.sum()):,} reports, eye-area products had about {eye_rate:.1f} "
        f"infection-related reactions per 100 reports, versus {other_rate:.1f} for other products "
        f"(about {ratio:.1f}x).",
        "These are voluntary, unvalidated reports. They do not prove any product caused a reaction or was "
        "contaminated; they tell us where to focus testing first.",
    ]


# ===========================================================================
# 5b. LABEL READER: photo of a product label -> structured details, checked against Open Beauty Facts
# ===========================================================================
import difflib
import tempfile
from collections import Counter

INGREDIENT_HEADERS = r"([il1|]ngr[eéè3]d[il1]ents?|inci|composition|zutaten|ingredientes)\s*[:：.\-]?"
STOP_WORDS = r"(made in|fabriqu[ée]|produit en|manufactured|distributed|lot\b|batch|exp\b|exp\.|expiry|best before|" \
             r"[àa] utiliser|ddm|warning|caution|pr[ée]cautions?|directions|mode d'emploi|usage|net\b|contenance|" \
             r"period after opening|periode? apr[èe]s ouverture|p[ée]riode d'ouverture|use within|" \
             r"\b\d+(?:[.,]\d+)?\s?(?:ml|g|fl\.?\s?oz)\b|\b\d{8,13}\b|\bpao\b|\b\d{1,2}\s?m\b)"
VALID_PAO = {1, 3, 6, 9, 12, 18, 24, 30, 36}


def ocr_engines():
    """Which text-recognition engines are installed, best first."""
    engines = []
    if sys.platform == "darwin":
        try:
            import ocrmac  # noqa: F401  (Apple Vision, built into macOS)
            engines.append("apple")
        except ImportError:
            pass
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        engines.append("tesseract")
    except Exception:
        pass
    return engines


def ocr_image(pil_image):
    """Return the text on the image, top to bottom, or None if no engine is available."""
    img = pil_image.convert("RGB")
    if img.width < 1000:                           # small photos read better scaled up
        img = img.resize((1000, int(img.height * 1000 / img.width)))
    for engine in ocr_engines():
        try:
            if engine == "apple":
                from ocrmac import ocrmac
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    img.save(tmp.name)
                lines = ocrmac.OCR(tmp.name, language_preference=["en-US", "fr-FR"]).recognize()
                os.unlink(tmp.name)
                lines = sorted(lines, key=lambda r: (-round(r[2][1], 2), r[2][0]))   # top to bottom, left to right
                return "\n".join(r[0] for r in lines)
            if engine == "tesseract":
                import pytesseract
                return pytesseract.image_to_string(img, config="--psm 6")
        except Exception:
            continue
    return None


@st.cache_data(show_spinner="Building ingredient dictionary from Open Beauty Facts...")
def ingredient_vocab(path):
    """Every ingredient name that appears at least twice in the dataset, in its most common spelling."""
    counts, spelling = Counter(), {}
    for text in load_obf(path).ingredients_text:
        for part in re.split(r"[,;•·]", str(text)):
            name = re.sub(r"\s+", " ", re.sub(r"[\[\(].*?[\]\)]|\*|\.$", "", part)).strip()
            key = name.lower()
            if 3 <= len(key) <= 50 and not key[0].isdigit():
                counts[key] += 1
                spelling.setdefault(key, Counter())[name] += 1
    return {k: spelling[k].most_common(1)[0][0] for k, n in counts.items() if n >= 2}


def clean_ocr(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"(?<=[a-zA-Z])0(?=[a-zA-Z])", "o", text)          # zero inside a word -> o
    text = re.sub(r"(?<=[a-zA-Z])1(?=[a-zA-Z])", "l", text)          # one inside a word -> l
    text = re.sub(r"-\n(?=[a-zà-ü])", "", text)                  # re-join words split across lines
    text = re.sub(r"(?<=[A-Za-z])[.](?=\s*[A-Z][a-z])", ",", text)  # OCR often reads commas as periods
    return text


def split_ingredients(block):
    block = re.sub(r"\s*\n\s*", " ", block)
    parts = re.split(r"\s*[,;•·]\s*", block)
    return [re.sub(r"\s+", " ", p).strip(" .:") for p in parts if len(p.strip(" .:")) >= 2]


def correct_ingredients(parts, vocab):
    """Snap each OCR'd ingredient to the closest real ingredient name in the dataset."""
    keys = list(vocab)
    fixed, recognized = [], 0
    for p in parts:
        k = p.lower()
        if k in vocab:
            fixed.append(p)                  # read correctly: keep the label's own spelling
            recognized += 1
            continue
        match = difflib.get_close_matches(k, keys, n=1, cutoff=0.84)
        if match:
            fixed.append(vocab[match[0]])
            recognized += 1
        else:
            fixed.append(p)
    return fixed, recognized


def parse_label(text, vocab=None):
    """Pull structured details out of label text. Anything not found stays None (unknown)."""
    text = clean_ocr(text or "")
    flat = re.sub(r"\s+", " ", text)
    out = {"ingredients": None, "ingredients_recognized": 0, "ingredients_total": 0, "pao_months": None,
           "expiry": None, "batch": None, "barcode": None, "size": None, "type": product_type(flat) if flat else None}

    m = re.search(INGREDIENT_HEADERS, text, flags=re.I)
    if m:
        rest = text[m.end():]
        stop = re.search(STOP_WORDS, rest, flags=re.I)
        block = rest[:stop.start()] if stop else rest
        parts = split_ingredients(block)
        if parts:
            if vocab:
                parts, out["ingredients_recognized"] = correct_ingredients(parts, vocab)
            out["ingredients"], out["ingredients_total"] = ", ".join(parts), len(parts)

    for n in re.findall(r"\b(\d{1,2})\s?[mM](?![lL\w])", flat):            # the open-jar symbol: "12M", "6 M"
        if int(n) in VALID_PAO:
            out["pao_months"] = int(n)
            break
    m = re.search(r"(?:exp(?:iry|\.)?|best before|use by|[àa] utiliser avant|ddm)\s*[:.]?\s*"
                  r"(\d{1,2})\s*[/.\-]\s*(\d{2,4})", flat, flags=re.I)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        year = year + 2000 if year < 100 else year
        if 1 <= month <= 12:
            out["expiry"] = f"{year}-{month:02d}"
    m = re.search(r"\b(?:lot|batch|l/n)\s*(?:no\.?|n°|#)?\s*[:.]?\s*([A-Z0-9][A-Z0-9\-]{2,})", flat, flags=re.I)
    if m:
        out["batch"] = m.group(1).upper()
    # Barcodes: try the spaced text first (word boundaries keep EAN/UPC lengths intact,
    # so a 13-digit code next to a size like "50 ml" is not mis-joined), then fall back
    # to the de-spaced text for codes OCR split into groups (e.g. "360052 335 1251").
    bm = re.search(r"(?<!\d)(\d{13}|\d{12}|\d{8})(?!\d)", flat)
    if not bm:
        bm = re.search(r"(?<!\d)(\d{13}|\d{12}|\d{8})(?!\d)", flat.replace(" ", ""))
    if bm:
        out["barcode"] = bm.group(1)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s?(ml|mL|g|fl\.?\s?oz)\b", flat)
    if m:
        out["size"] = f"{m.group(1)} {m.group(2)}"
    return out


def match_products(text, df, barcode=None, top=3):
    """Find which dataset products this label most likely is (barcode first, then name/brand words)."""
    if df is None or not text:
        return []
    if barcode:
        hit = df[df.code.fillna("") == barcode]
        if len(hit):
            return [(hit.iloc[0], 1.0)]
    words = set(re.findall(r"[a-zà-ü0-9]{3,}", text.lower()))
    scores = []
    for idx, (name, brand) in enumerate(zip(df.product_name.fillna(""), df.brands.fillna(""))):
        name_words = set(re.findall(r"[a-zà-ü0-9]{3,}", name.lower()))
        if not name_words:
            continue
        brand_words = set(re.findall(r"[a-zà-ü0-9]{3,}", brand.lower().split(",")[0]))
        score = len(name_words & words) / len(name_words)
        if brand_words and brand_words <= words:
            score = score * 0.7 + 0.3
        else:
            score *= 0.7
        if score >= 0.5:
            scores.append((idx, score))
    scores.sort(key=lambda s: -s[1])
    return [(df.iloc[i], round(s, 2)) for i, s in scores[:top]]



# ===========================================================================
# 6d. TEST A PRODUCT: simulated strip + transparent 0-100 score
# ===========================================================================
# The strip is SIMULATED: its color is generated from the product's risk factors, then read back
# by the real photo reader (section 5). A real strip would change color because of microbes in the sample.
PACKAGING_POINTS = {"jar": 12, "tube_wand": 10, "bottle": 6, "dropper": 6, "pump": 3, "tube": 3, "compact": 2}
STORAGE_POINTS = {"bathroom (steamy)": 10, "bag / purse": 8, "bedroom / dresser": 3, "fridge": 0}
FORMULA_POINTS = {"higher": 30, "typical": 12, "lower": 3, "unknown": 15}
LIGHTS = {"Normal light": (1.0, 1.0, 1.0), "Warm lamp": (1.0, 0.92, 0.78), "Cool daylight": (0.85, 0.93, 1.0),
          "Dim room": (0.62, 0.62, 0.62)}


def months_between(start, end):
    return max(0.0, (end - start).days / 30.44)


def risk_factors(ingredients, packaging, opened, pao, storage, eye, base=None):
    """Each factor gives points; the total (max 100) is how much the product's situation favors microbial growth."""
    fr = formula_risk(ingredients, base_override=base)
    months = months_between(opened, TODAY)
    if pao:
        age_pts = 25 if months > pao else round(20 * months / pao)
        age_note = f"{months:.1f} of {pao} months used" + (" (past toss-by)" if months > pao else "")
    else:
        age_pts = 15 if months > 12 else 8
        age_note = f"{months:.1f} months open, no open-jar symbol"
    rows = [
        ("Formula", FORMULA_POINTS[fr["level"]], 30,
         {"higher": "water-based, no recognized preservative", "typical": "water-based, preserved",
          "lower": "little or no water", "unknown": "no ingredient list"}[fr["level"]]),
        ("Time since opening", age_pts, 25, age_note),
        ("Packaging", PACKAGING_POINTS.get(packaging, 6), 12, PACKAGING_STEPS.get(packaging, DEFAULT_STEPS)["label"]),
        ("Storage", STORAGE_POINTS[storage], 10, storage),
        ("Used near the eye", 8 if eye else 0, 8, "eyes are the most sensitive area (FDA data)" if eye else "no"),
    ]
    df = pd.DataFrame(rows, columns=["factor", "points", "max", "why"])
    total = int(round(df.points.sum() / df["max"].sum() * 100))
    return df, total, fr


def simulate_strip(factor_score, light="Normal light", seed=0):
    """Make the strip image a real reaction might produce for this risk level (simulated, with natural variation)."""
    rng = random.Random(seed)
    t = min(max(0.08 + 0.80 * factor_score / 100 + rng.gauss(0, 0.07), 0.0), 1.0)
    return make_card(t, light=LIGHTS[light], brightness=1.0, seed=seed)


def label_card(img, name):
    """Print the product name on the card, outside the areas the reader measures."""
    from PIL import ImageDraw, ImageFont
    pil = Image.fromarray(img)
    draw = ImageDraw.Draw(pil)
    try:
        font = ImageFont.load_default(size=26)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((420, 92), "TERIA TEST", fill=(60, 60, 60), font=font)
    draw.text((100, 400), str(name)[:40], fill=(70, 70, 70), font=font)
    return np.array(pil)


def teria_score(signal, factor_score):
    """0-100, higher = more concern. Strip reading counts 60%, risk factors 40%. Unreadable strip = factors only."""
    if signal is None:
        return factor_score
    return int(round(0.6 * signal * 100 + 0.4 * factor_score))


def score_band(score):
    if score >= 60:
        return "High concern", "red", "Stop using it, especially near the eyes, and replace it."
    if score >= 35:
        return "Moderate concern", "amber", "Retest in a few days and watch for changes in smell, color or texture."
    return "Low concern", "green", "No strong warning signs. Keep tracking the toss-by date and retest on schedule."


# ===========================================================================
# 7. THE APP
# ===========================================================================
st.set_page_config(page_title="Teria", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# Look and feel: matches the Lovable design (calm, clinical, lots of white space)
# ---------------------------------------------------------------------------
INK, MUTED, LINE, TILE, BAND = "#1F2421", "#6B726E", "#E4E6E3", "#EEF0EE", "#EEF1EE"
COLORS = {"green": "#2F6B4F", "amber": "#9A6B00", "red": "#A8344B", "gray": "#6B726E"}
EYE, OTHER, ACCENT = "#3F5A4C", "#C9CFCB", "#3F5A4C"

ICONS = {  # simple line icons, same style as the design
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10"/>',
    "flask": '<path d="M9 3h6M10 3v6.5L4.6 18.4A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.4-2.6L14 9.5V3M7.5 15h9"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 5 9-5"/>',
    "sparkle": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
}


def icon(name, size=22, color=INK):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


THEME_CSS = f"""
@import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=DM+Sans:wght@400;500;600&display=swap");
  .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stMarkdown {{ font-family: "DM Sans", "Helvetica Neue", Arial, sans-serif; }}
  .stApp {{ color: {INK}; }}
  [data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: "Material Symbols Rounded" !important; }}
  .stApp {{ background: #FFFFFF; }}
  #MainMenu, footer, header[data-testid="stHeader"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
  .block-container {{ max-width: 1120px; padding-top: 1.2rem; padding-bottom: 4rem; }}
  h1, h2, h3, .serif {{ font-family: "Fraunces", Georgia, serif !important; font-weight: 600 !important;
                        letter-spacing: -0.01em; color: {INK} !important; }}
  h1 {{ font-size: 2.6rem !important; }}
  p, li, label, .stMarkdown {{ color: {INK}; }}
  [data-testid="stCaptionContainer"], .muted {{ color: {MUTED} !important; }}
  .eyebrow {{ font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; color: {MUTED}; margin-bottom: 0.3rem; }}

  /* bordered containers = the design's cards */
  [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {LINE} !important; border-radius: 14px !important; }}
  [data-testid="stMetricValue"] {{ font-family: "Fraunces", Georgia, serif; font-weight: 500; }}
  [data-testid="stMetricLabel"] p {{ color: {MUTED}; }}

  /* buttons: white with a thin border */
  .stButton > button, .stDownloadButton > button {{ background: #fff; color: {INK}; border: 1px solid {LINE};
      border-radius: 10px; font-weight: 500; padding: 0.5rem 1.1rem; }}
  .stButton > button:hover {{ border-color: {INK}; color: {INK}; background: #fff; }}
  .stButton > button[kind="primary"] {{ background: {INK}; color: #fff; border-color: {INK}; }}

  /* top navigation: buttons look like text links */
  .st-key-nav {{ border-bottom: 1px solid {LINE}; padding-bottom: 0.6rem; margin-bottom: 0.2rem; }}
  .st-key-nav .stButton > button, .st-key-nav [data-testid="stPopover"] button {{ border: none; background: transparent; white-space: nowrap;
      color: {MUTED}; padding: 0.3rem 0.2rem; font-weight: 500; }}
  .st-key-nav .stButton > button:hover {{ color: {INK}; }}
  .st-key-navactive .stButton > button {{ color: {INK} !important; text-decoration: underline; text-underline-offset: 6px; }}
  .brand {{ font-family: "Fraunces", Georgia, serif; font-size: 1.5rem; font-weight: 600; display: flex; align-items: center; gap: 0.45rem; }}

  /* notice band */
  .band {{ background: {BAND}; border-top: 1px solid {LINE}; border-bottom: 1px solid {LINE}; margin: 0 -100vw;
           padding: 0.85rem 100vw; display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
           font-size: 0.92rem; }}
  .band span {{ display: flex; align-items: center; gap: 0.5rem; }}
  .band .right {{ color: {MUTED}; }}

  /* feature cards */
  [class*="st-key-card"] {{ border: 1px solid {LINE}; border-radius: 14px; padding: 1.6rem 1.6rem 1rem; min-height: 330px;
                            justify-content: space-between; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2.2rem; }}
  .tile {{ background: {TILE}; border-radius: 10px; width: 56px; height: 56px; display: grid; place-items: center; }}
  .num {{ color: {MUTED}; font-size: 0.9rem; }}
  .card-title {{ font-size: 1.35rem; font-weight: 500; margin: 0 0 0.6rem; }}
  .card-text {{ color: {MUTED}; font-size: 1.02rem; line-height: 1.6; }}
  [class*="st-key-card"] .stButton > button {{ border: none; padding: 0.4rem 0; width: 100%; justify-content: space-between;
                                               font-size: 1.02rem; font-weight: 500; }}
  [class*="st-key-card"] .stButton > button div {{ width: 100%; display: flex; justify-content: space-between; }}

  .stat {{ font-family: "Fraunces", Georgia, serif; font-size: 2.2rem; line-height: 1.1; }}
  .stat-label {{ color: {MUTED}; font-size: 0.95rem; }}
  hr {{ border-color: {LINE} !important; }}
"""
# Blank lines would end the style block early in Markdown, so strip them before injecting.
st.markdown("<style>" + "\n".join(line for line in THEME_CSS.splitlines() if line.strip()) + "</style>",
            unsafe_allow_html=True)


def badge(label, color):
    return (f"<span style='background:{COLORS[color]};color:white;padding:3px 10px;border-radius:12px;"
            f"font-size:0.85em;font-weight:600'>{label}</span>")


def show_risk(where, ingredients):
    r = formula_risk(ingredients)
    label, color = {"higher": ("Higher risk", "red"), "typical": ("Typical risk", "amber"),
                    "lower": ("Lower risk", "green"), "unknown": ("Unknown", "gray")}[r["level"]]
    where.markdown(badge(label, color), unsafe_allow_html=True)
    where.write(r["advice"])
    if r["level"] != "unknown":
        where.caption(f"Water-based: {'yes' if r['water'] else 'no'} · Preservatives found: "
                      f"{', '.join(r['found']) or 'none recognized'} · Test every {r['days']} days")


def simulated(note="Simulated for demo. Test thresholds are placeholders pending lab calibration."):
    st.caption("⚠️ " + note)


# ---------------------------------------------------------------------------
# Persistence: the shelf and user-added products survive a page refresh / restart.
# We keep ONLY user data (shelf, user products, id counter) in a small JSON file
# next to this script. The dataset, demo catalog and FDA data stay in code.
# ---------------------------------------------------------------------------
PERSIST_PATH = os.path.join(HERE, "teria_shelf.json")


def load_state():
    """Read saved shelf/products from disk. On first run or any error, fall back to the demo shelf."""
    default = {"shelf": [dict(item) for item in SHELF], "user_products": {}, "next_user_pid": 1}
    if not os.path.exists(PERSIST_PATH):
        return default
    try:
        import json
        with open(PERSIST_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Basic shape check so a corrupt file can't break startup.
        if not isinstance(data.get("shelf"), list) or not isinstance(data.get("user_products"), dict):
            return default
        data.setdefault("next_user_pid", 1)
        return data
    except Exception:
        return default


def save_state():
    """Write the current shelf/products to disk. Called after any change."""
    try:
        import json
        with open(PERSIST_PATH, "w", encoding="utf-8") as fh:
            json.dump({"shelf": st.session_state.shelf,
                       "user_products": st.session_state.user_products,
                       "next_user_pid": st.session_state.next_user_pid}, fh, indent=2)
    except Exception as exc:   # never let a disk issue crash the app; just warn once
        st.warning(f"Could not save your shelf to disk: {exc}")


if "shelf" not in st.session_state:
    _saved = load_state()
    st.session_state.shelf = _saved["shelf"]
    # Products the user adds (from a label photo, an Open Beauty Facts search, or manual entry)
    # live here across reruns. Streamlit re-executes this module on every rerun, which resets the
    # module-level PRODUCTS back to the 20 demo items, so we re-register the user's products into
    # PRODUCTS each run. Every page that reads PRODUCTS[id] then sees them with no other changes.
    st.session_state.user_products = _saved["user_products"]
    st.session_state.next_user_pid = _saved["next_user_pid"]
PRODUCTS.update(st.session_state.user_products)


def add_user_product(name, category, base, packaging, pao, eye, opened, ingredients=""):
    """Register a new product and put it on the shelf. Returns the new product id."""
    pid = f"u{st.session_state.next_user_pid:02d}"
    st.session_state.next_user_pid += 1
    product = {"name": name, "category": category or "other", "base": base,
               "packaging": packaging if packaging != "unknown" else "jar",
               "pao": pao or 12, "eye": bool(eye), "ingredients": ingredients, "user_added": True}
    st.session_state.user_products[pid] = product
    PRODUCTS[pid] = product
    st.session_state.shelf.append({"id": pid, "opened": str(opened), "test": None})
    save_state()
    return pid


def remove_from_shelf(shelf_id):
    """Remove a product from the shelf. User-added products are also forgotten entirely."""
    st.session_state.shelf = [i for i in st.session_state.shelf if i["id"] != shelf_id]
    if shelf_id in st.session_state.user_products:
        del st.session_state.user_products[shelf_id]
        PRODUCTS.pop(shelf_id, None)
    save_state()


def update_opened(shelf_id, new_opened):
    """Change a product's opening date (recomputes its toss-by date)."""
    for item in st.session_state.shelf:
        if item["id"] == shelf_id:
            item["opened"] = str(new_opened)
    save_state()

dataset_path = find_dataset()
obf = load_obf(dataset_path) if dataset_path else None

MAIN_PAGES = ["Home", "Scan", "Test a product", "My shelf", "Evidence", "Ask AI"]
MORE_PAGES = ["Community trends", "Lab", "Find a product", "About"]
if "page" not in st.session_state:
    st.session_state.page = "Home"


def go(target):
    st.session_state.page = target


with st.container(key="nav"):
    cols = st.columns([2.2] + [1] * len(MAIN_PAGES) + [0.9], vertical_alignment="center")
    cols[0].markdown(f'<div class="brand">{icon("flask", 24)} Teria</div>', unsafe_allow_html=True)
    for col, name in zip(cols[1:], MAIN_PAGES):
        with col.container(key="navactive" if st.session_state.page == name else f"nav_{name}"):
            st.button(name, key=f"navbtn_{name}", on_click=go, args=(name,))
    with cols[-1].popover("More"):
        for name in MORE_PAGES:
            st.button(name, key=f"navmore_{name}", on_click=go, args=(name,), use_container_width=True)

page = st.session_state.page

st.markdown(f"""<div class="band"><span>{icon("flask", 18)} A thoughtful prototype, not a safety verdict.</span>
<span class="right">All test results are simulated. The physical test requires validation.</span></div>""",
            unsafe_allow_html=True)

# ---------------- Home ----------------
if page == "Home":
    st.markdown("<div style='height:2.2rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Teria Test</div>', unsafe_allow_html=True)
    st.markdown("<h1 style='font-size:3.2rem !important;margin:0 0 0.6rem'>Your beauty shelf, better understood.</h1>",
                unsafe_allow_html=True)
    st.markdown("<p class='muted' style='font-size:1.15rem;max-width:44rem'>Product information, care reminders and "
                "testing insights live in one place. Scan a label, test a product, and get results explained simply.</p>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)

    left, right = st.columns([3, 2], vertical_alignment="bottom")
    left.markdown('<div class="eyebrow">A simple place to start</div><h2 style="font-size:2.4rem !important;margin:0">'
                  'Care begins with knowing.</h2>', unsafe_allow_html=True)
    right.markdown(f"<p class='muted' style='text-align:right;font-size:1.05rem;margin:0'>Scan once. Come back whenever.</p>",
                   unsafe_allow_html=True)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    cards = [
        ("scan", "01", "Scan & guided testing", "Your label details, confirmed by you. A clear path to the proposed "
         "testing experience.", "Start a scan", "Scan"),
        ("flask", "02", "Understand your results", "Plain-language reports, including inconclusive outcomes. "
         "Always clearly simulated.", "Try a demo", "Test a product"),
        ("layers", "03", "Product care & insights", "A personal shelf for product details, reminders, and your saved "
         "demo history.", "Visit your shelf", "My shelf"),
    ]
    for col, (ic, num, title, text, link, target) in zip(st.columns(3, gap="medium"), cards):
        with col.container(key=f"card{num}"):
            st.markdown(f"""<div class="card-top"><div class="tile">{icon(ic, 26)}</div><span class="num">{num}</span></div>
                <div class="card-title">{title}</div><div class="card-text">{text}</div>""", unsafe_allow_html=True)
            st.button(f"{link}  →", key=f"cta{num}", on_click=go, args=(target,))

    st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
    left, right = st.columns([3, 1], vertical_alignment="bottom")
    left.markdown("<h2 style='font-size:2.1rem !important;margin:0'>Your shelf, at a glance</h2>", unsafe_allow_html=True)
    right.button("View shelf  →", key="viewshelf", on_click=go, args=("My shelf",))
    st.divider()
    saved = len(st.session_state.shelf)
    reports = sum(1 for i in st.session_state.shelf if i.get("test"))
    c1, c2, c3, c4 = st.columns([1, 1, 3, 1.4], vertical_alignment="center")
    c1.markdown(f"<div class='stat'>{saved}</div><div class='stat-label'>Saved products</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat'>{reports}</div><div class='stat-label'>Simulated reports</div>", unsafe_allow_html=True)
    attention = sum(1 for i in st.session_state.shelf if i.get("test") and i["test"]["result"] in ("contaminated", "unclear"))
    msg = (f"{attention} product{'s' if attention != 1 else ''} could use a closer look." if attention
           else "Your first product is the start of a little more clarity.")
    c3.markdown(f"<p class='muted' style='display:flex;gap:0.5rem;align-items:center;margin:0'>{icon('sparkle', 20, MUTED)} "
                f"{msg}</p>", unsafe_allow_html=True)
    c4.button("＋  Add a product", key="addproduct", on_click=go, args=("Test a product",))
    st.caption("Saved for this session only · no account needed")
    st.caption(f"Data: openFDA cosmetic adverse events · Open Beauty Facts "
               f"({os.path.basename(dataset_path) if dataset_path else 'dataset not found'})")

# ---------------- Evidence ----------------
elif page == "Evidence":
    st.title("Eye makeup shows 3.4× the infection-related reactions of other cosmetics")
    st.write("We analyzed real FDA cosmetic adverse event reports to decide which products Teria should test first.")

    f = FDA.copy()
    f["rate"] = f.infection_mentions / f.total_reports
    ci = [wilson_ci(k, n) for k, n in zip(f.infection_mentions, f.total_reports)]
    f["err_low"] = [(r - c[0]) * 100 for r, c in zip(f.rate, ci)]
    f["err_high"] = [(c[1] - r) * 100 for r, c in zip(f.rate, ci)]
    f["per_100"] = f.rate * 100
    eye = f[f.eye_area][["infection_mentions", "total_reports"]].sum()
    other = f[~f.eye_area][["infection_mentions", "total_reports"]].sum()
    p_eye = chi_square_2x2(eye.infection_mentions, eye.total_reports - eye.infection_mentions,
                           other.infection_mentions, other.total_reports - other.infection_mentions)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FDA reports analyzed", f"{int(f.total_reports.sum()):,}")
    c2.metric("Eye-area products", f"{eye.infection_mentions / eye.total_reports * 100:.1f} per 100")
    c3.metric("Other products", f"{other.infection_mentions / other.total_reports * 100:.1f} per 100")
    c4.metric("Chi-square p-value", "< 0.001" if p_eye < 0.001 else f"{p_eye:.3f}")

    f = f.sort_values("per_100")
    fig = px.bar(f, x="per_100", y="category", orientation="h", error_x="err_high", error_x_minus="err_low",
                 color=f.eye_area.map({True: "Used near the eye", False: "Other"}),
                 color_discrete_map={"Used near the eye": EYE, "Other": OTHER},
                 hover_data=["total_reports", "infection_mentions"],
                 labels={"per_100": "Infection-related reactions per 100 reports (95% CI)", "category": "", "color": ""})
    fig.update_layout(height=400)
    st.plotly_chart(fig)

    pr = f.assign(score=f.per_100 * np.where(f.eye_area, 1.5, 1.0)).sort_values("score", ascending=False)
    pr["priority"] = pd.cut(pr.score, [-1, 10, 30, 1000], labels=["low", "medium", "high"])
    st.success(f"**Test first:** {', '.join(pr[pr.priority == 'high'].category)}. Eye makeup is the first consumer "
               "target; tattoo ink points to a professional market (tattoo artists).")

    with st.expander("Explain this finding with AI"):
        st.caption(AI_DISCLAIMER)
        for line in explain_fda():
            st.markdown(line)

    st.divider()
    st.header("Organic and natural products skip preservatives about twice as often")
    if obf is None:
        st.warning("Put 'possibly helpful data set.zip' (or the .tsv inside it) in the same folder as this file, "
                   "then refresh.")
    else:
        o = obf_findings(obf)
        st.write(f"We checked the ingredient lists of **{len(obf):,} real products** from Open Beauty Facts "
                 f"for {len(PRESERVATIVES)} common preservatives. Microbes need water, so water-based formulas with "
                 "no recognized preservative are the riskiest once opened.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Organic / natural label", f"{o['rate_natural']:.1%}", help="Water-based, no recognized preservative")
        c2.metric("No such label", f"{o['rate_other']:.1%}")
        c3.metric("Difference", f"{o['rate_natural'] / o['rate_other']:.1f}x", help=f"Chi-square p = {o['p']:.3f}")
        left, right = st.columns(2)
        fig = px.bar(o["labels"], x="pct", y="group", orientation="h", text_auto=".0%", hover_data=["n"],
                     labels={"pct": "% water-based with no recognized preservative", "group": ""},
                     color_discrete_sequence=[ACCENT])
        fig.update_layout(xaxis_tickformat=".0%", height=320)
        left.plotly_chart(fig)
        fig = px.bar(o["by_type"], x="pct_unpreserved_water", y="type", orientation="h", text_auto=".0%",
                     hover_data=["products"], labels={"pct_unpreserved_water": "% water-based and unpreserved", "type": ""},
                     color_discrete_sequence=[OTHER])
        fig.update_layout(xaxis_tickformat=".0%", height=420)
        right.plotly_chart(fig)
        st.info("**So what:** people avoiding preservatives carry more contamination risk, so they have the most reason "
                "to check. \"Paraben-free\" isn't \"preservative-free\": brands swap in alternatives like phenoxyethanol.")

    with st.expander("Method and caveats"):
        st.markdown("""
- **FDA:** openFDA cosmetic adverse event reports. Counted reaction terms containing infection, conjunctivitis,
  hordeolum (stye), keratitis, cellulitis, abscess and similar. Reports are unvalidated and don't prove the product
  caused the reaction or was contaminated. Counts are mentions; one report can list several terms. The "other"
  average is pooled, so shampoo's 2,100 reports pull it down; deodorant and tattoo ink are as high as eyeliner.
- **Open Beauty Facts:** 2019 export, mostly French products, community-entered ingredient lists. Soap and toothpaste
  are excluded because their pH or sugar alcohols already resist microbes. A preservative missing from our list counts
  as "none". Only 20 eye products are in this dataset, so the eye-makeup focus comes from the FDA data.
""")

# ---------------- Test a product ----------------
elif page == "Test a product":
    st.title("Test a product")
    st.write("Add any product, tell Teria how you've used it, and get a test strip reading and a 0–100 score.")
    st.warning("**Demo mode:** the test strip is simulated from the product's risk factors so you can see the full "
               "flow. The photo reader that scores it is the real one. A real strip would react to microbes in the sample.")

    # ---- Step 1: the product ----
    st.subheader("Step 1 — the product")
    source = st.radio("Add it by", ["Label photo", "Search Open Beauty Facts", "My shelf", "Type it in"], horizontal=True)
    prod = {"name": "", "type": None, "ingredients": "", "packaging": "unknown", "pao": None, "eye": False}

    if source == "Label photo":
        engines = ocr_engines()
        photos = st.file_uploader("Photos of the label (front and back)", type=["png", "jpg", "jpeg", "webp"],
                                  accept_multiple_files=True)
        typed = st.text_area("No photo reader? Paste the label text instead", height=80)
        texts = []
        if photos and not engines:
            st.warning(f"No text reader installed. On a Mac run `{sys.executable} -m pip install ocrmac` and restart, "
                       "or paste the label text.")
        for ph in photos or []:
            if engines:
                with st.spinner(f"Reading {ph.name}..."):
                    t = ocr_image(Image.open(ph))
                if t and t.strip():
                    texts.append(t)
                else:
                    st.warning(f"No text found in {ph.name}. Try a sharper, closer photo.")
        if typed.strip():
            texts.append(typed)
        text = "\n".join(texts)
        if text.strip():
            vocab = ingredient_vocab(dataset_path) if dataset_path else None
            parsed = parse_label(text, vocab)
            matches = match_products(text, obf, parsed["barcode"]) if obf is not None else []
            with st.expander("Text read from the label"):
                st.text(text)
            chosen = None
            if matches:
                opts = ["None of these"] + [f"{m.product_name} · {m.brands if isinstance(m.brands, str) else ''} "
                                            f"({s:.0%} match)" for m, s in matches]
                pick = st.radio("Matched in Open Beauty Facts", opts, index=1 if matches[0][1] >= 0.8 else 0)
                chosen = matches[opts.index(pick) - 1][0] if pick != opts[0] else None
            prod.update(name=chosen.product_name if chosen is not None else "",
                        type=parsed["type"] or (chosen.type if chosen is not None else None),
                        ingredients=parsed["ingredients"] or (chosen.ingredients_text if chosen is not None else ""),
                        pao=parsed["pao_months"])
            if parsed["ingredients"]:
                st.caption(f"{parsed['ingredients_recognized']} of {parsed['ingredients_total']} ingredients matched "
                           "known names in Open Beauty Facts (misreads were corrected).")

    elif source == "Search Open Beauty Facts":
        if obf is None:
            st.warning("Dataset not found. Put the zip next to this file.")
        else:
            q = st.text_input("Product or brand", "Yves rocher")
            hits = obf[obf.product_name.fillna("").str.lower().str.contains(q.lower(), regex=False)
                       | obf.brands.fillna("").str.lower().str.contains(q.lower(), regex=False)].head(50) if q else obf.head(0)
            if len(hits):
                i = st.selectbox(f"{len(hits)} products", range(len(hits)),
                                 format_func=lambda k: f"{hits.iloc[k].product_name} · {hits.iloc[k].brands}")
                row = hits.iloc[i]
                prod.update(name=row.product_name, type=row.type, ingredients=row.ingredients_text)
            else:
                st.caption("No matches. Try 'crème', 'shampooing' or a brand.")

    elif source == "My shelf":
        shelf_ids = [i["id"] for i in st.session_state.shelf]
        if not shelf_ids:
            st.info("Your shelf is empty. Add a product using one of the other options above.")
            st.stop()
        pid = st.selectbox("Product", shelf_ids, format_func=lambda i: PRODUCTS[i]["name"])
        p = PRODUCTS[pid]
        item = next(i for i in st.session_state.shelf if i["id"] == pid)
        prod.update(name=p["name"], type=p["category"], packaging=p["packaging"], pao=p["pao"], eye=p["eye"],
                    base=p["base"],
                    ingredients={"water": "Aqua, Glycerin, Phenoxyethanol", "oil": "Ricinus Communis Oil, Cera Alba",
                                 "powder": "Talc, Mica, Zinc Stearate"}[p["base"]], shelf_id=pid,
                    opened=datetime.strptime(item["opened"], "%Y-%m-%d").date())
        st.caption("Demo shelf products use a typical formula for their base (water, oil or powder).")

    # ---- Step 2: confirm details and how it's been used ----
    st.subheader("Step 2 — check the details")
    c1, c2 = st.columns(2)
    name = c1.text_input("Product name", prod["name"], key=f"name_{source}")
    pack_keys = list(PACKAGING_STEPS) + ["unknown"]
    packaging = c2.selectbox("Packaging", pack_keys, index=pack_keys.index(prod["packaging"]),
                             format_func=lambda k: PACKAGING_STEPS.get(k, {"label": "Not sure"})["label"],
                             key=f"pack_{source}")
    pao_opts = [None, 3, 6, 9, 12, 18, 24, 36]
    pao = c1.selectbox("Open-jar symbol (months)", pao_opts, index=pao_opts.index(prod["pao"]) if prod["pao"] in pao_opts else 0,
                       format_func=lambda m: "Unknown" if m is None else f"{m}M", key=f"pao_{source}")
    opened = c2.date_input("Date opened", prod.get("opened", date(TODAY.year, max(1, TODAY.month - 4), 1)),
                           max_value=TODAY, key=f"opened_{source}")
    storage = c1.selectbox("Where it's kept", list(STORAGE_POINTS), key=f"storage_{source}")
    type_names = [t[0] for t in TYPES]
    eye_default = prod["eye"] or any(t[2] for t in TYPES if t[0] == prod["type"])
    eye = c2.checkbox("Used near the eyes", eye_default, key=f"eye_{source}")
    ingredients = st.text_area("Ingredients", prod["ingredients"] or "", height=90, key=f"ing_{source}_{name}")

    # Base (water / oil / powder) drives the formula risk score and how other pages describe the product.
    # Pre-fill from the product's known base (My shelf) or infer it from the ingredients, but let the user correct it.
    base_opts = ["water", "oil", "powder"]
    base_default = prod.get("base") or guess_base(ingredients)
    base = c1.selectbox("Formula base", base_opts,
                        index=base_opts.index(base_default) if base_default in base_opts else 0,
                        format_func=lambda b: {"water": "Water-based (aqua first)",
                                               "oil": "Oil-based (oils, butters, waxes)",
                                               "powder": "Powder (talc, mica, pressed)"}[b],
                        key=f"base_{source}",
                        help="Microbes need water, so water-based products are the highest risk. "
                             "We pre-filled a guess from the ingredients; change it if it's wrong.")

    # ---- Step 3: run the test ----
    st.subheader("Step 3 — run the test")
    light = st.radio("Lighting when the photo is taken", list(LIGHTS), horizontal=True,
                     help="Try a warm or dim light: the reader corrects color using the white reference square.")
    if "strip_seed" not in st.session_state:
        st.session_state.strip_seed = 1
    if st.button("Run test again (new simulated sample)"):
        st.session_state.strip_seed += 1

    if not name.strip():
        st.info("Add a product name to run the test.")
    else:
        factors, factor_score, fr = risk_factors(ingredients, packaging, opened, pao, storage, eye, base=base)
        seed = zlib.crc32(f"{name}|{opened}|{packaging}|{storage}".encode()) % 10000 + st.session_state.strip_seed
        strip = label_card(simulate_strip(factor_score, light, seed), name)
        r = read_strip(strip)
        signal = r["signal"] if r["status"] == "ok" else None
        score = teria_score(signal, factor_score)
        band, color, advice = score_band(score)

        left, right = st.columns([3, 2])
        left.image(strip, caption=f"Simulated Teria strip for {name} ({light.lower()})")
        with right:
            st.markdown(
                "<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem'>"
                "<span style='font-weight:600'>Teria score</span>"
                "<span style='background:#F2E4C9;color:#7a5a00;border:1px solid #e3cf9f;"
                "padding:2px 9px;border-radius:12px;font-size:0.72rem;font-weight:700;"
                "letter-spacing:0.06em'>⚠ SIMULATED DEMO</span></div>",
                unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:3.2rem;font-weight:700;line-height:1'>{score}"
                        f"<span style='font-size:1.2rem;color:#7b8682'> / 100</span></div>", unsafe_allow_html=True)
            st.markdown(badge(band, color), unsafe_allow_html=True)
            st.caption("Not a real contamination measurement or safety verdict. "
                       "The strip is generated from risk factors; thresholds await lab calibration.")
            st.write(advice)
            st.progress(score / 100)
            st.caption("Higher = more concern. 60% strip reading + 40% risk factors.")
            if signal is not None:
                st.metric("Strip reading", f"{signal:.2f}", help="0 = clean color, 1 = contaminated color")
                st.markdown("Patch as photographed "
                            f"<span style='display:inline-block;width:36px;height:16px;background:rgb{tuple(r['raw_rgb'])}'></span>"
                            " → after lighting correction "
                            f"<span style='display:inline-block;width:36px;height:16px;background:rgb{tuple(r['patch_rgb'])}'></span>",
                            unsafe_allow_html=True)
            else:
                st.warning(f"{r['reason']} The score uses risk factors only until the strip can be read.")

        st.subheader("How the score was calculated")
        c1, c2 = st.columns(2)
        c1.metric("Strip reading (60%)", f"{signal * 100:.0f} / 100" if signal is not None else "unreadable")
        c2.metric("Risk factors (40%)", f"{factor_score} / 100")
        st.dataframe(factors.rename(columns={"factor": "Risk factor", "points": "Points", "max": "Out of", "why": "Why"}),
                     hide_index=True)
        st.caption(f"Formula: {fr['advice']} Preservatives found: {', '.join(fr['found']) or 'none recognized'}.")

        guide = PACKAGING_STEPS.get(packaging, DEFAULT_STEPS)
        with st.expander(f"How to take the sample: {guide['label']}"):
            for n, step in enumerate(guide["steps"], 1):
                st.markdown(f"**{n}.** {step}")

        test_record = {"date": str(TODAY), "result": classify(signal) if signal is not None else "unreadable",
                       "signal": signal, "reason": r["reason"]}
        st.markdown("#### Save to My shelf")
        if prod.get("shelf_id"):
            # Product already on the shelf: just update its latest result.
            if st.button("Save this result to My shelf", type="primary"):
                for item in st.session_state.shelf:
                    if item["id"] == prod["shelf_id"]:
                        item["test"] = test_record
                save_state()
                st.success(f"Saved to {name}.")
        else:
            # New product (from a label photo, an OBF search, or manual entry): add it to the shelf.
            matched = source == "Search Open Beauty Facts" or (source == "Label photo" and prod.get("name"))
            st.caption(
                "This product isn't on your shelf yet. "
                + ("It matched Open Beauty Facts, " if matched else "")
                + "add it to keep its details, toss-by date and this result."
            )
            cat = prod.get("type") or "other"
            if st.button("＋ Add to My shelf with this result", type="primary", key="add_new_to_shelf"):
                pid = add_user_product(name=name, category=cat, base=base, packaging=packaging,
                                       pao=pao, eye=eye, opened=opened, ingredients=ingredients)
                for item in st.session_state.shelf:
                    if item["id"] == pid:
                        item["test"] = test_record
                save_state()
                st.success(f"Added **{name}** to My shelf (saved as {base}-based, "
                           f"{PRODUCTS[pid]['pao']}M) with this result.")
                st.caption("Open the My shelf page to see it with its toss-by date and reminders.")
    simulated("Simulated test strip. Score weights and thresholds are placeholders pending lab calibration.")

# ---------------- Scan ----------------
elif page == "Scan":
    st.title("Scan a test card")
    st.write("Guided testing in three steps: pick your product, follow the sampling walkthrough for its "
             "packaging, then photograph the whole card.")
    shelf_ids = [i["id"] for i in st.session_state.shelf]
    if not shelf_ids:
        st.info("Your shelf is empty. Add a product on the **Test a product** page first.")
        st.stop()
    pid = st.selectbox("Step 1 — which product are you testing?", shelf_ids,
                       format_func=lambda i: PRODUCTS[i]["name"])

    # ---- Step 2: guided sampling walkthrough (packaging-specific) ----
    prod = PRODUCTS[pid]
    guide = sampling_guide(pid)
    st.subheader("Step 2 — sampling walkthrough")
    st.caption(f"Packaging detected for **{prod['name']}**: {guide['label']} "
               f"· {prod['base']}-based" + (" · used near the eye" if prod.get("eye") else ""))
    for n, step in enumerate(guide["steps"], 1):
        st.markdown(f"**{n}.** {step}")
    if prod.get("eye"):
        st.markdown(badge("Eye-area product — take extra care with hygiene", "amber"), unsafe_allow_html=True)
    st.caption("These are general handling tips for the simulated test card, not a validated protocol.")

    st.subheader("Step 3 — photograph the card")
    source = st.radio("Photo", ["Sample photo", "Upload a photo", "Use camera"], horizontal=True)

    image = None
    if source == "Sample photo":
        name = st.selectbox("Sample", list(SAMPLES), index=4)
        image = make_card(**SAMPLES[name])
    else:
        up = st.file_uploader("Photo of the test card", type=["png", "jpg", "jpeg"]) if source == "Upload a photo" \
            else st.camera_input("Photograph the test card")
        if up is not None:
            pil = Image.open(up).convert("RGB")
            if pil.width > 1200:
                pil = pil.resize((1200, int(pil.height * 1200 / pil.width)))
            image = np.array(pil)

    if image is not None:
        left, right = st.columns([3, 2])
        left.image(image, caption="Test card")
        r = read_strip(image)
        key = classify(r["signal"]) if r["status"] == "ok" else "unreadable"
        res = RESULTS[key]
        right.subheader("Result")
        right.markdown(badge(res["label"], res["color"]), unsafe_allow_html=True)
        right.write(r["reason"] or res["advice"])
        if r["status"] == "ok":
            right.metric("Test signal", f"{r['signal']:.2f}", help="0 = clean color, 1 = contaminated color")
            right.progress(r["signal"])
            right.markdown(
                "Patch as photographed "
                f"<span style='display:inline-block;width:36px;height:16px;background:rgb{tuple(r['raw_rgb'])}'></span>"
                " → after lighting correction "
                f"<span style='display:inline-block;width:36px;height:16px;background:rgb{tuple(r['patch_rgb'])}'></span>",
                unsafe_allow_html=True)
        fresh_test = {"date": str(TODAY), "result": key, "signal": r["signal"], "reason": r["reason"]}
        with right.expander("Explain this result with AI"):
            st.caption(AI_DISCLAIMER)
            for line in explain_result(pid, fresh_test):
                st.markdown(line)
        if right.button("Save to My shelf", type="primary"):
            for item in st.session_state.shelf:
                if item["id"] == pid:
                    item["test"] = fresh_test
            save_state()
            right.success(f"Saved to {PRODUCTS[pid]['name']}.")

    st.divider()
    st.subheader("Formula check: how often should you test this product?")
    ing = st.text_area("Paste the ingredient list from the label",
                       "Aqua, Aloe Barbadensis Leaf Juice, Glycerin, Cetearyl Alcohol, Butyrospermum Parkii Butter, "
                       "Xanthan Gum, Lavandula Angustifolia Oil")
    show_risk(st, ing)
    with st.expander("Explain this formula check with AI"):
        st.caption(AI_DISCLAIMER)
        for line in explain_formula(ing):
            st.markdown(line)
    simulated()

# ---------------- My shelf ----------------
elif page == "My shelf":
    st.title("My shelf")
    st.write("Toss-by dates come from each product's period-after-opening symbol (the open-jar icon).")
    high_fda = set(FDA[FDA.eye_area].category)
    order = {"contaminated": 0, "unreadable": 1, "unclear": 2}

    def rank(item):
        t = item["test"]
        r = order.get(t["result"], 3) if t else 3
        if toss_by(item["opened"], PRODUCTS[item["id"]]["pao"]) < TODAY or (not t and PRODUCTS[item["id"]]["category"] in high_fda):
            r = min(r, 1)
        return r

    for item in sorted(st.session_state.shelf, key=rank):
        p, t = PRODUCTS[item["id"]], item["test"]
        tb = toss_by(item["opened"], p["pao"])
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 3])
            c1.markdown(f"**{p['name']}**  \n{p['category']} · {p['base']}-based" + (" · eye area" if p["eye"] else ""))
            if p["category"] in high_fda:
                c1.markdown(badge("High FDA infection risk", "red"), unsafe_allow_html=True)
            c2.markdown(f"Opened **{item['opened']}**  \nToss by **{tb}**")
            if tb < TODAY:
                c2.markdown(badge("Past toss-by date", "red"), unsafe_allow_html=True)
            if t:
                res = RESULTS[t["result"]]
                c3.markdown(badge(res["label"], res["color"]), unsafe_allow_html=True)
                c3.caption(f"Tested {t['date']}" + (f" · signal {t['signal']:.2f}" if t.get("signal") is not None else "")
                           + (f" · {t['reason']}" if t.get("reason") else ""))
            else:
                c3.markdown(badge("Not tested yet", "gray"), unsafe_allow_html=True)

            with st.expander("Manage this product"):
                m1, m2 = st.columns([3, 1], vertical_alignment="bottom")
                new_opened = m1.date_input("Date opened", datetime.strptime(item["opened"], "%Y-%m-%d").date(),
                                           max_value=TODAY, key=f"opened_edit_{item['id']}")
                if str(new_opened) != item["opened"]:
                    update_opened(item["id"], new_opened)
                    st.rerun()
                m2.button("Remove", key=f"remove_{item['id']}", on_click=remove_from_shelf, args=(item["id"],))
                if item["id"] in st.session_state.user_products:
                    st.caption("You added this product, so removing it deletes it completely.")
                else:
                    st.caption("This is a demo product. Removing it takes it off your shelf for this session.")

    if not st.session_state.shelf:
        st.info("Your shelf is empty. Add a product from the **Test a product** page.")

    st.divider()
    st.subheader("Care reminders")
    st.caption("Reminders are based on your opening dates and test history. They are guidance, not a safety verdict.")
    reminders = []
    for item in st.session_state.shelf:
        p, t = PRODUCTS[item["id"]], item["test"]
        tb = toss_by(item["opened"], p["pao"])
        if tb < TODAY:
            reminders.append(f"**{p['name']}** is past its toss-by date ({tb}). Consider replacing it.")
        if t and t["result"] == "contaminated":
            reminders.append(f"**{p['name']}** last tested positive on {t['date']}. Stop using it, "
                             "especially near the eyes.")
        elif t and t["result"] == "unclear":
            reminders.append(f"**{p['name']}** had an unclear result on {t['date']}. Retest in a few days.")
        elif t and t["result"] == "unreadable":
            reminders.append(f"**{p['name']}**'s last photo was unreadable. Retake it in better light.")
        elif not t and p["category"] in high_fda:
            reminders.append(f"**{p['name']}** is an eye-area product and hasn't been tested yet. "
                             "Consider running a scan.")
    if reminders:
        for rm in reminders:
            st.markdown(f"- {rm}")
    else:
        st.markdown("Nothing needs attention right now.")
    simulated("Simulated demo shelf.")

# ---------------- Community trends ----------------
elif page == "Community trends":
    st.title("Community trends")
    st.warning("**Simulated, opt-in community data.** These numbers stand in for tests that users might "
               "voluntarily and anonymously submit. They are kept separate from the FDA and Open Beauty Facts "
               "research data, which live on the Evidence page.")
    com = make_community()
    total_sub = int(com.submissions.sum())
    total_pos = int(com.positives.sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Tests submitted (simulated)", f"{total_sub:,}")
    c2.metric("Positive results among submitted tests", f"{total_pos:,}")
    c3.metric("Product categories", f"{com.category.nunique()}")

    st.subheader("Positive results among submitted tests, by category")
    st.caption("We show the share of submitted tests that came back positive, with the sample count for each "
               "category. This is not a population-wide rate, and we do not rank brands.")
    show = com[com.submissions >= 20].copy()
    show["eye_label"] = show.eye.map({True: "Used near the eye", False: "Other"})
    fig = px.bar(show, x="positive_share", y="category", orientation="h", text_auto=".0%",
                 color="eye_label", color_discrete_map={"Used near the eye": EYE, "Other": OTHER},
                 hover_data={"submissions": True, "positives": True, "positive_share": ":.0%", "eye_label": False},
                 labels={"positive_share": "Positive results among submitted tests",
                         "category": "", "eye_label": ""})
    fig.update_layout(xaxis_tickformat=".0%", height=460)
    st.plotly_chart(fig)

    st.caption("Categories with fewer than 20 submitted tests are hidden because the sample is too small to describe.")
    with st.expander("How this stays honest"):
        st.markdown("""
- **Opt-in and aggregated:** nothing here ties back to a person or a specific product; we only show category totals.
- **Framed as submitted tests:** we say "positive results among submitted tests," not a brand or market rate.
- **Sample counts shown:** every category carries its submission count, and small samples are hidden.
- **Separate from research:** this community data never mixes with the FDA or Open Beauty Facts analysis.
""")
    simulated("Simulated community submissions.")

# ---------------- Ask AI ----------------
elif page == "Ask AI":
    st.title("Ask AI")
    st.caption(AI_DISCLAIMER)
    st.write("Pick something to explain. The AI only puts Teria's own calculated results and sourced data into "
             "plain language.")

    topic = st.radio("What would you like explained?",
                     ["A product on my shelf", "The FDA finding", "A formula (ingredient list)"])

    if topic == "A product on my shelf":
        ids = [i["id"] for i in st.session_state.shelf]
        if not ids:
            st.info("Your shelf is empty. Add a product on the **Test a product** page first.")
        else:
            pick = st.selectbox("Product", ids, format_func=lambda i: PRODUCTS[i]["name"])
            item = next(i for i in st.session_state.shelf if i["id"] == pick)
            st.subheader("Test result")
            for line in explain_result(pick, item["test"]):
                st.markdown(line)
            st.subheader("Toss-by date")
            for line in explain_toss_by(pick, item["opened"]):
                st.markdown(line)
    elif topic == "The FDA finding":
        for line in explain_fda():
            st.markdown(line)
    else:
        ing = st.text_area("Paste an ingredient list",
                           "Aqua, Glycerin, Aloe Barbadensis Leaf Juice, Xanthan Gum")
        for line in explain_formula(ing):
            st.markdown(line)

    st.divider()
    st.caption("The AI does not measure contamination, diagnose conditions, or invent expiration dates. "
               "Every explanation names its source: your test, the product label, FDA reports, or Open Beauty Facts.")

# ---------------- Lab ----------------
elif page == "Lab":
    st.title("Where does the rapid test miss contamination?")
    st.write("Simulated runs comparing the rapid test to lab plate counts, the gold standard.")
    df = make_experiments()
    tp = int((df.contaminated & df.test_positive).sum())
    fn = int((df.contaminated & ~df.test_positive).sum())
    fp = int((~df.contaminated & df.test_positive).sum())
    tn = int((~df.contaminated & ~df.test_positive).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Test runs", len(df))
    c2.metric("Sensitivity", f"{tp / (tp + fn):.0%}", help="Caught when contaminated")
    c3.metric("Specificity", f"{tn / (tn + fp):.0%}", help="Clean when clean")
    c4.metric("Missed contaminations", fn, help="The dangerous error")

    c = df[df.contaminated]
    by_base = c.groupby("base").test_positive.agg(["mean", "count"]).reset_index()
    by_base.columns = ["base", "sensitivity", "samples"]
    left, right = st.columns(2)
    fig = px.bar(by_base, x="base", y="sensitivity", text_auto=".0%", hover_data=["samples"], range_y=[0, 1],
                 color_discrete_sequence=[ACCENT])
    fig.update_layout(yaxis_tickformat=".0%", height=340, title="Sensitivity by product base")
    left.plotly_chart(fig)
    cm = pd.DataFrame([[tp, fn], [fp, tn]], index=["Truly contaminated", "Truly clean"],
                      columns=["Test: contaminated", "Test: clean"])
    fig = px.imshow(cm, text_auto=True, color_continuous_scale="Purples")
    fig.update_layout(height=340, coloraxis_showscale=False, title="Rapid test vs. plate count")
    right.plotly_chart(fig)

    enough = by_base[by_base.samples >= 15].sort_values("sensitivity")
    if len(enough) >= 2:
        worst, best = enough.iloc[0], enough.iloc[-1]
        st.info(f"**Suggested next experiment:** the test catches {worst.sensitivity:.0%} of contamination in "
                f"**{worst.base}-based** products vs. {best.sensitivity:.0%} in {best.base}-based ones. Run more spiked "
                f"{worst.base}-based samples and try a different reagent or a longer development time.")
    simulated("Simulated experiment data.")

# ---------------- Find a product ----------------
elif page == "Find a product":
    st.title("Find a real product")
    if obf is None:
        st.warning("Put 'possibly helpful data set.zip' (or the .tsv inside it) in the same folder as this file, then refresh.")
    else:
        st.write(f"Search {len(obf):,} real products from Open Beauty Facts. The data is mostly French, so try "
                 "'crème', 'shampooing' or a brand name.")
        q = st.text_input("Product name, brand or barcode")
        risky = st.checkbox("Only higher-risk formulas (water-based, no recognized preservative)")
        hits = obf
        if q:
            ql = q.lower()
            hits = hits[hits.code.fillna("").eq(q) | hits.product_name.fillna("").str.lower().str.contains(ql, regex=False)
                        | hits.brands.fillna("").str.lower().str.contains(ql, regex=False)]
        if risky:
            hits = hits[(hits.risk_level == "higher") & ~hits.type.isin(SELF_PRESERVING)]
        if q or risky:
            st.caption(f"{len(hits):,} matching products. Showing up to 25.")
            for _, it in hits.head(25).iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    if isinstance(it.get("image_small_url"), str):
                        c1.image(it["image_small_url"])
                    c2.markdown(f"**{it.product_name}** · {it.brands if isinstance(it.brands, str) else 'Unknown brand'}")
                    show_risk(c2, it.ingredients_text)
                    with c2.expander("Ingredients"):
                        st.write(it.ingredients_text)
        st.caption("Source: Open Beauty Facts (community-contributed). Risk levels use keyword checks on ingredient lists.")

# ---------------- About ----------------
else:
    st.title("About Teria")
    st.markdown("""
**Teria is a platform for developing and validating rapid microbial tests.** Our first application is an
affordable at-home test for contamination in cosmetics.

**Why it matters.** Contaminated cosmetics can carry bacteria like *Pseudomonas aeruginosa* and *Staphylococcus aureus*,
which are most dangerous near the eyes. Expiration dates and smell don't tell you whether a product is contaminated.

**What the data says.** In FDA reports, eye makeup shows 3.4× the infection-related reactions of other cosmetics.
In Open Beauty Facts, organic and natural products skip preservatives about twice as often.

**How it works.** Swab the product onto a Teria strip, photograph the card, and the app corrects for lighting using the
printed reference squares and reads the color.

**For researchers.** The Lab dashboard compares the rapid test with lab plate counts and suggests the next experiment.

**Roadmap.** Lab calibration → spiked samples → pilot with makeup artists and tattoo studios → regulatory review.

**Honesty note.** The biology is not yet validated. Test thresholds, the demo shelf and lab experiments are simulated.
The FDA and Open Beauty Facts analyses use real data.
""")