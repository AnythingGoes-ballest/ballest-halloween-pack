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


# --- ball textures ------------------------------------------------------------------------------------------------------
# A ball texture wraps the ball: u (left to right) goes once around, v (top to bottom) from pole to pole. The ball's
# front (+x, the way it faces) is the texture's middle.
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
    col = np.zeros(p.shape) + np.array([0.07, 0.03, 0.10])
    col += (p[..., 2:3] + 1) * 0.02                                 # a little lighter on top
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
        web = np.maximum(web, smooth(np.abs(np.sin(a)) * np.sin(theta), 0.006) * near)
        # rings: straight between spokes (a polygon), sagging toward the middle a little
        for k in range(1, 9):
            ring = 0.16 * k
            r = ring * (math.cos(step / 2) / np.cos(a)) * (1 - 0.06 * np.cos(a * spokes / 2) ** 2)
            web = np.maximum(web, smooth(np.abs(theta - r) * 1.0, 0.007) * near * (theta > 0.05))
    col = col * (1 - web[..., None]) + np.array([0.92, 0.92, 0.96]) * web[..., None]
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
def candle_flames(size):
    """Glowing flames on the skull candle's three wicks. The wick tops were found in the model (the brown faces at the
    top of each candle, read through the host's model reader), in the file's own units; placed as the hat places the
    model: longest side (118.73) scaled to `size`, bottom of its bounds centred on the hat slot."""
    lo, hi = np.array([-51.89, -45.88, 5.75]), np.array([41.72, 45.88, 124.48])
    k = size / 118.73
    centre = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    lines = []
    for wick in ([-23.3, -10.1, 124.1], [-2.9, 7.9, 109.5], [-1.1, -14.1, 104.0]):
        p = (np.array(wick) - centre) * k
        lines.append(f"sphere flame r=0.9 at={p[0]:.1f},{p[1]:.1f},{p[2] + 1.0:.1f} scale=1,1,1.7")
    return lines


MODEL_TEXT = {
    "pumpkin_ball.txt": """# The ball as a jack-o'-lantern: KayKit's (Kay Lousberg, CC0), recoloured orange by make_pack.py, stretched a little
# upright so its body is as round as the ball and a little bigger (106 cm across), rolling with it. The ball itself is
# clear glass, so where it shows through the pumpkin's grooves the pumpkin is seen through it.
mesh jackolantern_orange.glb size=106 scale=1.07,1,1.3 at=0,0,-51
""",
    "skull_ball.txt": """# The ball as a skull: KayKit's (Kay Lousberg, CC0), a little bigger than the ball and rolling with it. The ball itself
# is clear glass, so where it shows through, the skull is seen through it.
mesh skull.glb size=106 at=0,0,-51
""",
    "ghost_ball.txt": """# A ghost (Quaternius, CC0) floating inside a clear ball with a misty purple lower half. It stays upright, faces
# where the ball is going and flies faster as the ball speeds up; still, it hovers.
material mist glass #b58cff opacity=0.35
group shell
bowl mist r=49.5 wall=0.8
group ghost travel
mesh ghost.glb size=72 at=0,0,-30 anim=Fast_Flying rate=0.8 run=0.08 idle=Flying_Idle
""",
    "bat_ball.txt": """# A bat (Quaternius, CC0) flapping inside a clear ball with a dark purple lower half, flapping faster as the ball
# speeds up. It stays upright and faces where the ball is going.
material dusk glass #4a1a6a opacity=0.5
group shell
bowl dusk r=49.5 wall=0.8
group bat travel
mesh bat.glb size=70 at=0,0,-24 anim=Flying rate=1 run=0.12
""",
    "ghost_skull_ball.txt": """# A ghost skull (Quaternius, CC0) floating inside a clear ball with an eerie green lower half. It stays upright, faces
# where the ball is going and flies faster as the ball speeds up; still, it hovers.
material eerie glass #6cff9a opacity=0.3
group shell
bowl eerie r=49.5 wall=0.8
group skull travel
mesh ghost_skull.glb size=72 at=0,0,-30 anim=Fast_Flying rate=0.8 run=0.08 idle=Flying_Idle
""",
    "brew_ball.txt": """# A witch's brew: a clear ball half full of green potion that stays level as the ball rolls, its surface glowing,
# and glowing bubbles rising and sinking in it.
material brew glass #2cff3c opacity=0.55
material surface glow #30ff48 bright=2
material bubble glow #b4ff70 bright=6
tempo rate=0.5
group potion travel
bowl brew r=49.5 wall=0.8
disc surface r=49 hole=0 at=0,0,-0.5
group b1 on=potion bob=14 phase=0
sphere bubble r=3 at=14,6,-30
group b2 on=potion bob=18 phase=90
sphere bubble r=2.2 at=-10,12,-26
group b3 on=potion bob=12 phase=200
sphere bubble r=2.6 at=4,-16,-22
group b4 on=potion bob=16 phase=300
sphere bubble r=1.8 at=-18,-6,-28
group b5 on=potion bob=10 phase=140
sphere bubble r=2 at=22,-10,-18
""",
    "graveyard_ball.txt": """# A snow-globe graveyard: a mound of dark earth with two graves and a dead tree with a lantern (KayKit, Kay
# Lousberg, CC0) inside a clear ball, kept upright and turned the way the ball is going.
material earth plastic #2c2a24 rough=0.95
material grass plastic #3a4a2a rough=0.9
group yard travel
cylinder earth r=38 h=6 at=0,0,-34
cylinder grass r=36 h=0.6 at=0,0,-28.2
mesh gravestone.glb size=18 at=12,-14,-27.6 rot=0,-15,0
mesh grave.glb size=17 at=10,12,-27.6 rot=0,10,0
mesh dead_tree.glb size=48 at=-12,2,-27.6 rot=0,40,0
""",
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
mesh jackolantern_orange.glb size=30 rot=0,180,0
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
    "bat_hat.txt": """# A bat (Quaternius, CC0) hovering over the ball, flapping.
mesh bat.glb size=34 at=0,0,6 anim=Flying rate=1
""",
    "skull_candle_hat.txt": """# A skull with three lit candles on it (KayKit, Kay Lousberg, CC0), with glowing flames on the wicks.
material flame glow #ffb840 bright=12
mesh skull_candle.glb size=30
""" + "\n".join(candle_flames(30)) + "\n",
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
        elif w[0] in ("sphere", "bowl", "cylinder", "cone", "disc", "box"):
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
    lon = np.arctan2(p[..., 1], p[..., 0])
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
        draw(tris("pumpkin_ball.txt"), PREVIEWS / "pumpkin.png", ball=None, azimuth=10, elevation=10, extent=62)
        draw(tris("skull_ball.txt"), PREVIEWS / "skull.png", ball=None, azimuth=15, elevation=8, extent=60)
        draw(tris("ghost_ball.txt"), PREVIEWS / "ghost.png", ball="glass", azimuth=15)
        draw(tris("bat_ball.txt"), PREVIEWS / "bat.png", ball="glass", azimuth=10)
        draw(tris("ghost_skull_ball.txt"), PREVIEWS / "ghost_skull.png", ball="glass", azimuth=15)
        draw(tris("brew_ball.txt"), PREVIEWS / "brew.png", ball="glass", azimuth=20, elevation=22)
        draw(tris("graveyard_ball.txt"), PREVIEWS / "graveyard.png", ball="glass", azimuth=200, elevation=18)
        for name in ("spider_web", "mummy", "candy_corn"):
            draw([], PREVIEWS / f"{name}.png", ball=texture(f"{name}.png"), azimuth=0, elevation=10, extent=52)
        draw(tris("witch_hat.txt"), PREVIEWS / "witch_hat.png", azimuth=20, elevation=18, extent=30, centre_z=14)
        draw(tris("jackolantern_hat.txt"), PREVIEWS / "jackolantern_hat.png", azimuth=185, elevation=12, extent=20, centre_z=12)
        draw(tris("devil_horns.txt"), PREVIEWS / "devil_horns.png", azimuth=10, elevation=10, extent=22, centre_z=5)
        draw(tris("bat_hat.txt"), PREVIEWS / "bat_hat.png", azimuth=5, elevation=10, extent=22, centre_z=16)
        draw(tris("skull_candle_hat.txt"), PREVIEWS / "skull_candle_hat.png", azimuth=20, elevation=12, extent=20, centre_z=14)
    Image.open(PREVIEWS / "pumpkin.png").save(HERE / "icon.png")


if __name__ == "__main__":
    for d in (TEXTURES, PREVIEWS):
        d.mkdir(exist_ok=True)
    orange_jackolantern()
    spider_web()
    mummy()
    candy_corn()
    write_models()
    previews()
