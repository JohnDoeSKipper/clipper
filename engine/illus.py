"""Hand-drawn-style illustrations for the Paintings channel, drawn in code:
cream ink on night-blue paper, so white captions still read on top."""
import math, os
import numpy as np
import skia
import core as C
import audio as S3
from core import W, H, color, ease, ease_out, lerp

PAPER, INK, GOLD = "#131A30", "#EADFC4", "#F2C14E"
SS = 1.6  # illustrations are rendered once at this scale, then moved by the camera


def ink(w=4.0, a=1.0, col=INK, seed=3, rough=1.1):
    p = skia.Paint(AntiAlias=True, Color=color(col, a), StrokeWidth=w, Style=skia.Paint.kStroke_Style)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    if rough:
        p.setPathEffect(skia.DiscretePathEffect.Make(10, rough, seed))
    return p


def fill(col, a=1.0):
    return skia.Paint(AntiAlias=True, Color=color(col, a))


def path(pts, close=False):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def paper(c):
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (W / 2, 820), 1250, [color("#1B2545"), color("#0C1022")])))
    rng = np.random.default_rng(7)
    for _ in range(1400):   # paper grain
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        c.drawCircle(x, y, rng.uniform(0.6, 1.6), fill(INK, rng.uniform(0.015, 0.05)))


def text(c, s, x, y, f, a=1.0, col=INK, center=True):
    w = f.measureText(s)
    c.drawString(s, x - w / 2 if center else x, y, f, fill(col, a))


def bake(draw):
    surf = skia.Surface(int(W * SS), int(H * SS))
    c = surf.getCanvas()
    c.scale(SS, SS)
    draw(c)
    return surf.makeImageSnapshot()


def show(canvas, img, zoom=1.0, cx=W / 2, cy=H / 2, alpha=1.0):
    """Draw a baked illustration with the camera centred on (cx, cy)."""
    if alpha <= 0:
        return
    w, h = W / zoom, H / zoom
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    p = skia.Paint(AntiAlias=True, Color=color("#FFFFFF", alpha))
    canvas.drawImageRect(img, skia.Rect.MakeXYWH(x0 * SS, y0 * SS, w * SS, h * SS), skia.Rect.MakeWH(W, H),
                         skia.SamplingOptions(skia.CubicResampler.Mitchell()), p)
    return (x0, y0, zoom)


def to_screen(px, py, view):
    x0, y0, z = view
    return (px - x0) * z, (py - y0) * z


# ------------------------------------------------------------------ map of France
FR = [(2.4, 51.05), (1.85, 50.95), (1.6, 50.7), (1.4, 50.05), (0.1, 49.5), (-0.35, 49.3), (-1.2, 49.35), (-1.3, 49.68),
      (-1.9, 49.7), (-1.6, 48.8), (-1.5, 48.63), (-2.0, 48.65), (-2.8, 48.55), (-3.5, 48.82), (-4.0, 48.72), (-4.75, 48.4),
      (-4.3, 48.2), (-4.7, 48.03), (-4.2, 47.8), (-3.35, 47.72), (-2.75, 47.55), (-2.2, 47.27), (-2.0, 46.85),
      (-1.8, 46.5), (-1.15, 46.15), (-1.05, 45.62), (-1.15, 45.2), (-1.25, 44.65), (-1.3, 44.0), (-1.55, 43.48),
      (-1.78, 43.37), (-0.75, 42.95), (0.65, 42.7), (1.75, 42.5), (3.17, 42.43), (3.05, 42.8), (3.1, 43.15), (3.7, 43.4),
      (4.2, 43.47), (4.6, 43.37), (5.35, 43.3), (5.95, 43.1), (6.65, 43.25), (7.27, 43.7), (7.5, 43.78), (7.65, 44.15),
      (6.9, 44.4), (7.0, 45.0), (6.75, 45.3), (7.05, 45.9), (6.8, 46.4), (6.15, 46.15), (5.95, 46.3), (6.45, 46.9),
      (7.0, 47.4), (7.58, 47.58), (7.8, 48.6), (8.2, 48.97), (7.4, 49.15), (6.7, 49.2), (6.1, 49.47), (5.8, 49.55),
      (4.85, 49.8), (4.83, 50.15), (4.2, 49.98), (4.1, 50.3), (3.15, 50.75), (2.6, 50.85)]
CORSICA = [(9.4, 43.0), (9.55, 42.2), (9.25, 41.4), (8.8, 41.55), (8.6, 42.1), (8.75, 42.6), (9.3, 42.75)]


def geo(lon, lat):
    return 540 + (lon - 2.3) * 63.3, 800 - (lat - 46.5) * 92


PIN = geo(4.83, 43.79)   # Saint-Remy-de-Provence


def draw_map(c):
    paper(c)
    outline = path([geo(*p) for p in FR], close=True)
    c.drawPath(outline, fill("#24305A", 0.75))
    for k in range(-8, 30):   # light hatching inside the country
        c.save()
        c.clipPath(outline, doAntiAlias=True)
        c.drawLine(-200 + k * 60, 300, 400 + k * 60, 1300, ink(1.6, 0.07, rough=0))
        c.restore()
    c.drawPath(outline, ink(5, 0.95, seed=5))
    c.drawPath(outline, ink(2, 0.35, seed=9, rough=2.2))
    cor = path([geo(*p) for p in CORSICA], close=True)
    c.drawPath(cor, fill("#24305A", 0.75))
    c.drawPath(cor, ink(4, 0.9, seed=6))
    f_sm = S3.vfont("Cormorant-600.ttf", 0, 34)
    f_it = S3.vfont("CormorantGaramond-Italic.ttf", 0, 46)
    px, py = geo(2.35, 48.86)
    c.drawCircle(px, py, 7, fill(INK, 0.9))
    text(c, "Paris", px + 20, py + 11, f_sm, 0.85, center=False)
    for name, lon, lat in (("ATLANTIC", -3.6, 45.4), ("MEDITERRANEAN", 5.9, 42.25)):
        gx, gy = geo(lon, lat)
        text(c, name, gx, gy, S3.vfont("Cormorant-500.ttf", 0, 24), 0.4)
    gx, gy = PIN
    c.drawCircle(gx, gy, 11, fill(GOLD))
    c.drawCircle(gx, gy, 11, ink(2.5, 1, PAPER, rough=0))
    c.drawLine(gx - 14, gy + 4, gx - 150, gy - 120, ink(2.5, 0.8, GOLD, rough=0))
    text(c, "Saint-Rémy-de-Provence", gx - 150, gy - 172, f_it, 1.0, GOLD)
    text(c, "Saint-Paul asylum, 1889–1890", gx - 150, gy - 132, S3.vfont("Cormorant-500.ttf", 0, 30), 0.85)


# ------------------------------------------------------------------ the bedroom window
WIN = (250, 500, 830, 1150)   # left, top, right, bottom of the opening
STAR = (640, 660)


def draw_window(c):
    paper(c)
    l, t, r, b = WIN
    rng = np.random.default_rng(11)
    # stone wall: a few loose block lines
    for y in range(330, 1400, 108):
        c.drawLine(40, y, 1040, y + rng.uniform(-4, 4), ink(2, 0.13, seed=int(y)))
        off = 60 if (y // 108) % 2 else 150
        for x in range(off, 1040, 190):
            c.drawLine(x, y, x + rng.uniform(-3, 3), y + 108, ink(2, 0.11, seed=int(x + y)))
    c.drawRect(skia.Rect.MakeLTRB(l - 46, t - 46, r + 46, b + 70), fill("#0C1022", 0.9))   # deep reveal
    view = skia.Rect.MakeLTRB(l, t, r, b)
    c.save()
    c.clipRect(view, doAntiAlias=True)
    c.drawRect(view, skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [(0, t), (0, 900)], [color("#16234F"), color("#2B4A8F"), color("#7C8FB5"), color("#E8C98A")], [0, 0.55, 0.86, 1.0])))
    for k in range(60):   # brush-like dashes in the sky
        x, y = rng.uniform(l, r), rng.uniform(t, 840)
        ln = rng.uniform(18, 46)
        c.drawLine(x, y, x + ln, y + rng.uniform(-5, 5), ink(3, rng.uniform(0.06, 0.16), "#C9D6F2", seed=k))
    far = [(l, 870)] + [(l + i * 29, 845 - 38 * math.sin(i * 0.55) - 22 * math.sin(i * 1.3 + 1)) for i in range(21)] + [(r, 900), (r, 940), (l, 940)]
    c.drawPath(path(far, True), fill("#27376B"))
    c.drawPath(path(far[1:22]), ink(3, 0.6, seed=4))
    near = [(l, 915)] + [(l + i * 29, 902 - 16 * math.sin(i * 0.4 + 2)) for i in range(21)] + [(r, 950), (l, 950)]
    c.drawPath(path(near, True), fill("#1C2A55"))
    c.drawRect(skia.Rect.MakeLTRB(l, 925, r, b), skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [(0, 925), (0, b)], [color("#A88F4C"), color("#6F6238")])))
    for k in range(90):   # wheat strokes
        x, y = rng.uniform(l, r), rng.uniform(945, b)
        c.drawLine(x, y, x + rng.uniform(-10, 10), y - rng.uniform(16, 34), ink(2.5, rng.uniform(0.15, 0.4), "#E9D28C", seed=k))
    wall = [(l + 40, 1085), (l + 150, 955), (r - 110, 945), (r - 20, 1060)]   # the walled field
    c.drawPath(path(wall), ink(6, 0.9, seed=8))
    c.drawPath(path([(wall[0][0], wall[0][1] + 14), (wall[1][0] + 4, wall[1][1] + 12), (wall[2][0] - 4, wall[2][1] + 12), (wall[3][0], wall[3][1] + 14)]), ink(2.5, 0.5, seed=12))
    sx, sy = STAR   # the morning star
    c.drawCircle(sx, sy, 70, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        (sx, sy), 70, [color("#FFF3C4", 0.9), color("#FFF3C4", 0)])))
    c.drawCircle(sx, sy, 15, fill("#FFF6D6"))
    for k in range(8):
        a = k * math.pi / 4
        c.drawLine(sx + 26 * math.cos(a), sy + 26 * math.sin(a), sx + (52 if k % 2 == 0 else 38) * math.cos(a),
                   sy + (52 if k % 2 == 0 else 38) * math.sin(a), ink(3, 0.85, "#FFF3C4", seed=k))
    c.restore()
    # frame and sill
    c.drawRect(view, ink(7, 0.95, seed=2))
    c.drawRect(skia.Rect.MakeLTRB(l - 46, t - 46, r + 46, b + 70), ink(4, 0.6, seed=13))
    for (x0, y0), (x1, y1) in (((l, t), (l - 46, t - 46)), ((r, t), (r + 46, t - 46)), ((l, b), (l - 46, b + 70)), ((r, b), (r + 46, b + 70))):
        c.drawLine(x0, y0, x1, y1, ink(3, 0.5, seed=int(x0)))
    f_it = S3.vfont("CormorantGaramond-Italic.ttf", 0, 44)
    text(c, "The view from his window, before sunrise", 540, t - 96, f_it, 0.95)
    text(c, "ILLUSTRATION", 540, b + 112, S3.vfont("Cormorant-500.ttf", 0, 22), 0.45)


def draw_bars(canvas, view, prog):
    """Iron bars sliding down over the window (drawn live so they can animate)."""
    if prog <= 0:
        return
    l, t, r, b = WIN
    canvas.save()
    x0, y0, z = view
    canvas.scale(z, z)
    canvas.translate(-x0, -y0)
    canvas.clipRect(skia.Rect.MakeLTRB(l, t, r, b))
    n = 6
    for k in range(1, n):
        x = l + (r - l) * k / n
        e = ease_out(min(1.0, max(0.0, prog * 1.6 - k * 0.1)))
        yb = t + (b - t) * e
        canvas.drawLine(x, t, x, yb, skia.Paint(AntiAlias=True, Color=color("#070A16"), StrokeWidth=17, Style=skia.Paint.kStroke_Style))
        canvas.drawLine(x - 5, t, x - 5, yb, skia.Paint(AntiAlias=True, Color=color(INK, 0.35), StrokeWidth=2.5, Style=skia.Paint.kStroke_Style))
    e2 = ease_out(min(1.0, max(0.0, prog * 1.6 - 0.7)))
    for yy in (t + (b - t) * 0.33, t + (b - t) * 0.67):
        canvas.drawLine(l, yy, l + (r - l) * e2, yy, skia.Paint(AntiAlias=True, Color=color("#070A16"), StrokeWidth=13, Style=skia.Paint.kStroke_Style))
    canvas.restore()


# ------------------------------------------------------------------ generic country map
def make_map(place, sub, lat, lon, country=None):
    """Returns (draw(canvas), pin_xy): ink outline of the country containing (lat, lon), with a gold pin."""
    import json
    feats = json.load(open(os.path.join(C.ROOT, "cache/countries.geojson")))["features"]

    def inside(ring, x, y):
        hit = False
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
        return hit

    ring, name = None, country
    cands = []
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in polys:
            outer = [(a, b) for a, b in p[0]]
            if inside(outer, lon, lat):
                ring, name = outer, f["properties"].get("ADMIN")
            if country and country.lower() in (f["properties"].get("ADMIN", "").lower(), f["properties"].get("ADM0_A3", "").lower()):
                cands.append(outer)
    if ring is None and cands:
        ring = max(cands, key=len)
    if ring is None:
        raise ValueError(f"no country outline found for {place} ({lat}, {lon})")
    k = math.cos(math.radians(lat))
    xs = [a * k for a, _ in ring]
    ys = [b for _, b in ring]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    sc = 780 / span
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    geo2 = lambda lo, la: (540 + (lo * k - cx) * sc, 800 - (la - cy) * sc)
    pts = [geo2(a, b) for a, b in ring]
    step = max(1, len(pts) // 260)
    pts = pts[::step]
    pin = geo2(lon, lat)

    def draw(c):
        paper(c)
        outline = path(pts, close=True)
        c.drawPath(outline, fill("#24305A", 0.75))
        c.save()
        c.clipPath(outline, doAntiAlias=True)
        for q in range(-10, 34):
            c.drawLine(-300 + q * 60, 250, 300 + q * 60, 1350, ink(1.6, 0.07, rough=0))
        c.restore()
        c.drawPath(outline, ink(5, 0.95, seed=5))
        c.drawPath(outline, ink(2, 0.35, seed=9, rough=2.2))
        gx, gy = pin
        c.drawCircle(gx, gy, 11, fill(GOLD))
        c.drawCircle(gx, gy, 11, ink(2.5, 1, PAPER, rough=0))
        side = -1 if gx > 430 else 1
        lx, ly = gx + side * 150, gy - 120
        lx = min(max(lx, 250), W - 250)
        c.drawLine(gx + side * 14, gy - 4, lx, ly, ink(2.5, 0.8, GOLD, rough=0))
        text(c, place, lx, ly - 52, S3.vfont("CormorantGaramond-Italic.ttf", 0, 46), 1.0, GOLD)
        if sub:
            text(c, sub, lx, ly - 12, S3.vfont("Cormorant-500.ttf", 0, 30), 0.85)
        if name:
            text(c, name.upper(), 540, min(1290, max(p[1] for p in pts) + 70), S3.vfont("Cormorant-500.ttf", 0, 26), 0.45)
    return draw, pin
