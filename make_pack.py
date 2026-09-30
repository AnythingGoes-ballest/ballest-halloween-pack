"""Makes the Halloween Pack's files from the downloaded models (see README for their sources):
  - models/jackolantern_orange.glb: the jack-o'-lantern with its yellow pumpkin turned orange (its texture recoloured)
  - textures/*.png: the ball textures drawn here (spider web, mummy, candy corn) and the plain colours under the
    pumpkin and skull balls
  - models/*.txt: the models, in the plugin manager's model format
  - previews/*.png and icon.png: the tile pictures, drawn from the models as the host builds them (the meshes are
    read by the plugin manager's own reader, tools/tests/meshfile_test.cpp)
    python make_pack.py <path to ballest-plugin-manager>
Needs Python with NumPy and Pillow."""
import colorsys
import io
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
MODELS, TEXTURES, PREVIEWS = HERE / "models", HERE / "textures", HERE / "previews"
TOOL = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "ballest-plugin-manager") / "build" / "meshfile_test.exe"


# --- the orange jack-o'-lantern ---------------------------------------------------------------------------------------
def read_glb(path):
    b = path.read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    gltf = json.loads(b[20:20 + n])
    start = 20 + n + 8
    length = struct.unpack("<I", b[20 + n:24 + n])[0]
    return gltf, bytearray(b[start:start + length])


def write_glb(path, gltf, binary):
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    binary = bytes(binary) + b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js +
                     struct.pack("<II", len(binary), 0x004E4942) + binary)


def replace_view(gltf, binary, index, data):
    """Puts new bytes in one buffer view, moving the views after it."""
    view = gltf["bufferViews"][index]
    start, old = view.get("byteOffset", 0), view["byteLength"]
    padded = data + b"\0" * (-len(data) % 4)
    old_padded = old + (-old % 4)
    binary[start:start + old_padded] = padded
    view["byteLength"] = len(data)
    for other in gltf["bufferViews"]:
        if other is not view and other.get("byteOffset", 0) > start:
            other["byteOffset"] += len(padded) - old_padded
    gltf["buffers"][0]["byteLength"] = len(binary)


def orange_jackolantern():
    """KayKit's jack-o'-lantern is its yellow pumpkin: its pumpkin colours (hue 26-41 degrees) are moved to the orange
    pumpkin's (19 degrees on average, measured from KayKit's small pumpkin), keeping their light and shade."""
    gltf, binary = read_glb(HERE / "sources" / "jackolantern.glb")
    image = gltf["images"][0]
    view = gltf["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    rgb = np.asarray(Image.open(io.BytesIO(bytes(binary[start:start + view["byteLength"]]))).convert("RGB"), float) / 255
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in rgb.reshape(-1, 3)]).reshape(rgb.shape)
    pumpkin = (hsv[..., 0] * 360 > 22) & (hsv[..., 0] * 360 < 48) & (hsv[..., 1] > 0.35)
    hsv[..., 0] = np.where(pumpkin, np.clip(hsv[..., 0] - 14.5 / 360, 0, 1), hsv[..., 0])
    hsv[..., 1] = np.where(pumpkin, np.clip(hsv[..., 1] * 1.08, 0, 1), hsv[..., 1])
    out = np.array([colorsys.hsv_to_rgb(*p) for p in hsv.reshape(-1, 3)]).reshape(rgb.shape)
    buf = io.BytesIO()
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(buf, "PNG")
    replace_view(gltf, binary, image["bufferView"], buf.getvalue())
    write_glb(MODELS / "jackolantern_orange.glb", gltf, binary)


def glow_face(path):
    """The carved parts of the jack-o'-lantern (the dark colours of its texture: the eyes, nose and mouth) made a
    primitive of their own with a glowing orange material, so the face is lit from inside."""
    gltf, binary = read_glb(path)
    prim = gltf["meshes"][0]["primitives"][0]
    image = gltf["images"][0]
    view = gltf["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    tex = np.asarray(Image.open(io.BytesIO(bytes(binary[start:start + view["byteLength"]]))).convert("RGB"))

    def read(i):
        a = gltf["accessors"][i]
        v = gltf["bufferViews"][a["bufferView"]]
        off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        dt = np.dtype({5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]])
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        return np.frombuffer(bytes(binary[off:off + a["count"] * n * dt.itemsize]), dtype=dt).reshape(-1, n)

    idx = read(prim["indices"]).reshape(-1, 3)
    uv = read(prim["attributes"]["TEXCOORD_0"])
    h, w = tex.shape[:2]
    centre = uv[idx].mean(1)
    texel = tex[np.clip((centre[:, 1] * h).astype(int), 0, h - 1), np.clip((centre[:, 0] * w).astype(int), 0, w - 1)]
    dark = texel.max(1) < 75
    print(f"jack-o'-lantern: {int(dark.sum())} of {len(dark)} triangles are the glowing face")

    def add(indices):
        raw = indices.astype("<u4").tobytes()
        at = len(binary)
        binary.extend(raw + b"\0" * (-len(raw) % 4))
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": at, "byteLength": len(raw), "target": 34963})
        gltf["accessors"].append({"bufferView": len(gltf["bufferViews"]) - 1, "componentType": 5125, "count": int(indices.size),
                                  "type": "SCALAR"})
        return len(gltf["accessors"]) - 1

    gltf["materials"].append({"name": "carved_glow", "pbrMetallicRoughness": {"baseColorFactor": [1, 0.6, 0.1, 1], "metallicFactor": 0,
                                                                              "roughnessFactor": 1},
                               "emissiveFactor": [1.0, 0.5, 0.06],
                               "extensions": {"KHR_materials_emissive_strength": {"emissiveStrength": 1.6}}})
    gltf.setdefault("extensionsUsed", []).append("KHR_materials_emissive_strength")
    lit = {"attributes": prim["attributes"], "indices": add(idx[dark]), "material": len(gltf["materials"]) - 1}
    skin = dict(prim)
    skin["indices"] = add(idx[~dark])
    gltf["meshes"][0]["primitives"] = [skin, lit]
    gltf["buffers"][0]["byteLength"] = len(binary)
    write_glb(path, gltf, binary)


def set_material(gltf, name, base=None, emissive=None, strength=1.0, rough=None):
    """Changes the colours of every material called `name`: a plain colour, or a glowing one (the host draws a material
    with an emissive colour and no texture as glowing, at 5 x the strongest channel x `strength`)."""
    found = False
    for m in gltf["materials"]:
        if m.get("name") != name:
            continue
        found = True
        pbr = m.setdefault("pbrMetallicRoughness", {})
        pbr.pop("baseColorTexture", None)
        pbr["metallicFactor"] = 0
        if base:
            pbr["baseColorFactor"] = list(base)
        if rough is not None:
            pbr["roughnessFactor"] = rough
        if emissive:
            m["emissiveFactor"] = list(emissive)
            m["extensions"] = {"KHR_materials_emissive_strength": {"emissiveStrength": strength}}
            if "KHR_materials_emissive_strength" not in gltf.setdefault("extensionsUsed", []):
                gltf["extensionsUsed"].append("KHR_materials_emissive_strength")
    assert found, name


def lit_creatures():
    """Quaternius' ghost, ghost skull and bat are dark purple and black models that came out as silhouettes in the
    game's light. The ghost glows pale blue, the ghost skull glows green over a bone skull, and the bat is purple with
    glowing red eyes."""
    for name, edits in {
        "ghost": [("Ghost_Main", dict(base=(0.75, 0.85, 1.0, 1), emissive=(0.62, 0.8, 1.0), strength=0.9))],
        "ghost_skull": [("Ghost_Main", dict(base=(0.3, 1.0, 0.55, 1), emissive=(0.25, 1.0, 0.5), strength=0.9)),
                        ("Ghost_Secondary", dict(base=(0.85, 0.78, 0.62, 1), rough=0.6))],
        "bat": [("Main", dict(base=(0.2, 0.07, 0.34, 1), rough=0.6)), ("Black", dict(base=(0.12, 0.04, 0.2, 1), rough=0.6)),
                ("Eyes", dict(base=(1, 0.1, 0.05, 1), emissive=(1.0, 0.12, 0.05), strength=1.6))],
    }.items():
        gltf, binary = read_glb(HERE / "sources" / f"{name}.glb")
        for material, kw in edits:
            set_material(gltf, material, **kw)
        write_glb(MODELS / f"{name}.glb", gltf, binary)


# --- ball textures ------------------------------------------------------------------------------------------------------
# A ball texture wraps the ball: u (left to right) goes once around, v (top to bottom) from pole to pole. Measured on
# the racing ball at the start (a test texture of four coloured quarters): the camera behind the ball looks at u = 0.25,
# the side where a model's -x is. Textures are drawn about +x here and turned a quarter to put their front there.
TW, TH = 1024, 512


def directions():
    u, v = np.meshgrid((np.arange(TW) + 0.5) / TW, (np.arange(TH) + 0.5) / TH)
    lon = (u - 0.5) * 2 * math.pi
    lat = (0.5 - v) * math.pi
    return np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], -1), lon, lat


def save(rgb, name):
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(TEXTURES / name)


def smooth(d, width):
    return np.clip(1 - d / width, 0, 1)


def spider_web():
    """Two webs, front and back, white threads on a dark purple ball: twelve spokes and sagging rings between them."""
    p, _, _ = directions()
    col = np.zeros(p.shape) + np.array([0.20, 0.07, 0.28])
    col += (p[..., 2:3] + 1) * 0.04                                 # a little lighter on top
    web = np.zeros(p.shape[:2])
    for axis in (np.array([1.0, 0, 0]), np.array([-1.0, 0, 0])):
        up = np.array([0, 0, 1.0])
        side = np.cross(up, axis)
        theta = np.arccos(np.clip(p @ axis, -1, 1))                # angle from the web's middle
        phi = np.arctan2(p @ up, p @ side)
        near = theta < 1.45
        spokes = 12
        step = 2 * math.pi / spokes
        a = (phi + step / 2) % step - step / 2                     # angle from the nearest spoke
        web = np.maximum(web, smooth(np.abs(np.sin(a)) * np.sin(theta), 0.010) * near)
        # rings: straight between spokes (a polygon), sagging toward the middle a little
        for k in range(1, 9):
            ring = 0.16 * k
            r = ring * (math.cos(step / 2) / np.cos(a)) * (1 - 0.06 * np.cos(a * spokes / 2) ** 2)
            web = np.maximum(web, smooth(np.abs(theta - r) * 1.0, 0.011) * near * (theta > 0.05))
    col = col * (1 - web[..., None]) + np.array([0.92, 0.92, 0.96]) * web[..., None]
    col = np.roll(col, -TW // 4, axis=1)                            # a web's middle where the camera looks (u = 0.25)
    save(col, "spider_web.png")


def mummy():
    """Bandages wound round the ball at many tilts over dark gaps, and two eyes looking out of a gap at the front."""
    p, lon, lat = directions()
    rng = np.random.default_rng(31)
    col = np.zeros(p.shape) + np.array([0.12, 0.09, 0.06])
    eyes_gap = (np.abs(lat - 0.18) < 0.09) & (np.abs(lon) < 0.55)
    for i in range(46):
        n = rng.normal(size=3)
        n[2] *= 2.2                                                 # mostly wound around, not over the top
        n /= np.linalg.norm(n)
        d = p @ n - rng.uniform(-0.5, 0.5)
        width = rng.uniform(0.06, 0.1)
        band = np.abs(d) < width
        shade = rng.uniform(0.78, 0.95)
        edge = 1 - 0.35 * (np.abs(d) / width) ** 4                  # darker along its edges
        tone = np.array([0.93, 0.88, 0.76]) * shade
        stripe = 1 - 0.06 * (np.sin((p @ np.cross(n, [0, 0, 1])) * 90) > 0.8)   # a faint weave
        paint = band & ~eyes_gap
        col = np.where(paint[..., None], tone * (edge * stripe)[..., None], col)
    for side in (-1, 1):                                            # the eyes
        c = np.array([math.cos(0.18) * math.cos(0.2 * side), math.cos(0.18) * math.sin(0.2 * side), math.sin(0.18)])
        ang = np.arccos(np.clip(p @ c, -1, 1))
        col = np.where((ang < 0.11)[..., None], np.array([0.95, 0.93, 0.85]), col)
        pupil = np.array([math.cos(0.17) * math.cos(0.2 * side - 0.02), math.cos(0.17) * math.sin(0.2 * side - 0.02), math.sin(0.17)])
        col = np.where((np.arccos(np.clip(p @ pupil, -1, 1)) < 0.045)[..., None], np.array([0.05, 0.03, 0.02]), col)
    col = np.roll(col, -TW // 4, axis=1)                            # the eyes where the camera looks (u = 0.25)
    save(col, "mummy.png")


def candy_corn():
    """Candy corn's colours from bottom to top: yellow, orange, white, with soft edges between them."""
    _, _, lat = directions()
    yellow, orange, white = np.array([1.0, 0.78, 0.1]), np.array([1.0, 0.45, 0.05]), np.array([0.98, 0.96, 0.9])
    t1 = np.clip((lat + 0.35) / 0.08 + 0.5, 0, 1)[..., None]       # yellow to orange at 20 degrees below the middle
    t2 = np.clip((lat - 0.35) / 0.08 + 0.5, 0, 1)[..., None]       # orange to white at 20 degrees above
    col = yellow * (1 - t1) + orange * t1
    col = col * (1 - t2) + white * t2
    save(col, "candy_corn.png")


def plain(name, rgb):
    save(np.zeros((64, 128, 3)) + np.array(rgb), name)


# --- models ------------------------------------------------------------------------------------------------------------
def candle_flames(size, turned=False):
    """Glowing flames on the skull candle's three wicks. The wick tops were found in the model (the brown faces at the
    top of each candle, read through the host's model reader), in the file's own units; placed as the hat places the
    model: longest side (118.73) scaled to `size`, bottom of its bounds centred on the hat slot."""
    lo, hi = np.array([-51.89, -45.88, 5.75]), np.array([41.72, 45.88, 124.48])
    k = size / 118.73
    centre = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    lines = []
    for wick in ([-23.3, -10.1, 124.1], [-2.9, 7.9, 109.5], [-1.1, -14.1, 104.0]):
        p = (np.array(wick) - centre) * k
        if turned:                                  # turned round (yaw 180) about the centre of its bounds
            p[0], p[1] = -p[0], -p[1]
        lines.append(f"sphere flame r={0.9 * size / 30:.2f} at={p[0]:.1f},{p[1]:.1f},{p[2] + 1.0:.1f} scale=1,1,1.7")
    return lines


def spider_lines():
    """Two spiders on the ball, one at the front (+x) and one at the back: shapes only. Each sits on the surface with
    its legs lying along it: eight legs, four to a side, each two capsules (a rising upper part, a lower part reaching
    down to the surface). A capsule stands along z, so turning it by `roll` about x lays it along (0, cos, sin)."""
    lines = ["material spider plastic #14101a rough=0.35", "material eyes glow #ff2010 bright=8"]
    for sign, scale in ((-1, 1.0), (1, 0.65)):      # the big one on the camera side (-x)
        r = lambda v: v * scale
        base = 50 + r(3.5)
        lines.append(f"sphere spider r={r(5.5):.1f} at={sign * base:.1f},0,0 scale=0.85,1,0.95")
        lines.append(f"sphere spider r={r(8):.1f} at={sign * (base + r(1)):.1f},{r(-11):.1f},0 scale=0.85,1.15,0.95")
        for side in (-1, 1):
            lines.append(f"sphere eyes r={r(1.1):.1f} at={sign * (base + r(3.2)):.1f},{r(2.6) * side:.1f},{r(1.6):.1f}")
        for side in (-1, 1):
            for k, theta in enumerate((-50, -18, 16, 48)):
                d = (math.cos(math.radians(theta)) * side, math.sin(math.radians(theta)))
                # direction in the y-z plane, and the roll that lays a z-capsule along it
                ang = math.degrees(math.atan2(d[1], d[0]))            # from +y toward +z
                rot = 90 - ang                                        # a roll turns +z to (0, sin, cos): measured from turn()
                x1, x2 = sign * (base + r(2.5)), sign * (base - r(0.4))
                a1 = (r(4.5) * d[0], r(4.5) * d[1])
                a2 = (a1[0] + r(10) * d[0], a1[1] + r(10) * d[1])
                lines.append(f"capsule spider r={r(1.0):.2f} len={r(9):.1f} at={x1:.1f},{a1[0]:.1f},{a1[1]:.1f} rot=0,0,{rot:.1f}")
                lines.append(f"capsule spider r={r(0.8):.2f} len={r(9):.1f} at={x2:.1f},{a2[0]:.1f},{a2[1]:.1f} rot=0,0,{rot:.1f}")
    return lines


MODEL_TEXT = {
    "pumpkin_ball.txt": """# The ball as a jack-o'-lantern: KayKit's (Kay Lousberg, CC0), recoloured orange by make_pack.py, stretched a little
# upright so its body is as round as the ball and a little bigger (106 cm across), rolling with it. The ball itself is
# clear glass, so where it shows through the pumpkin's grooves the pumpkin is seen through it.
mesh jackolantern_orange.glb size=106 scale=1.07,1,1.3 at=0,0,-51 rot=0,180,0
""",
    "skull_ball.txt": """# The ball as a skull: KayKit's (Kay Lousberg, CC0), a little bigger than the ball and rolling with it. The ball itself
# is clear glass, so where it shows through, the skull is seen through it.
mesh skull.glb size=106 at=0,0,-51 rot=0,180,0
""",
    "ghost_ball.txt": """# A ghost (Quaternius, CC0, recoloured to glow by make_pack.py) floating inside a clear ball with a misty purple lower
# half, looking back at the camera. It hovers, and flies faster as the ball speeds up.
material mist glass #b58cff opacity=0.42
group shell
bowl mist r=49.5 wall=0.8
group ghost travel
mesh ghost.glb size=76 at=0,0,-32 rot=0,180,0 anim=Fast_Flying rate=0.8 run=0.08 idle=Flying_Idle
""",
    "bat_ball.txt": """# A bat (Quaternius, CC0, recoloured with glowing red eyes) flapping inside a clear ball with a dark purple lower half,
# looking back at the camera, flapping faster as the ball speeds up.
material dusk glass #5a1a8a opacity=0.55
group shell
bowl dusk r=49.5 wall=0.8
group bat travel
mesh bat.glb size=74 at=0,0,-26 rot=0,180,0 anim=Flying rate=1 run=0.12
""",
    "ghost_skull_ball.txt": """# A ghost skull (Quaternius, CC0, recoloured to glow green) floating inside a clear ball with an eerie green lower
# half, looking back at the camera. It hovers, and flies faster as the ball speeds up.
material eerie glass #4cff88 opacity=0.4
group shell
bowl eerie r=49.5 wall=0.8
group skull travel
mesh ghost_skull.glb size=76 at=0,0,-32 rot=0,180,0 anim=Fast_Flying rate=0.8 run=0.08 idle=Flying_Idle
""",
    "brew_ball.txt": """# A witch's brew: a clear ball half full of glowing green potion that stays level as the ball rolls, with a swirl of
# light turning on its surface, bubbles rising to pop, a skull and two eyeballs floating in it.
material brew glass #2cff3c opacity=0.6
material surface glow #30ff48 bright=3
material foam glow #b8ff9c bright=5
material eye plastic #f6f2e2 rough=0.25
material iris plastic #3cc060 rough=0.2
material pupil plastic #0a0a0a rough=0.1
tempo rate=0.4
group potion travel
bowl brew r=49.5 wall=0.8
disc surface r=49 hole=0 at=0,0,-0.5
mesh bubbles.glb at=0,0,-32 anim=rise rate=0.8
mesh bubbles.glb at=17,-11,-30 anim=rise rate=0.55
mesh bubbles.glb at=-17,12,-31 anim=rise rate=0.65
group swirl on=potion spin=z speed=22
ring foam r=27 thick=1.7 degrees=210 at=0,0,0.2
ring foam r=15 thick=1.4 degrees=170 at=0,0,0.2 rot=0,0,0
group skullbob on=potion bob=2.2
mesh skull.glb size=17 at=10,-14,-1 rot=0,200,0
group eyebob1 on=potion bob=1.8 phase=110
sphere eye r=5 at=-17,15,2
sphere iris r=2.9 at=-21.4,15,2
sphere pupil r=1.5 at=-23.4,15,2
group eyebob2 on=potion bob=2 phase=240
sphere eye r=4 at=-4,-24,1.5
sphere iris r=2.3 at=-7.6,-24,1.5
sphere pupil r=1.2 at=-9.2,-24,1.5
""",
    "graveyard_ball.txt": """# A snow-globe graveyard at night: a clear ball with a deep blue lower half, a moon and stars, a mound of earth with
# two graves, a dead tree with a lantern (KayKit, Kay Lousberg, CC0), two little glowing jack-o'-lanterns, green mist
# along the ground and a bat circling. Kept upright and turned the way the ball is going.
material night glass #1c1478 opacity=0.55
material earth plastic #3a2c22 rough=0.95
material grass plastic #3d5a2a rough=0.9
material moon glow #fff4b8 bright=4
material star glow #ffffff bright=6
material mist glass #7dffa0 opacity=0.18
group shell
bowl night r=49.5 wall=0.8
group yard travel
cone earth r=22 top=44 h=24 at=0,0,-44
cylinder grass r=44 h=0.8 at=0,0,-20.4
disc mist r=43 hole=0 at=0,0,-19.2
mesh gravestone.glb size=24 at=15,-17,-19.6 rot=0,-160,0
mesh grave.glb size=23 at=17,15,-19.6 rot=0,-170,0
mesh dead_tree.glb size=62 at=-13,3,-19.6 rot=0,40,0
mesh jackolantern_orange.glb size=10 at=24,2,-19.6 rot=0,180,0
mesh jackolantern_orange.glb size=8 at=-24,-17,-19.6 rot=0,150,0
sphere moon r=6.5 at=26,10,31
sphere star r=0.7 at=-10,-22,38
sphere star r=0.7 at=12,-30,30
sphere star r=0.6 at=-28,10,36
sphere star r=0.7 at=6,26,40
sphere star r=0.6 at=-4,-6,44
sphere star r=0.6 at=32,-14,22
group orbit on=yard spin=z speed=55
mesh bat.glb size=14 at=30,0,24 rot=0,90,0 anim=Flying rate=1
""",
    "spider_ball.txt": """# Two spiders on the spider web ball, a big one at the front and a smaller one at the back, made from shapes: a black
# body and abdomen, glowing red eyes and eight legs in two bent segments. They roll with the ball.
""" + "\n".join(spider_lines()) + "\n",
}

HAT_TEXT = {
    "witch_hat.txt": """# A witch's hat built from shapes: a wide brim, a tall cone bent back at its tip, a purple band and a gold buckle.
material cloth plastic #221230 rough=0.85
material band plastic #7a2cc8 rough=0.5
material buckle metal #e0b848 rough=0.3
cylinder cloth r=25 h=1.4
cone cloth r=12.5 top=5 h=22 at=0,0,1.4
cone cloth r=5 top=2.2 h=8 at=-0.8,0,23 rot=-20,0,0
cone cloth r=2.2 top=0.2 h=8 at=-3.3,0,30.5 rot=-45,0,0
cylinder band r=12.9 h=3.2 at=0,0,1.5
box buckle size=0.8,5,4.4 at=12.9,0,3.1
""",
    "jackolantern_hat.txt": """# A little jack-o'-lantern (KayKit, Kay Lousberg, CC0, recoloured orange) sitting on the ball, turned round so its
# face looks back at the camera behind the ball.
mesh jackolantern_orange.glb size=42 rot=0,180,0
""",
    "devil_horns.txt": """# Devil horns built from shapes: two red horns curving out and up.
material horn plastic #d01820 rough=0.3
cone horn r=4.2 top=3 h=8 at=2,-9,-2 rot=0,0,-20
cone horn r=3 top=1.6 h=7 at=2,-11.7,5.5 rot=0,0,-38
cone horn r=1.6 top=0.2 h=6 at=2,-15.9,11 rot=0,0,-60
cone horn r=4.2 top=3 h=8 at=2,9,-2 rot=0,0,20
cone horn r=3 top=1.6 h=7 at=2,11.7,5.5 rot=0,0,38
cone horn r=1.6 top=0.2 h=6 at=2,15.9,11 rot=0,0,60
""",
    "bat_hat.txt": """# A bat (Quaternius, CC0) hovering over the ball, flapping, turned round to look back at the camera behind the ball.
mesh bat.glb size=48 at=0,0,6 rot=0,180,0 anim=Flying rate=1
""",
    "skull_candle_hat.txt": """# A skull with three lit candles on it (KayKit, Kay Lousberg, CC0), with glowing flames on the wicks, turned round
# to look back at the camera behind the ball.
material flame glow #ffb840 bright=12
mesh skull_candle.glb size=40 rot=0,180,0
""" + "\n".join(candle_flames(40, turned=True)) + "\n",
}


def write_models():
    for name, text in {**MODEL_TEXT, **HAT_TEXT}.items():
        (MODELS / name).write_text(text, newline="\n")


# --- tile pictures -----------------------------------------------------------------------------------------------------
SIZE, SCALE = 256, 4


def turn(rot, p):
    """The engine's rotator turn (FRotationMatrix), as models.cpp applies "rot"."""
    sp, cp = math.sin(math.radians(rot[0])), math.cos(math.radians(rot[0]))
    sy, cy = math.sin(math.radians(rot[1])), math.cos(math.radians(rot[1]))
    sr, cr = math.sin(math.radians(rot[2])), math.cos(math.radians(rot[2]))
    x = np.array([cp * cy, cp * sy, sp])
    y = np.array([sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp])
    z = np.array([-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp])
    return p[:, 0:1] * x + p[:, 1:2] * y + p[:, 2:3] * z


def load_obj(path):
    v, vt, faces, mat, materials = [], [], [], None, {}
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "mtllib":
            for ml in open(path.parent / " ".join(p[1:])):
                q = ml.split()
                if q and q[0] == "newmtl":
                    cur = materials.setdefault(q[1], {"Kd": (0.8, 0.8, 0.8), "tex": None})
                elif q and q[0] == "Kd":
                    cur["Kd"] = tuple(float(x) for x in q[1:4])
                elif q and q[0] == "Ke":
                    cur["Ke"] = tuple(float(x) for x in q[1:4])
                elif q and q[0] == "map_Kd":
                    cur["tex"] = np.asarray(Image.open(ml.split(None, 1)[1].strip()).convert("RGB"), float) / 255
        elif p[0] == "v":
            v.append([float(x) for x in p[1:4]])
        elif p[0] == "vt":
            vt.append([float(x) for x in p[1:3]])
        elif p[0] == "usemtl":
            mat = p[1]
        elif p[0] == "f":
            faces.append(([int(c.split("/")[0]) - 1 for c in p[1:4]], [int(c.split("/")[1]) - 1 for c in p[1:4]], mat))
    return np.array(v), np.array(vt) if vt else np.zeros((len(v), 2)), faces, materials


def mesh_tris(line, work):
    """A mesh line's triangles and colours, posed and placed as models.cpp does."""
    words = line.split()
    opts = dict(w.split("=", 1) for w in words[2:] if "=" in w)
    num = lambda k, d: [float(x) for x in opts[k].split(",")] if k in opts else d
    size = float(opts.get("size", 0))
    anim = opts.get("anim", "")
    obj = work / (Path(words[1]).stem + ".obj")
    subprocess.run([str(TOOL), str(MODELS / words[1]), anim, "0.2", str(obj)], check=True, capture_output=True)
    rest = work / (Path(words[1]).stem + "_rest.obj")
    subprocess.run([str(TOOL), str(MODELS / words[1]), "", "0", str(rest)], check=True, capture_output=True)
    v, vt, faces, mats = load_obj(obj)
    rv = load_obj(rest)[0]
    k = size / (rv.max(0) - rv.min(0)).max() if size else 1
    scale = np.array(num("scale", [1, 1, 1]))
    rot = num("rot", [0, 0, 0])
    at = np.array(num("at", [0, 0, 0]))
    placed_rest = turn(rot, rv * k * scale)
    lo, hi = placed_rest.min(0), placed_rest.max(0)
    offset = at - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    p = turn(rot, v * k * scale) + offset
    out = []
    for idx, tidx, mat in faces:
        m = mats.get(mat, {"Kd": (0.8, 0.8, 0.8), "tex": None})
        if m["tex"] is not None:
            u, w = vt[tidx].mean(0)
            tex = m["tex"]
            colour = tex[min(int(w % 1 * tex.shape[0]), tex.shape[0] - 1), min(int(u % 1 * tex.shape[1]), tex.shape[1] - 1)] ** 2.2
        else:
            colour = np.array(m["Kd"])
        ke = np.array(m.get("Ke", (0, 0, 0)))
        if ke.max() > 0.01:                             # a glowing part is drawn at full brightness in its colour
            out.append((p[idx], ke / ke.max(), "glow", 1.0))
        else:
            out.append((p[idx], colour, "plastic", 1.0))
    return out


def shape_tris(words, mats):
    """A few of the model format's shapes as triangles: sphere, box, cylinder, cone, disc, bowl."""
    kind, mat = words[0], words[1]
    o = dict(w.split("=", 1) for w in words[2:] if "=" in w)
    num = lambda k, d: [float(x) for x in o[k].split(",")] if k in o else d
    at, rot, sc = np.array(num("at", [0, 0, 0])), num("rot", [0, 0, 0]), np.array(num("scale", [1, 1, 1]))
    kind_m, colour, alpha = mats[mat]
    seg = 28
    tris = []
    ring = lambda r, z: [np.array([r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z]) for i in range(seg)]
    if kind in ("sphere", "bowl"):
        r = float(o["r"])
        rows = 12
        top = 0.5 if kind == "bowl" else 0.0
        for j in range(rows):
            t0, t1 = top * math.pi + (1 - top) * math.pi * j / rows, top * math.pi + (1 - top) * math.pi * (j + 1) / rows
            a, b = ring(r * math.sin(t0), r * math.cos(t0)), ring(r * math.sin(t1), r * math.cos(t1))
            for i in range(seg):
                tris += [[a[i], b[i], a[(i + 1) % seg]], [a[(i + 1) % seg], b[i], b[(i + 1) % seg]]]
    elif kind in ("cylinder", "cone"):
        r = float(o["r"])
        top = float(o.get("top", r)) if kind == "cone" else r
        h = float(o["h"])
        a, b = ring(r, 0), ring(top, h)
        for i in range(seg):
            tris += [[a[i], a[(i + 1) % seg], b[i]], [b[i], a[(i + 1) % seg], b[(i + 1) % seg]]]
            tris += [[np.zeros(3), a[i], a[(i + 1) % seg]], [np.array([0, 0, h]), b[i], b[(i + 1) % seg]]]
    elif kind == "capsule":
        r, length = float(o["r"]), float(o["len"])
        a, b = ring(r, r), ring(r, r + length)
        for i in range(seg):
            tris += [[a[i], a[(i + 1) % seg], b[i]], [b[i], a[(i + 1) % seg], b[(i + 1) % seg]]]
        for cz, sign in ((r, -1), (r + length, 1)):
            rows = 6
            for j in range(rows):
                t0, t1 = math.pi / 2 * j / rows, math.pi / 2 * (j + 1) / rows
                c0 = ring(r * math.cos(t0), cz + sign * r * math.sin(t0))
                c1 = ring(r * math.cos(t1), cz + sign * r * math.sin(t1))
                for i in range(seg):
                    tris += [[c0[i], c1[i], c0[(i + 1) % seg]], [c0[(i + 1) % seg], c1[i], c1[(i + 1) % seg]]]
    elif kind == "ring":
        r, thick = float(o["r"]), float(o["thick"]) / 2
        span = math.radians(float(o.get("degrees", 360)))
        n = 40
        for i in range(n):
            a0, a1 = span * i / n, span * (i + 1) / n
            for j in range(8):
                b0, b1 = 2 * math.pi * j / 8, 2 * math.pi * (j + 1) / 8
                pt = lambda a, b: np.array([(r + thick * math.cos(b)) * math.cos(a), (r + thick * math.cos(b)) * math.sin(a), thick * math.sin(b)])
                tris += [[pt(a0, b0), pt(a1, b0), pt(a0, b1)], [pt(a1, b0), pt(a1, b1), pt(a0, b1)]]
    elif kind == "disc":
        r = float(o["r"])
        a = ring(r, 0)
        tris += [[np.zeros(3), a[i], a[(i + 1) % seg]] for i in range(seg)]
    elif kind == "box":
        s = np.array(num("size", [1, 1, 1])) / 2
        c = [np.array([x, y, z]) * s for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        for f in ((0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)):
            tris += [[c[f[0]], c[f[1]], c[f[2]]], [c[f[0]], c[f[2]], c[f[3]]]]
    out = []
    for t in tris:
        p = turn(rot, np.array(t) * sc) + at
        out.append((p, np.array(colour), kind_m, alpha))
    return out


def model_tris(text, work):
    mats, out = {}, []
    for raw in text.splitlines():
        s = raw.split("# ")[0].strip()
        if not s or s.startswith("#"):
            continue
        w = s.split()
        if w[0] == "material":
            opts = dict(x.split("=", 1) for x in w[3:] if "=" in x)
            hexes = [x for x in w[3:] if x.startswith("#")]
            h = hexes[0][1:] if hexes else "ffffff"
            colour = [(int(h[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4)]
            mats[w[1]] = (w[2], colour, float(opts.get("opacity", 1)) if w[2] == "glass" else 1.0)
        elif w[0] == "mesh":
            out += mesh_tris(s, work)
        elif w[0] in ("sphere", "bowl", "cylinder", "cone", "disc", "box", "capsule", "ring"):
            out += shape_tris(w, mats)
    return out


def srgb(c):
    return np.clip(np.power(np.clip(c, 0, 1), 1 / 2.2), 0, 1)


def draw(tris, out, ball=None, azimuth=30, elevation=15, extent=58, centre_z=0):
    """Flat-shaded triangles, farthest first. `ball`: None, "glass" (a pale disc behind and a rim in front) or a
    texture array for the ball itself."""
    az, el = math.radians(azimuth), math.radians(elevation)
    view = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
    f = -view
    right = np.array([-f[1], f[0], 0.0])
    right /= np.linalg.norm(right)
    up = np.array([0.0, 0.0, 1.0]) - f[2] * f
    up /= np.linalg.norm(up)
    light = view * 0.6 + np.array([0.0, 0.0, 0.8])
    light /= np.linalg.norm(light)
    px = SIZE * SCALE
    to_screen = lambda p: np.stack([px / 2 + (p @ right) / extent * px / 2, px / 2 - ((p @ up) - centre_z) / extent * px / 2], -1)
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    r = 50 / extent * px / 2
    c = to_screen(np.zeros((1, 3)))[0]
    if isinstance(ball, np.ndarray):
        img.alpha_composite(textured_ball(ball, view, right, up, int(2 * r)), (int(c[0] - r), int(c[1] - r)))
    elif isinstance(ball, str):
        ImageDraw.Draw(img, "RGBA").ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(205, 225, 240, 90))
    layer = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    depth = [t[0].mean(0) @ view for t in tris]
    for n in np.argsort(depth):
        p, colour, kind, alpha = tris[n]
        normal = np.cross(p[1] - p[0], p[2] - p[0])
        length = np.linalg.norm(normal)
        if length == 0:
            continue
        if kind == "glow":
            rgb = srgb(np.array(colour) / max(max(colour), 1e-3))
        else:
            rgb = srgb(np.array(colour) * (0.45 + 0.55 * abs(normal @ light) / length))
        a = 255 if kind != "glass" else int(255 * min(1.0, alpha * 1.3))
        d.polygon([tuple(q) for q in to_screen(p)], fill=tuple(int(v * 255) for v in rgb) + (a,))
    img.alpha_composite(layer)
    if isinstance(ball, str):
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(230, 240, 250, 200), width=SCALE * 5)
        d.arc([c[0] - r * 0.8, c[1] - r * 0.8, c[0] + r * 0.8, c[1] + r * 0.8], 200, 250, fill=(255, 255, 255, 170), width=SCALE * 6)
    img.resize((SIZE, SIZE), Image.LANCZOS).save(out)
    print("wrote", out.relative_to(HERE))


def textured_ball(tex, view, right, up, n):
    """The ball's own sphere with a texture, as seen along `view`, lit from above, with a shine."""
    y, x = np.mgrid[0:n, 0:n]
    sx, sy = (x + 0.5) / n * 2 - 1, 1 - (y + 0.5) / n * 2
    r2 = sx * sx + sy * sy
    inside = r2 < 1
    sz = np.sqrt(np.clip(1 - r2, 0, 1))
    p = sx[..., None] * right + sy[..., None] * up + sz[..., None] * view
    lon = np.arctan2(p[..., 1], p[..., 0]) + math.pi / 2           # u = 0.25 on the model's -x side (measured)
    lat = np.arcsin(np.clip(p[..., 2], -1, 1))
    u = ((lon / (2 * math.pi) + 0.5) * tex.shape[1]).astype(int) % tex.shape[1]
    v = np.clip(((0.5 - lat / math.pi) * tex.shape[0]).astype(int), 0, tex.shape[0] - 1)
    col = tex[v, u] ** 2.2
    light = view * 0.6 + np.array([0.0, 0.0, 0.8])
    light /= np.linalg.norm(light)
    col = col * (0.45 + 0.55 * np.clip(p @ light, 0, 1))[..., None]
    col = srgb(col)
    shine = np.exp(-(((sx + 0.42) ** 2 + (sy - 0.45) ** 2) / 0.02))
    col = col + (1 - col) * (0.7 * shine)[..., None]
    rgba = np.dstack([col, inside.astype(float)])
    return Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")


def texture(name):
    return np.asarray(Image.open(TEXTURES / name).convert("RGB"), float) / 255


def previews():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        tris = lambda f: model_tris((MODELS / f).read_text(), work)
        draw(tris("pumpkin_ball.txt"), PREVIEWS / "pumpkin.png", ball=None, azimuth=190, elevation=10, extent=62)
        draw(tris("skull_ball.txt"), PREVIEWS / "skull.png", ball=None, azimuth=195, elevation=8, extent=60)
        draw(tris("ghost_ball.txt"), PREVIEWS / "ghost.png", ball="glass", azimuth=195)
        draw(tris("bat_ball.txt"), PREVIEWS / "bat.png", ball="glass", azimuth=190)
        draw(tris("ghost_skull_ball.txt"), PREVIEWS / "ghost_skull.png", ball="glass", azimuth=195)
        draw(tris("brew_ball.txt"), PREVIEWS / "brew.png", ball="glass", azimuth=20, elevation=22)
        draw(tris("graveyard_ball.txt"), PREVIEWS / "graveyard.png", ball="glass", azimuth=200, elevation=18)
        draw(tris("spider_ball.txt"), PREVIEWS / "spider_web.png", ball=texture("spider_web.png"), azimuth=180, elevation=10, extent=56)
        draw([], PREVIEWS / "mummy.png", ball=texture("mummy.png"), azimuth=180, elevation=10, extent=52)
        draw([], PREVIEWS / "candy_corn.png", ball=texture("candy_corn.png"), azimuth=0, elevation=10, extent=52)
        draw(tris("witch_hat.txt"), PREVIEWS / "witch_hat.png", azimuth=20, elevation=18, extent=30, centre_z=14)
        draw(tris("jackolantern_hat.txt"), PREVIEWS / "jackolantern_hat.png", azimuth=185, elevation=12, extent=27, centre_z=16)
        draw(tris("devil_horns.txt"), PREVIEWS / "devil_horns.png", azimuth=10, elevation=10, extent=22, centre_z=5)
        draw(tris("bat_hat.txt"), PREVIEWS / "bat_hat.png", azimuth=185, elevation=10, extent=30, centre_z=22)
        draw(tris("skull_candle_hat.txt"), PREVIEWS / "skull_candle_hat.png", azimuth=200, elevation=12, extent=26, centre_z=19)
    Image.open(PREVIEWS / "pumpkin.png").save(HERE / "icon.png")


if __name__ == "__main__":
    for d in (TEXTURES, PREVIEWS):
        d.mkdir(exist_ok=True)
    orange_jackolantern()
    glow_face(MODELS / "jackolantern_orange.glb")
    lit_creatures()
    shutil.copy(HERE / "sources" / "bubbles.glb", MODELS / "bubbles.glb")
    spider_web()
    mummy()
    candy_corn()
    write_models()
    previews()
