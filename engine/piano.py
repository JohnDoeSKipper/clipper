"""Piano renderer v2: 48 kHz stereo, four velocity layers of the Salamander
Grand Piano, sustain pedal, voiced melody and gentle rubato."""
import os, re, subprocess
import numpy as np
import mido
import core as C

SR = 48000
DIR = os.path.join(C.ROOT, "cache/piano48")
PC = {"C": 0, "D#": 3, "F#": 6, "A": 9}
LAYERS = [2, 5, 8, 11]
_cache = {}
_roots = []


def _load_roots():
    if not _roots:
        _roots.extend(sorted({12 * (int(m.group(2)) + 1) + PC[m.group(1)]
                              for m in (re.match(r"^([A-G]#?)(\d)v\d+\.flac$", f) for f in os.listdir(DIR)) if m}))


def _sample(root, layer):
    key = (root, layer)
    if key not in _cache:
        name = {v: k for k, v in PC.items()}[root % 12] + str(root // 12 - 1)
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(DIR, f"{name}v{layer}.flac"),
                              "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
        x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
        thr = 0.004 * np.abs(x).max()
        start = max(0, int(np.argmax(np.abs(x).max(axis=1) > thr)) - int(0.002 * SR))
        _cache[key] = x[start:]
    return _cache[key]


def _voice(midi, vel, hold, damp=0.22):
    """One note: nearest sampled pitch, crossfaded between two loudness layers."""
    _load_roots()
    root = min(_roots, key=lambda r: abs(r - midi))
    ratio = 2 ** ((midi - root) / 12)
    pos = np.clip((vel - 22) / 26.0, 0, len(LAYERS) - 1.001)     # vel 22..100 spans the four layers
    lo = int(pos)
    fr = pos - lo
    n = int((hold + damp * 6) * SR)
    out = np.zeros((n, 2), np.float32)
    for layer, w in ((LAYERS[lo], np.cos(fr * np.pi / 2)), (LAYERS[lo + 1], np.sin(fr * np.pi / 2))):
        if w < 0.02:
            continue
        src = _sample(root, layer)
        m = int(min(n, (len(src) - 2) / ratio))
        idx = np.arange(m) * ratio
        i0 = idx.astype(np.int64)
        f = (idx - i0)[:, None]
        out[:m] += w * (src[i0] * (1 - f) + src[i0 + 1] * f)
    t = np.arange(n) / SR
    env = np.where(t < hold, 1.0, np.exp(-(t - hold) / damp))
    return out * env[:, None]


def _notes(path):
    """[(eighths_from_start, eighths_long, pitch, track)]"""
    mf = mido.MidiFile(path)
    unit = mf.ticks_per_beat / 2
    notes = []
    for ti, tr in enumerate(mf.tracks):
        tick, on = 0, {}
        for msg in tr:
            tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                on.setdefault(msg.note, []).append(tick)
            elif msg.type in ("note_off", "note_on") and on.get(msg.note):
                t0 = on[msg.note].pop(0)
                notes.append((t0 / unit, (tick - t0) / unit, msg.note, ti))
    return sorted(notes)


def render(midi_path, seconds, eighth_bpm=84.0, pickup=1.0, bar=12.0, seed=5, fade_s=1.6, start=0.0):
    """Stereo float32 (n, 2). eighth_bpm sets the tempo; the score marks 132."""
    rng = np.random.default_rng(seed)
    notes = [(q - start, d, p, tr) for q, d, p, tr in _notes(midi_path) if q >= start - 1e-6]
    e = 60.0 / eighth_bpm
    tracks = sorted({n[3] for n in notes})
    rh, lh = tracks[0], tracks[-1]
    if rh == lh:                       # single-track file: split hands by pitch
        notes = [(q, d, p, 0 if p >= 60 else 1) for q, d, p, tr in notes]
        rh, lh = 0, 1

    def warp(q):                       # score position (eighths) -> seconds, with a small ritardando into each barline
        b = (q - pickup) / bar
        k = np.floor(b)
        u = b - k
        shaped = u + 0.035 * (u ** 3) - 0.012 * np.sin(2 * np.pi * u)
        return (pickup + (k + shaped / 1.035) * bar) * e

    pedal = sorted({round(q, 3) for q, d, p, tr in notes if tr == lh and p < 53})   # pedal changes on each bass note
    out = np.zeros((int((seconds + 6) * SR), 2), np.float32)
    for q, d, p, tr in notes:
        t0 = warp(q)
        if t0 > seconds + 0.5:
            continue
        nxt = next((x for x in pedal if x > q + 0.05), q + d)
        end_q = max(q + d, nxt + 0.15)                       # held by the pedal until the next change
        hold = max(0.25, warp(end_q) - t0)
        if tr == rh:                                         # the singing melody, with a slow swell across each bar
            arc = np.sin(np.pi * (((q - pickup) / bar) % 1.0))
            vel = 60 + 9 * arc + (p - 72) * 0.25
            t0 += 0.018
        elif p < 53:
            vel = 46
        else:
            vel = 37
            t0 += 0.006 * (p - 55) / 12
        vel = float(np.clip(vel + rng.normal(0, 1.8), 24, 96))
        t0 = max(0.0, t0 + rng.normal(0, 0.005))
        x = _voice(p, vel, hold)
        pan = np.clip((p - 60) / 60.0, -0.35, 0.35)         # bass a little left, treble a little right
        x = x * np.array([1 - max(0, pan), 1 + min(0, pan)], np.float32)
        a = int(t0 * SR)
        b = min(len(out), a + len(x))
        out[a:b] += x[:b - a]
    # hall: smooth stereo tail, darker as it decays
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    wet = np.zeros_like(out)
    for ch in range(2):
        nz = rng.normal(0, 1, n)
        bright = np.convolve(nz, np.ones(10) / 10, mode="same") * np.exp(-t / 0.22)
        dark = np.convolve(nz, np.ones(90) / 90, mode="same") * np.exp(-t / 0.55) * 2.2
        ir = np.concatenate([np.zeros(int(0.018 * SR)), bright + dark])
        ir /= np.sqrt((ir ** 2).sum())
        m = len(out) + len(ir)
        wet[:, ch] = np.fft.irfft(np.fft.rfft(out[:, ch], m) * np.fft.rfft(ir, m))[:len(out)]
    out = out + 0.2 * wet
    out = out[:int(seconds * SR)]
    fade = int(fade_s * SR)
    out[-fade:] *= (np.linspace(1, 0, fade) ** 1.5)[:, None]
    return (out / np.abs(out).max() * 0.9).astype(np.float32)
