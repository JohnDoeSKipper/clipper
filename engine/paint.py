"""Paintings channel renderer. One JSON spec in, one finished short out.
Look and motion are fixed here (approved on The Starry Night); the spec only
says what to show and when."""
import math, os, subprocess, sys
import numpy as np
import skia
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import core as C
import audio as A
import illus as I
import piano
from core import W, H, FPS, color, ease, ease_out, lerp, font

AMBER = "#FFD166"
CUBIC = skia.SamplingOptions(skia.CubicResampler.Mitchell())


def _sk(pil):
    return skia.Image.fromarray(np.array(pil.convert("RGBA")), colorType=skia.kRGBA_8888_ColorType)


def _backdrop(pil):
    small = pil.resize((W // 8, max(1, int(pil.height * (W / 8) / pil.width)))).filter(ImageFilter.GaussianBlur(6))
    s = max(H / small.height, W / small.width)
    big = small.resize((int(small.width * s) + 1, int(small.height * s) + 1), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30))
    x, y = (big.width - W) // 2, (big.height - H) // 2
    return _sk(big.crop((x, y, x + W, y + H)))


class Picture:
    """An image shown as a framed object on its own blurred backdrop."""

    def __init__(self, path, max_w=5200):
        pil = Image.open(path).convert("RGB")
        if pil.width > max_w:
            pil = pil.resize((max_w, int(pil.height * max_w / pil.width)), Image.LANCZOS)
        self.iw, self.ih = pil.size
        self.up = 2 if self.iw < 2600 else 1
        big = pil.resize((self.iw * self.up, self.ih * self.up), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2.0, 60, 2)) if self.up > 1 else pil
        self.img, self.bg = _sk(big), _backdrop(pil)
        self.cy = 800 if self.iw >= self.ih else 780
        self.fit = min(980 / self.iw, 900 / self.ih)
        self.full = (self.iw / 2, self.ih / 2, self.fit, 540, self.cy)

    def draw(self, c, cam, alpha=1.0):
        ax, ay, z, sx, sy = cam
        p = skia.Paint(AntiAlias=True, Color=color("#FFFFFF", alpha))
        c.drawImageRect(self.bg, skia.Rect.MakeWH(W, H), CUBIC, p)
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=color("#06080F", 0.55 * alpha)))
        x0, y0 = sx - ax * z, sy - ay * z
        dst = skia.Rect.MakeXYWH(x0, y0, self.iw * z, self.ih * z)
        c.drawRect(skia.Rect.MakeXYWH(x0 + 6, y0 + 22, self.iw * z, self.ih * z),
                   skia.Paint(AntiAlias=True, Color=color("#000000", 0.6 * alpha), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
        c.drawImageRect(self.img, skia.Rect.MakeWH(self.iw * self.up, self.ih * self.up), dst, CUBIC, p)
        c.drawRect(dst, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color=color("#F3E9D2", 0.85 * alpha)))


def _callout(canvas, text, sx, sy, a, side, dy, dx):
    if a <= 0:
        return
    f = font(C.INTER_BOLD, 38)
    pw, ph = f.measureText(text) + 56, 72
    lx, ly = sx + side * dx, max(360, sy + dy)
    px = min(max(lx if side > 0 else lx - pw, 40), W - pw - 40)
    e = ease_out(a)
    tip, start = (px + pw / 2, ly + ph / 2), (sx + side * 30, sy - 70)
    canvas.drawLine(start[0], start[1], lerp(start[0], tip[0], e), lerp(start[1], tip[1], e),
                    skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color=color("#FFFFFF", 0.9 * a)))
    rr = skia.Rect.MakeXYWH(px, ly - ph / 2, pw, ph)
    canvas.drawRoundRect(rr, 36, 36, skia.Paint(AntiAlias=True, Color=color("#0B0B0F", 0.86 * a)))
    canvas.drawRoundRect(rr, 36, 36, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color=color(AMBER, a)))
    canvas.drawString(text, px + 28, ly + 14, f, skia.Paint(AntiAlias=True, Color=color("#FFFFFF", a)))


def _brand(canvas, txt):
    f = font(C.INTER_BOLD, 28)
    x = (W - sum(f.measureText(ch) + 5 for ch in txt)) / 2 + 14
    canvas.drawCircle(x - 22, 262, 7, skia.Paint(AntiAlias=True, Color=color(AMBER)))
    for ch in txt:
        canvas.drawString(ch, x + 2, 274, f, skia.Paint(AntiAlias=True, Color=color("#000000", 0.55)))
        canvas.drawString(ch, x, 272, f, skia.Paint(AntiAlias=True, Color=color("#FFFFFF", 0.92)))
        x += f.measureText(ch) + 5


def _center(canvas, s, y, f, col, a):
    canvas.drawString(s, (W - f.measureText(s)) / 2, y, f, skia.Paint(AntiAlias=True, Color=color(col, a)))


class Film:
    def __init__(self, spec, TL, root):
        self.spec, self.TL = spec, TL
        self.total = TL[-1]["scene_end"]
        p = spec["painting"]
        self.pic = Picture(os.path.join(root, p["file"]))
        pic = self.pic
        F = pic.full
        F2 = (F[0], F[1], F[2] * 1.045, F[3], F[4])
        self.keys, self.rings, self.labels, self.inserts, self.whooshes = [], [], [], [], []
        last_free = 0.0                        # when the camera was last back on the whole painting

        def target(region, scale=None, sy=800):
            cx, cy, rx, ry = region
            z = scale * pic.fit if scale else min(max(0.45 * W / (2 * rx * pic.iw), 2.2 * pic.fit), 4.2 * pic.fit)
            return (cx * pic.iw, cy * pic.ih, z, 540, sy)

        def idle_until(t):
            nonlocal last_free
            if t - last_free > 0.6:
                self.keys.append((t - 0.25, F2, "l"))
            self.keys.append((t, F, "l"))

        for ev in spec["timeline"]:
            kind = ev["type"]
            if kind == "reveal":
                cx, cy, zm = ev["from"]
                self.keys += [(0.0, (cx * pic.iw, cy * pic.ih, pic.fit * zm, 540, 840), "e"), (ev["until"], F, "o")]
                self.title_in = ev["until"] - 0.3
                last_free = ev["until"]
            elif kind == "insert":
                self.inserts.append(self._make_insert(ev, root))
                self.whooshes.append(ev["at"] - 0.2)
            elif kind == "highlight":
                r, zt, out = ev["ring"], ev["zoom"], ev["out"]
                cam = target(ev["region"], ev.get("scale"), 880 if ev.get("tilt") else 800)
                if ev.get("tilt", {}).get("start"):
                    st = ev["tilt"]["start"]
                    cam = (st[0] * pic.iw, st[1] * pic.ih, cam[2], 540, 900)
                dur = ev.get("zoomDur", 1.1)
                idle_until(zt)
                self.keys.append((zt + dur, cam, "e"))
                self.rings.append((ev["region"], max(r, last_free - 0.15), zt + dur - 0.45, zt + dur))
                self.whooshes.append(zt)
                end_cam, hold_from = cam, zt + dur
                if ev.get("label"):
                    self._label(ev, ev["region"], max(ev.get("labelAt", 0), zt + dur - 0.1), ev.get("then", {}).get("ring", out))
                th = ev.get("then")
                if th:
                    c2 = target(th["region"], th.get("scale"))
                    self.keys += [(th["zoom"], cam, "l"), (th["zoom"] + 0.7, c2, "e")]
                    self.rings.append((th["region"], th["ring"], th["zoom"] + 0.4, th["zoom"] + 0.7))
                    self.whooshes.append(th["zoom"])
                    if th.get("label"):
                        self._label(th, th["region"], max(th.get("labelAt", 0), th["zoom"] + 0.75), out)
                    end_cam, hold_from = c2, th["zoom"] + 0.7
                tilt = ev.get("tilt")
                if tilt:
                    c2 = (tilt["to"][0] * pic.iw, tilt["to"][1] * pic.ih, cam[2], 540, 770)
                    self.keys += [(tilt["from"], cam, "l"), (tilt["until"], c2, "e")]
                    end_cam, hold_from = c2, tilt["until"]
                drift = (end_cam[0], end_cam[1], end_cam[2] * (1.0 if tilt else 1.07), end_cam[3], end_cam[4])
                self.keys += [(max(out, hold_from + 0.05), drift, "l"), (max(out, hold_from + 0.05) + 1.0, F, "e")]
                last_free = max(out, hold_from + 0.05) + 1.0
        self.keys.append((self.total, F2 if self.total - last_free > 1 else F, "l"))
        self.keys.sort(key=lambda k: k[0])
        self.museum_from = TL[-1]["scene_start"] - 1.0

    def _label(self, ev, region, on, off):
        cx, cy, rx, ry = region
        side = ev.get("labelSide", 1 if cx < 0.5 else -1)
        self.labels.append((ev["label"], cx * self.pic.iw, (cy - ry * 0.45) * self.pic.ih, on, off, side))

    def _make_insert(self, ev, root):
        d = dict(at=ev["at"], to=ev["to"], kind=ev["kind"])
        if ev["kind"] == "map":
            draw, pin = I.make_map(ev["place"], ev.get("sub", ""), ev["lat"], ev["lon"], ev.get("country"))
            d.update(img=I.bake(draw), pin=pin)
        elif ev["kind"] == "window":
            d.update(img=I.bake(I.draw_window), bars=ev.get("bars"))
        else:
            d.update(pic=Picture(os.path.join(root, ev["file"])), caption=ev.get("caption", ""), credit=ev.get("credit", ""))
        return d

    # ---- camera
    def cam_at(self, t):
        ks = self.keys
        for (t0, c0, _), (t1, c1, mode) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / max(1e-6, t1 - t0)
                u = ease(u) if mode == "e" else ease_out(u) if mode == "o" else u
                z = math.exp(lerp(math.log(c0[2]), math.log(c1[2]), u))
                return (lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u), z, lerp(c0[3], c1[3], u), lerp(c0[4], c1[4], u))
        return ks[-1][1]

    def frame(self, t):
        surf = C.new_surface()
        c = surf.getCanvas()
        pic, spec = self.pic, self.spec
        cam = self.cam_at(t)
        ax, ay, z, sx, sy = cam
        to_s = lambda px, py: (sx + (px - ax) * z, sy + (py - ay) * z)
        pic.draw(c, cam)
        for (cx, cy, rx, ry), on, f0, f1 in self.rings:
            if t < on or t > f1:
                continue
            a = 1 - ease((t - f0) / max(1e-6, f1 - f0)) if t > f0 else 1.0
            d = ease_out((t - on) / 0.45)
            ex, ey = to_s(cx * pic.iw, cy * pic.ih)
            oval = skia.Rect.MakeLTRB(ex - rx * pic.iw * z, ey - ry * pic.ih * z, ex + rx * pic.iw * z, ey + ry * pic.ih * z)
            hole = skia.Path()
            hole.addRect(skia.Rect.MakeLTRB(-200, -200, W + 200, H + 200))
            hole.addOval(oval)
            hole.setFillType(skia.PathFillType.kEvenOdd)
            c.drawPath(hole, skia.Paint(AntiAlias=True, Color=color("#000000", 0.6 * a * d), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22)))
            arc = skia.Path()
            arc.addArc(oval, -110, min(359.9, 360 * d))
            pen = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color=color("#FFFFFF", 0.95 * a))
            pen.setStrokeCap(skia.Paint.kRound_Cap)
            c.drawPath(arc, pen)
        floor = lambda a=1.0: c.drawRect(skia.Rect.MakeLTRB(0, 1200, W, H), skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [(0, 1200), (0, 1650)], [color("#000000", 0), color("#000000", 0.5 * a)])))
        floor()
        for text, px, py, on, off, side in self.labels:
            a = min(ease((t - on) / 0.3), 1 - ease((t - off) / 0.2))
            lx, ly = to_s(px, py)
            _callout(c, text, lx, ly, a, side, -230, 110)
        p = spec["painting"]
        a_title = max(0.0, min(1.0, (pic.fit * 1.097 - z) / (pic.fit * 0.065))) * ease((t - self.title_in) / 0.5)
        if a_title > 0:
            ty = pic.cy + pic.ih * pic.fit / 2 + 96
            _center(c, p["title"], ty, font(C.LORA_IT, 60), "#FFFFFF", a_title)
            sub = p.get("museum", "") if t > self.museum_from else f'{p["artist"]}  ·  {p["year"]}'
            _center(c, sub, ty + 56, font(C.INTER_SEMI, 32), "#D9DEEA", a_title)
        for ins in self.inserts:
            a = min(ease((t - ins["at"] + 0.2) / 0.5), 1 - ease((t - ins["to"]) / 0.55))
            if a <= 0:
                continue
            u = (t - ins["at"] + 0.2) / (ins["to"] + 0.55 - ins["at"] + 0.2)
            layered = a < 0.999
            if layered:
                c.saveLayerAlpha(None, int(a * 255))
            if ins["kind"] == "map":
                px, py = ins["pin"]
                v = I.show(c, ins["img"], lerp(1.0, 1.5, ease(u)), lerp(540, px, 0.75 * ease(u)), lerp(800, py - 60, 0.75 * ease(u)))
                qx, qy = I.to_screen(px, py, v)
                pulse = ((t - ins["at"]) * 0.8) % 1.0
                c.drawCircle(qx, qy, 16 + 46 * pulse, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color=color(I.GOLD, 1 - pulse)))
            elif ins["kind"] == "window":
                v = I.show(c, ins["img"], lerp(1.0, 1.16, u), 540, lerp(900, 840, u))
                if ins.get("bars") is not None:
                    I.draw_bars(c, v, (t - ins["bars"] + 0.15) / 0.9)
            else:
                q = ins["pic"]
                F = q.full
                q.draw(c, (F[0], F[1], F[2] * lerp(1.0, 1.06, u), F[3], F[4]))
                ty = q.cy + q.ih * q.fit * 1.06 / 2 + 92
                if ins["caption"]:
                    _center(c, ins["caption"], ty, font(C.LORA_IT, 50), "#FFFFFF", 1)
                if ins["credit"]:
                    _center(c, ins["credit"], ty + 46, font(C.INTER_SEMI, 24), "#B9C0D0", 0.9)
            floor(0.9)
            if layered:
                c.restore()
        _brand(c, spec.get("brand", "BEHIND THE PAINTING"))
        A.caption(c, self.TL, t, self.capf, y=1490)
        return surf

    capf = None


def render(spec, TL, voice, sr, root, out_path, tmp, frames_only=None):
    """spec has all cue strings already resolved to seconds."""
    tail = spec.get("tail", 3.2)
    TL[-1]["scene_end"] += tail
    C.prep_captions(TL, max_words=4, max_chars=22)
    film = Film(spec, TL, root)
    film.capf = A.vfont("Cormorant-700.ttf", 0, 96)
    if frames_only is not None:
        paths = []
        for t in frames_only:
            p = os.path.join(tmp, f"{spec['id']}_{t:06.2f}.png")
            C.save_png(film.frame(t), p)
            paths.append(p)
        return paths
    silent = os.path.join(tmp, spec["id"] + "_silent.mp4")
    w = C.SceneWriter(silent)
    for f in range(round(film.total * FPS)):
        w.write(film.frame(f / FPS))
    w.close()
    m = spec["music"]
    music = piano.render(os.path.join(root, m["midi"]), film.total, eighth_bpm=m.get("bpm", 84), pickup=m.get("pickup", 0),
                         bar=m.get("bar", 8), start=m.get("start", 0))
    mix = A.Mix2(film.total)
    for k, tz in enumerate(film.whooshes):
        mix.add(tz, A.whoosh(0.9, seed=11 + k), 0.045)
    wav = os.path.join(tmp, spec["id"] + ".wav")
    mix.write(wav, voice, sr, music, under_db=m.get("under_db", -12.0), duck_db=3.0)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a",
                           "-c:v", "libx264", "-crf", "24", "-preset", "medium", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", out_path])
    return out_path
