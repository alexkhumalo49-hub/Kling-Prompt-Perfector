import streamlit as st
import re
from collections import defaultdict

st.set_page_config(page_title="Kling Prompt Perfecter", layout="centered")

st.title("🔧 Kling Prompt Perfecter")
st.write(
    "Paste your rich, cinematic scene description below. This tool compresses and restructures it into a short, keyword-rich, Kling-friendly prompt."
)

# -----------------------------
# Utilities
# -----------------------------

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

# Controlled vocabulary (expand as needed)
CHARACTERS = [
    # Generic
    "man", "woman", "boy", "girl", "child", "teen", "elder", "warrior", "knight", "mage", "alchemist",
    # Project-specific seeds
    "alaric", "lys", "mentor", "clockwork golem", "golem", "warden", "courier", "guard", "villager",
]

OBJECTS = [
    "pocketwatch", "watch", "gear", "gears", "cog", "cogs", "lantern", "book", "vial", "flask", "dagger",
    "sword", "staff", "goggles", "gloves", "gauntlet", "mask", "blueprint", "scroll", "compass", "key",
    "chain", "amulet", "locket", "ring", "crystal", "device", "machine", "contraption", "tool", "wrench",
]

ENVIRONMENTS = [
    "workshop", "laboratory", "lab", "forge", "library", "clocktower", "alley", "street", "market",
    "cathedral", "temple", "ruins", "forest", "desert", "mountain", "city", "rooftop", "dock", "harbor",
    "bridge", "train", "railway", "tunnel", "cave", "warehouse", "courtyard", "palace", "throne room",
]

LIGHTING = [
    "golden", "warm", "cool", "neon", "lantern", "candlelight", "moonlight", "rim light", "backlight",
    "volumetric light", "god rays", "glow", "glowing", "shadow", "dramatic shadows", "high contrast", "noir",
]

CAMERA = [
    "close-up", "extreme close-up", "portrait", "mid-shot", "medium shot", "wide", "ultra wide", "establishing",
    "low angle", "high angle", "bird's-eye", "dutch angle", "over-the-shoulder", "os", "pov", "profile",
    "rule of thirds", "center composition", "symmetry",
]

MOOD = [
    "tense", "mysterious", "ominous", "hopeful", "melancholic", "somber", "romantic", "triumphant", "serene",
    "gritty", "epic", "urgent", "brooding", "whimsical", "austere", "eerie",
]

STYLE = [
    "cinematic", "anime", "motion graphics anime", "highly detailed", "ultra-detailed", "4k", "8k",
    "dramatic lighting", "film grain", "sharp focus", "depth of field", "bokeh", "illustrative", "stylized",
]

HAIR_EYES = [
    "silver hair", "black hair", "blonde hair", "red hair", "blue hair", "green hair", "brown hair",
    "short hair", "long hair", "messy hair", "tied hair", "braided hair", "ponytail",
    "blue eyes", "green eyes", "brown eyes", "amber eyes", "gold eyes", "silver eyes"
]

WARDROBE = [
    "tattered coat", "alchemist coat", "cloak", "hooded cloak", "robes", "armor", "leather armor",
    "apron", "goggles", "scarf", "gloves", "boots", "bracers", "belt", "satchel"
]

# Regex helpers
TOKEN_SPLIT = re.compile(r"[\s,.;:()\[\]{}\-_/]+")

# Simple keyword finder (case-insensitive, matches whole words where possible)

def find_keywords(text: str, vocab: list[str]) -> list[str]:
    out = []
    low = text.lower()
    for v in vocab:
        # match whole phrase v as a substring boundary-aware when possible
        pattern = r"(?<!\w)" + re.escape(v.lower()) + r"(?!\w)"
        if re.search(pattern, low):
            out.append(v)
    return out

# Extract noun-ish candidates (very heuristic, no NLP deps)

def noun_candidates(text: str) -> list[str]:
    words = [w for w in TOKEN_SPLIT.split(text) if w]
    # candidates are words longer than 3 letters that are alphabetic
    cands = [w.lower() for w in words if len(w) > 3 and w.isalpha()]
    return list(dict.fromkeys(cands))  # dedupe, keep order

# Compress list to top-N unique tokens, preserving original order

def compress(items: list[str], n: int) -> list[str]:
    seen = set()
    out = []
    for it in items:
        if it.lower() not in seen:
            out.append(it)
            seen.add(it.lower())
        if len(out) >= n:
            break
    return out

# Build Kling-structured prompt

def build_prompt(
    master: str,
    character_sheet: str | None = None,
    strict: bool = True,
    per_section_cap: int = 7,
    style_preset: str | None = None,
    add_quality: bool = True,
):
    master_norm = normalize(master)

    buckets = defaultdict(list)

    # Core finds from controlled vocabs
    buckets["Character"].extend(find_keywords(master_norm, CHARACTERS))
    buckets["Character"].extend(find_keywords(master_norm, HAIR_EYES))
    buckets["Character"].extend(find_keywords(master_norm, WARDROBE))

    buckets["Objects / Secondary"].extend(find_keywords(master_norm, OBJECTS))
    buckets["Environment"].extend(find_keywords(master_norm, ENVIRONMENTS))
    buckets["Lighting / Color"].extend(find_keywords(master_norm, LIGHTING))
    buckets["Camera / Composition"].extend(find_keywords(master_norm, CAMERA))
    buckets["Mood / Emotion"].extend(find_keywords(master_norm, MOOD))
    buckets["Style & Quality"].extend(find_keywords(master_norm, STYLE))

    # Heuristic extras: noun candidates that look environment-ish or object-ish
    nouns = noun_candidates(master_norm)
    # Add any nouns that are not already present and look relevant
    for n in nouns:
        if n in buckets["Environment"] or n in buckets["Objects / Secondary"]:
            continue
        # crude guesses
        if n.endswith("shop") or n.endswith("room") or n in {"ruins", "market", "harbor", "cathedral"}:
            buckets["Environment"].append(n)
        elif n in {"lanterns", "gears", "cogs", "machine", "device", "contraption", "blueprints"}:
            buckets["Objects / Secondary"].append(n.rstrip('s'))

    # Optional preset and quality anchors
    preset_styles = {
        "The Clockwork Alchemist (Default)": [
            "motion graphics anime", "cinematic", "dramatic lighting", "sharp focus"
        ],
        "Painterly Anime": ["anime", "illustrative", "soft shading"],
        "Gritty Noir": ["noir", "high contrast", "film grain"],
    }

    if style_preset and style_preset in preset_styles:
        buckets["Style & Quality"].extend(preset_styles[style_preset])

    if add_quality:
        buckets["Style & Quality"].extend(["highly detailed", "4k", "depth of field"])  # safe, generic quality cues

    # Deduplicate + compress
    for k in list(buckets.keys()):
        items = buckets[k]
        # remove near-duplicates by lowercase set while preserving order
        deduped = []
        seen = set()
        for it in items:
            key = it.lower()
            if key not in seen:
                deduped.append(it)
                seen.add(key)
        if strict:
            deduped = compress(deduped, per_section_cap)
        buckets[k] = deduped

    # Build lines in desired order
    lines = []

    if character_sheet:
        lines.append(f"Character Sheet Reference: {normalize(character_sheet)}")

    order = [
        "Character",
        "Objects / Secondary",
        "Environment",
        "Lighting / Color",
        "Camera / Composition",
        "Mood / Emotion",
        "Style & Quality",
    ]

    for k in order:
        items = buckets.get(k, [])
        if items:
            # Remove duplicates like plural vs singular basics
            line = f"{k}: " + ", ".join(items)
            lines.append(line)

    return "\n".join(lines)

# -----------------------------
# UI
# -----------------------------
with st.form("pp_form"):
    master_prompt = st.text_area(
        "Master Scene Description (paste your rich, cinematic text)",
        height=220,
        placeholder=(
            "Example: Alaric stands in the glowing workshop, giant gears turning behind him; "
            "he wears a tattered alchemist coat and messy silver hair, clutching a brass pocketwatch. "
            "Golden lantern light, tense and mysterious mood, cinematic anime style, mid-shot, dramatic shadows."
        ),
    )

    character_sheet = st.text_input(
        "(Optional) Character Sheet Reference (for consistency)",
        placeholder="Alaric — male alchemist, tall, lean, messy silver hair, sharp gold eyes, tattered coat, goggles"
    )

    col1, col2 = st.columns(2)
    with col1:
        strict = st.checkbox("Stricter compression (shorter output)", value=True)
        per_cap = st.slider("Max items per section", min_value=3, max_value=12, value=7)
    with col2:
        style_preset = st.selectbox(
            "Style Preset",
            ["The Clockwork Alchemist (Default)", "Painterly Anime", "Gritty Noir", "None"],
            index=0,
        )
        add_quality = st.checkbox("Add quality tags (highly detailed, 4k, DoF)", value=True)

    submitted = st.form_submit_button("Generate Kling Prompt")

if submitted:
    if not master_prompt.strip():
        st.warning("Please paste your master scene description.")
    else:
        preset_name = None if style_preset == "None" else style_preset
        result = build_prompt(
            master_prompt,
            character_sheet=character_sheet if character_sheet.strip() else None,
            strict=strict,
            per_section_cap=per_cap,
            style_preset=preset_name,
            add_quality=add_quality,
        )

        st.subheader("Kling-Optimized Prompt")
        st.code(result, language="text")

        st.caption(
            "Tip: If Kling still drifts, start the prompt with the Character Sheet line and keep sections under ~50-70 tokens total."
        )

st.markdown("---")
st.markdown(
    "**How to use:** Paste → (optional) add Character Sheet → choose preset → Generate → copy the result into Kling."
)
st.markdown(
    "**Pro tip:** Keep narrative words out; favor concrete visuals (props, setting, lighting, camera, mood, style)."
)
