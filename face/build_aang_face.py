"""Build ONE Furhat asset pack containing BOTH Aang faces:

  adult - Aang4        everyday: bold deep-blue arrow, light skin, blue-grey eyes
  adult - Aang4Avatar  Avatar State: glowing white-cyan arrow + solid-white "ghost" eyes,
                       on a TAN skin so the glow pops

Furhat asset packs are SINGULAR — each /assetpack/deploy REPLACES the previous pack — so
both characters MUST live in one pack to coexist after a restart. The blue/white arrow is
baked into each variant's skin texture (UV-aligned), not an overlay.

Run:  python build_aang_face.py   ->  face/Aang.zip   (then deploy + RESTART)
"""

import os
import json
import shutil
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\tmp\jules_char"                 # extracted Jules export (UV template)
BUILD = r"C:\tmp\aang_char"
ADULT = os.path.join(BUILD, "models", "adult")
TEX = os.path.join(ADULT, "textures")

# ---- arrow geometry, 1024-space (origin top-left, y down) ----
CX, TIP_Y, HEAD_BASE_Y, HEAD_HALF_W, STEM_TOP_Y, STEM_HALF_W = 511, 262, 138, 105, 38, 44

# Both characters, in one pack. Bump skin/eye-set names when iterating a texture (fresh
# names dodge the asset-pack texture cache); character names stay stable for config/SDK.
# bright_mul/bright_add tune projector glow: the everyday face stays light (the look you
# liked); the Avatar face is deliberately DARKER (warm brown) so it doesn't glow "super
# bright" and the white arrow + ghost eyes pop hard against it.
# Both faces share the SAME warm light-brown skin (per the reference photos). They differ
# ONLY in the arrow colour (deep blue vs glowing white) and the eyes (blue-grey vs white
# ghost). The arrow geometry is identical, so it sits in the EXACT same spot on both — in
# the Avatar State it just blazes white with a soft glow halo, like the show.
# Aang's skin is the SAME in both modes (lore-accurate) — only the arrow + eyes glow in the Avatar
# State. So ONE dark warm Mediterranean skin for both faces, with tm_skins_c WHITE so the baked
# pure-white avatar arrow stays full brightness and the white ghost-eyes (a separate texture) pop on
# the dark skin. Fine-tune HUE live via tm_skins_c; darkness changes need a rebuild + reboot.
_SKIN = dict(skin_target=(90, 65, 45), skin_blend=0.85,
             bright_mul=0.9, bright_add=0, skin_tint="#FFFFFFFF")
VARIANTS = [
    dict(char="Aang4", skin="aang11", arrow=(45, 110, 215), eye_color="#6B93B8FF",
         eye_set="default", ghost=False, glow=False, **_SKIN),
    dict(char="Aang4Avatar", skin="aang11avatar", arrow=(255, 255, 255), eye_color="#FFFFFFFF",
         eye_set="aang9ghost", ghost=True, glow=True, **_SKIN),
]


def reset_build():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    shutil.copytree(SRC, BUILD)


def arrow_alpha():
    S = 2
    W = 1024 * S
    a = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(a)
    cx = CX * S
    d.polygon([(cx, TIP_Y * S), (cx - HEAD_HALF_W * S, HEAD_BASE_Y * S),
               (cx + HEAD_HALF_W * S, HEAD_BASE_Y * S)], fill=255)
    d.rectangle([cx - STEM_HALF_W * S, STEM_TOP_Y * S,
                 cx + STEM_HALF_W * S, (HEAD_BASE_Y + 8) * S], fill=255)
    return a.resize((1024, 1024), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.35))


def make_skin(skin_name, arrow_color, skin_target, skin_blend, alpha, bright_mul, bright_add,
              glow=False, preview=False):
    src = os.path.join(TEX, "textureSets", "skins", "naturalistic_dark_02")
    arr = np.asarray(Image.open(os.path.join(src, "skinAlbedo.png")).convert("RGB")).astype(np.float32)
    arr = np.clip(arr * bright_mul + bright_add, 0, 255)
    target = np.array(skin_target, dtype=np.float32)
    arr = np.clip(arr * (1 - skin_blend) + target * skin_blend, 0, 255)
    skin = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    if glow:   # strong white bloom so the arrow blazes far brighter than the dark skin
        wide = alpha.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.55))
        tight = alpha.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.85))
        for halo in (wide, tight):
            layer = Image.new("RGBA", skin.size, (255, 255, 255, 0))
            layer.putalpha(halo)
            skin = Image.alpha_composite(skin, layer)
    arrow = Image.new("RGBA", skin.size, tuple(arrow_color) + (0,))
    arrow.putalpha(alpha)
    skin = Image.alpha_composite(skin, arrow).convert("RGB")
    out = os.path.join(TEX, "textureSets", "skins", skin_name)
    os.makedirs(out, exist_ok=True)
    skin.save(os.path.join(out, "skinAlbedo.png"))
    shutil.copy(os.path.join(src, "skinNormals.png"), os.path.join(out, "skinNormals.png"))
    if preview:
        skin.crop((300, 20, 724, 460)).save(os.path.join(HERE, "aang_face_preview.png"))


def make_ghost_eyes(eye_set):
    src = os.path.join(TEX, "textureSets", "eyes", "default")
    out = os.path.join(TEX, "textureSets", "eyes", eye_set)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(src):
        shutil.copy(os.path.join(src, f), os.path.join(out, f))
    eye = Image.open(os.path.join(src, "eye.png"))
    Image.new("RGBA", eye.size, (255, 255, 255, 255)).save(os.path.join(out, "eye.png"))


def write_profile(char, skin, eye_set, eye_color, skin_tint):
    base = json.load(open(os.path.join(ADULT, "profiles", "characters", "Jules.json"), encoding="utf-8"))
    p = {x["NAME"]: x["VAL"] for x in base["Parameters"]}
    p["tm_skins_t"], p["tm_skins_c"] = skin, skin_tint
    p["tm_eyes_t"], p["tm_eyes_c"] = eye_set, eye_color
    p["to_facial-hair_t"] = ""        # no goatee
    p["to_tattoos_t"] = ""            # arrow is baked into the skin
    p["to_lips_t"] = ""               # no lipstick
    p["to_skin-texture_c"] = "#00000018"
    p["to_eyebrows_c"] = "#3D2F28FF"
    p["to_freckles_t"] = ""
    p["to_spots_t"] = ""
    p["to_nose_t"] = ""
    p["EyebrowSize"] = "0.30"
    p["EyeSize"] = "0.65"
    p["EyeRoundness"] = "0.55"
    p["NoseHeight"] = "0.30"
    p["Nose size/nostril width"] = "0.55"
    p["ChinHeight"] = "0.45"
    p["ChinWidth"] = "0.75"
    p["MouthWidth"] = "0.42"
    p["MouthSize"] = "0.42"
    base["Parameters"] = [{"NAME": k, "VAL": v} for k, v in p.items()]
    json.dump(base, open(os.path.join(ADULT, "profiles", "characters", f"{char}.json"), "w",
                         encoding="utf-8"), indent=2)


def main():
    reset_build()
    alpha = arrow_alpha()
    for i, v in enumerate(VARIANTS):
        make_skin(v["skin"], v["arrow"], v["skin_target"], v["skin_blend"], alpha,
                  v["bright_mul"], v["bright_add"], glow=v.get("glow", False), preview=(i == 0))
        if v["ghost"]:
            make_ghost_eyes(v["eye_set"])
        write_profile(v["char"], v["skin"], v["eye_set"], v["eye_color"], v["skin_tint"])
    os.remove(os.path.join(ADULT, "profiles", "characters", "Jules.json"))
    json.dump({"CharacterName": "Aang", "CharacterPack": "", "SourceMask": "adult",
               "Version": "1.0", "ExportDate": "2026-06-16 00:00:00"},
              open(os.path.join(BUILD, "manifest.json"), "w", encoding="utf-8"))

    out = os.path.join(HERE, "Aang.zip")
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(BUILD):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, BUILD))
    print("built combined pack:", out, os.path.getsize(out), "bytes")
    print("characters:", ", ".join(v["char"] for v in VARIANTS))


if __name__ == "__main__":
    main()
