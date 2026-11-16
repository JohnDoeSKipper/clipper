"""v3 look-and-sound pieces: plain white 'classy' captions, sound effects, final mix."""
import os, re, subprocess, wave
import numpy as np
import skia
import core as C
from core import W, H, color, ease_out

SR = 44100
FONTS = os.path.join(C.ROOT, "assets/fonts")
SFX = os.path.join(C.ROOT, "assets/sfx")
_tf = {}


def vfont(file, weight, size):
    """Variable font at a chosen weight."""
    key = (file, weight)
    if key not in _tf:
        tf = skia.Typeface.MakeFromFile(os.path.join(FONTS, file))
        try:
            tag = (ord("w") << 24) | (ord("g") << 16) | (ord("h") << 8) | ord("t")
            VP = skia.FontArguments.VariationPosition
            pos = VP(VP.Coordinates([VP.Coordinate(tag, float(weight))]))
            args = skia.FontArguments()
            args.setVariationDesignPosition(pos)
            tf = tf.makeClone(args)
        except Exception as e:  # static file or older binding
            print("font variation not applied:", e)
        _tf[key] = tf
    f = skia.Font(_tf[key], size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def caption(canvas, timeline, t, fnt, y=1480, plate=None, shadow="#000000", track=0.0, strong=False):
    """One phrase at a time, plain white, sentence case. Words not yet spoken
    are simply fainter white. Soft shadow instead of an outline."""
    for tl in timeline:
        if not (tl["scene_start"] <= t < tl["scene_end"]):
            continue
        chunks = tl["_chunks"]
        cur = None
        for i, ch in enumerate(chunks):
            c0 = ch[0][1]
            c1 = chunks[i + 1][0][1] if i + 1 < len(chunks) else tl["end"] + 0.3
            if c0 - 0.04 <= t < c1 - 0.04:
                cur = (ch, c0)
                break
        if cur is None:
            return
        ch, c0 = cur
        texts = [w[0].replace("...", "…") for w in ch]
        space = fnt.measureText(" ") + track
        widths = [fnt.measureText(x) for x in texts]
        total = sum(widths) + space * (len(texts) - 1)
        a_in = ease_out((t - c0 + 0.04) / 0.14)
        size = fnt.getSize()
        base = y + size * 0.33
        if plate:
            pad_x, ph = size * 0.5, size * 1.5
            rc = skia.Rect.MakeXYWH((W - total) / 2 - pad_x, y - ph / 2, total + 2 * pad_x, ph)
            canvas.drawRoundRect(rc, ph * 0.22, ph * 0.22, skia.Paint(AntiAlias=True, Color=color(plate[0], plate[1] * a_in)))
        x = (W - total) / 2
        for i, w in enumerate(ch):
            spoken = w[1] - 0.04 <= t
            a = (1.0 if spoken else (0.72 if strong else 0.5)) * a_in
            if not plate:
                for blur, sa, dy in (((22, 0.7, 5), (8, 0.8, 4), (2.2, 0.9, 3)) if strong else ((14, 0.75, 4), (4, 0.6, 2))):
                    canvas.drawString(texts[i], x, base + dy, fnt, skia.Paint(
                        AntiAlias=True, Color=color(shadow, sa * a_in),
                        MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur)))
            canvas.drawString(texts[i], x, base, fnt, skia.Paint(AntiAlias=True, Color=color("#FFFFFF", a)))
            x += widths[i] + space
        return


# ------------------------------------------------------------------ sound
def load_wav(name, gain=1.0):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(SFX, name), "-f", "f32le",
                          "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).copy()
    return x / max(1e-6, np.abs(x).max()) * gain


def _lp(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same")


def whistle(seed=1):
    """Two-toot steam whistle ('choo-choo'): three-chime chord with breath noise."""
    rng = np.random.default_rng(seed)
    out = []
    for dur in (0.26, 0.62):
        n = int(dur * SR)
        t = np.arange(n) / SR
        glide = 1 - 0.06 * np.exp(-t / 0.035) - 0.04 * np.clip((t - dur + 0.12) / 0.12, 0, 1)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
        x = np.zeros(n)
        for f, a in ((392, 1.0), (494, 0.85), (587, 0.8)):
            ph = 2 * np.pi * np.cumsum(f * glide * vib) / SR
            x += a * (np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph))
        breath = _lp(rng.normal(0, 1, n), 6) * 0.9
        env = np.clip(t / 0.04, 0, 1) * np.clip((dur - t) / 0.12, 0, 1)
        out += [(x / 3 + breath) * env, np.zeros(int(0.11 * SR))]
    y = np.concatenate(out)
    return (y / np.abs(y).max()).astype(np.float32)


def rail_clatter(dur, seed=2):
    """Low rolling rumble with the 'clack-clack' of wheels on rail joints."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    rumble = _lp(rng.normal(0, 1, n), 220) * 5
    x = rumble * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * t))
    click = _lp(rng.normal(0, 1, int(0.05 * SR)), 10) * np.exp(-np.arange(int(0.05 * SR)) / (0.012 * SR)) * 5
    k = 0.15
    while k < dur - 0.2:
        for off in (0.0, 0.11):
            a = int((k + off) * SR)
            x[a:a + len(click)] += click[:max(0, min(len(click), n - a))]
        k += 0.46
    env = np.clip(t / 0.5, 0, 1) * np.clip((dur - t) / 0.7, 0, 1)
    y = x * env
    return (y / np.abs(y).max()).astype(np.float32)


def whoosh(dur=0.45, seed=4):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    y = _lp(noise, 40) * 3 * (1 - t / dur) + _lp(noise, 8) * (t / dur)
    env = np.sin(np.pi * t / dur) ** 2
    y = y * env
    return (y / np.abs(y).max()).astype(np.float32)


def thud(seed=5):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (95 * np.exp(-t / 0.08) + 45) * t) * np.exp(-t / 0.09)
    y[:400] += np.random.default_rng(seed).normal(0, 0.4, 400) * np.exp(-np.arange(400) / 90)
    return (y / np.abs(y).max()).astype(np.float32)


def clank(seed=6):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in
            ((523, 1, .12), (1187, .7, .09), (1840, .5, .06), (2794, .35, .05), (3961, .2, .04)))
    y[:300] += np.random.default_rng(seed).normal(0, 0.6, 300) * np.exp(-np.arange(300) / 60)
    return (y / np.abs(y).max()).astype(np.float32)


def brake(dur=0.7, seed=7):
    """Steel-on-steel squeal that drops in pitch as the wheels lock."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 2600 - 900 * (t / dur) ** 1.5
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.006 * np.sin(2 * np.pi * 37 * t))) / SR
    y = np.sin(ph) + 0.5 * np.sin(1.51 * ph) + 0.3 * _lp(rng.normal(0, 1, n), 3)
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.18, 0, 1)
    y = y * env
    return (y / np.abs(y).max()).astype(np.float32)


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.fx = np.zeros(self.n, np.float32)

    def add(self, t, x, gain=1.0):
        a = int(max(0, t) * SR)
        b = min(self.n, a + len(x))
        if b > a:
            self.fx[a:b] += x[:b - a] * gain

    def write(self, path, voice, sr_v, music=None, music_gain=0.2, duck=0.5):
        n = self.n
        v = np.interp(np.linspace(0, len(voice) - 1, int(len(voice) * SR / sr_v)), np.arange(len(voice)), voice)
        v = np.pad(v, (0, max(0, n - len(v))))[:n]
        v = v / max(1e-6, np.abs(v).max()) * 0.85
        out = v + self.fx
        if music is not None:
            m = np.pad(music, (0, max(0, n - len(music))))[:n]
            env = _lp(np.abs(v), int(0.35 * SR))
            env = np.clip(env / max(1e-6, np.percentile(env, 90)), 0, 1)
            out = out + m * music_gain * (1 - duck * env)
        out = np.tanh(out * 1.05)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes((out * 32767).astype(np.int16).tobytes())


class Mix2:
    """Stereo 48 kHz final mix: voice centred, stereo music bed ducked under it."""
    R = 48000

    def __init__(self, seconds):
        self.n = int(seconds * self.R)
        self.fx = np.zeros(self.n, np.float32)

    def add(self, t, x, gain=1.0):
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * self.R / SR)), np.arange(len(x)), x)
        a = int(max(0, t) * self.R)
        b = min(self.n, a + len(x))
        if b > a:
            self.fx[a:b] += x[:b - a] * gain

    def write(self, path, voice, sr_v, music, under_db=-12.0, duck_db=3.0):
        n = self.n
        v = np.interp(np.linspace(0, len(voice) - 1, int(len(voice) * self.R / sr_v)), np.arange(len(voice)), voice)
        v = np.pad(v, (0, max(0, n - len(v))))[:n]
        v = v / max(1e-6, np.abs(v).max()) * 0.85
        m = np.zeros((n, 2), np.float32)
        k = min(n, len(music))
        m[:k] = music[:k]
        rms_v = np.sqrt((v[np.abs(v) > 0.02] ** 2).mean())
        rms_m = np.sqrt((m[:k] ** 2).mean())
        g = 10 ** ((under_db + duck_db) / 20) * rms_v / rms_m      # level when the voice is silent
        env = _lp(np.abs(v), int(0.4 * self.R))
        env = np.clip(env / max(1e-6, np.percentile(env, 85)), 0, 1)
        duck = 1 - (1 - 10 ** (-duck_db / 20)) * env
        out = (v + self.fx)[:, None] + m * (g * duck)[:, None]
        out = np.tanh(out * 1.05)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.R)
            wf.writeframes((out * 32767).astype(np.int16).tobytes())
        return under_db, under_db + duck_db
