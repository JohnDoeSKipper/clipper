"""Shared pieces for CLIPPER sample shorts: voice, captions, audio bed, encoder."""
import math, os, re, subprocess, wave
import numpy as np
import skia

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/fonts") + "/"
POPPINS_BOLD = GF + "Poppins-Bold.ttf"
LORA = GF + "Lora-Variable.ttf"
LORA_IT = GF + "Lora-Italic-Variable.ttf"
INTER_SEMI = GF + "Inter-SemiBold.otf"
INTER_BOLD = GF + "Inter-Bold.otf"

_tf_cache = {}


def font(path, size):
    if path not in _tf_cache:
        _tf_cache[path] = skia.Typeface.MakeFromFile(path)
    f = skia.Font(_tf_cache[path], size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def color(hexstr, a=1.0):
    h = hexstr.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return skia.Color(r, g, b, int(max(0, min(1, a)) * 255))


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- voice
_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(ROOT, "cache/models/kokoro-v1.0.onnx"),
                         os.path.join(ROOT, "cache/models/voices-v1.0.bin"))
    return _kokoro


def _trim(x, sr, thr=0.012, pad=0.03):
    win = int(sr * 0.01)
    env = np.abs(x)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * sr))
    b = min(len(x), idx[-1] + int(pad * sr))
    return x[a:b]


def _word_weight(k, word):
    core = re.sub(r"[^A-Za-z0-9']", "", word)
    try:
        ph = k.tokenizer.phonemize(core or word, "en-us")
        n = len(re.sub(r"\s", "", ph))
    except Exception:
        n = len(core)
    n = max(n, 2)
    if re.search(r"[,;:]$", word):
        n += 3
    if re.search(r"(—|\.\.\.|\?|!|\.)$", word):
        n += 4
    return n


def _silences(x, sr, min_len=0.09):
    hop = int(sr * 0.01)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
    thr = max(0.006, 0.04 * rms.max())
    quiet = rms < thr
    gaps, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_len and i > 3 and j < n - 3:
                gaps.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return gaps


def _align(k, words, x, sr, t_off):
    """Word timings. First a proportional estimate from phoneme counts, then
    clause boundaries are snapped to the real pauses found in the audio."""
    dur = len(x) / sr
    wts = [_word_weight(k, w) for w in words]
    base = [max(2, w - (3 if re.search(r"[,;:]$", wd) else 0)
                - (4 if re.search(r"(—|\.\.\.|\?|!|\.)$", wd) else 0))
            for w, wd in zip(wts, words)]
    tot = float(sum(wts))
    # estimated end time of each word that closes a clause
    acc, est = 0.0, {}
    for i, (wd, w) in enumerate(zip(words, wts)):
        acc += w
        if i < len(words) - 1 and re.search(r"(,|;|:|—|\.\.\.|\?|!|\.)$", wd):
            est[i] = dur * acc / tot
    pins = {}  # word index -> (gap start, gap end)
    for g0, g1 in sorted(_silences(x, sr, 0.18), key=lambda g: g[0] - g[1]):
        mid = (g0 + g1) / 2
        cands = [i for i in est if i not in pins and abs(est[i] - mid) < 0.75]
        if not cands:
            continue
        i = min(cands, key=lambda i: abs(est[i] - mid))
        ok = all((j < i and pins[j][1] <= g0) or (j > i and pins[j][0] >= g1) for j in pins)
        if ok:
            pins[i] = (g0, g1)
    out, seg_start, seg_t = [], 0, 0.0
    cuts = sorted(pins) + [len(words) - 1]
    for c in cuts:
        seg_end_t = pins[c][0] if c in pins else dur
        idx = list(range(seg_start, c + 1))
        # inside a segment keep pause weight for unpinned punctuation, none on the last word
        ws = [(base[i] if i == c else wts[i]) for i in idx]
        st, a2 = float(sum(ws)), 0.0
        for i, w in zip(idx, ws):
            t0 = seg_t + (seg_end_t - seg_t) * a2 / st
            a2 += w
            out.append((words[i], t_off + t0, t_off + seg_t + (seg_end_t - seg_t) * a2 / st))
        if c in pins:
            seg_t = pins[c][1]
        seg_start = c + 1
    return out


def narrate(sentences, voice, speed=1.0, gap=0.28, lead=0.15, tail=0.6):
    """sentences: list of dicts with 'text' (shown) and optional 'say' (spoken),
    'gap' (pause after). Returns (audio float32 @24k, sr, timeline).
    timeline[i] = dict(start, end, scene_end, words=[(word, t0, t1)])."""
    k = kokoro()
    sr = 24000
    chunks = [np.zeros(int(lead * sr), dtype=np.float32)]
    t = lead
    timeline = []
    for i, s in enumerate(sentences):
        spoken = s.get("say", s["text"])
        x, sr = k.create(spoken, voice=voice, speed=speed, lang="en-us")
        x = _trim(np.asarray(x, dtype=np.float32), sr)
        dur = len(x) / sr
        words = s["text"].split()
        wt = _align(k, words, x, sr, t)
        g = s.get("gap", gap) if i < len(sentences) - 1 else tail
        timeline.append(dict(start=t, end=t + dur, scene_end=t + dur + g, words=wt))
        chunks.append(x)
        chunks.append(np.zeros(int(g * sr), dtype=np.float32))
        t += dur + g
    audio = np.concatenate(chunks)
    # scene boundaries: first scene starts at 0
    prev = 0.0
    for tl in timeline:
        tl["scene_start"] = prev
        prev = tl["scene_end"]
    return audio, sr, timeline


def pad_music(duration, chord, sr=44100, level=0.05):
    """Soft synthetic pad (detuned sines, slow swell). chord = list of Hz."""
    n = int(duration * sr)
    t = np.arange(n) / sr
    out = np.zeros(n, dtype=np.float64)
    for j, f in enumerate(chord):
        for det in (-0.35, 0.0, 0.4):
            lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.05 + 0.013 * j) * t + j * 1.7 + det)
            out += lfo * np.sin(2 * np.pi * (f + det) * t + j)
            out += 0.25 * lfo * np.sin(2 * np.pi * (2 * f + det) * t + j * 0.5)
    out /= np.max(np.abs(out))
    env = np.minimum(1, t / 2.5) * np.minimum(1, (duration - t) / 2.0)
    return (out * env * level).astype(np.float32)


def write_mix(path, voice, sr_v, music, sr_m=44100):
    n = int(len(voice) * sr_m / sr_v)
    v = np.interp(np.linspace(0, len(voice) - 1, n), np.arange(len(voice)), voice)
    m = np.zeros(n, dtype=np.float32)
    m[:min(n, len(music))] = music[:n]
    v = v / max(1e-6, np.max(np.abs(v))) * 0.82
    mix = np.clip(v + m, -1, 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr_m)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- captions
def chunk_words(words, max_words=3, max_chars=17):
    """words: [(word, t0, t1)] -> list of chunks [(word,t0,t1),...]"""
    chunks, cur = [], []
    for w in words:
        trial = cur + [w]
        chars = sum(len(x[0]) for x in trial) + len(trial) - 1
        if cur and (len(trial) > max_words or chars > max_chars):
            chunks.append(cur)
            cur = [w]
        else:
            cur = trial
        if re.search(r"[,.?!—;:]$", w[0]) and cur:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def draw_caption(canvas, timeline, t, y=1440, size=84, upper=True,
                 hi="#FFC53D", base="#FFFFFF", path=POPPINS_BOLD):
    """Karaoke-style caption: current 2-3 word chunk, spoken word highlighted."""
    for tl in timeline:
        if not (tl["scene_start"] <= t < tl["scene_end"]):
            continue
        chunks = tl["_chunks"]
        cur = None
        for i, ch in enumerate(chunks):
            c0 = ch[0][1]
            c1 = chunks[i + 1][0][1] if i + 1 < len(chunks) else tl["end"] + 0.25
            if c0 - 0.03 <= t < c1 - 0.03:
                cur = (ch, c0)
                break
        if cur is None:
            return
        ch, c0 = cur
        clean = lambda w: (w.upper() if upper else w).replace("—", "").strip()
        texts = [clean(w[0]) for w in ch]
        f = font(path, size)
        space = f.measureText(" ")
        widths = [f.measureText(x) for x in texts]
        total = sum(widths) + space * (len(texts) - 1)
        # wrap into two lines if too wide
        lines = [list(range(len(texts)))]
        if total > 900 and len(texts) > 1:
            best, bi = 1e9, 1
            for cut in range(1, len(texts)):
                a = sum(widths[:cut]) + space * (cut - 1)
                b = sum(widths[cut:]) + space * (len(texts) - cut - 1)
                if max(a, b) < best:
                    best, bi = max(a, b), cut
            lines = [list(range(bi)), list(range(bi, len(texts)))]
        pop = 0.9 + 0.1 * ease_out((t - c0) / 0.12)
        lh = size * 1.12
        y0 = y - (len(lines) - 1) * lh / 2
        canvas.save()
        canvas.translate(W / 2, y)
        canvas.scale(pop, pop)
        canvas.translate(-W / 2, -y)
        for li, idxs in enumerate(lines):
            lw = sum(widths[i] for i in idxs) + space * (len(idxs) - 1)
            x = (W - lw) / 2
            yy = y0 + li * lh + size * 0.35
            for i in idxs:
                active = ch[i][1] - 0.03 <= t
                is_now = ch[i][1] - 0.03 <= t < ch[i][2] + 0.02
                stroke = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                    StrokeWidth=size * 0.2, Color=color("#0B0B0F", 0.95))
                stroke.setStrokeJoin(skia.Paint.kRound_Join)
                canvas.drawString(texts[i], x, yy, f, stroke)
                col = hi if is_now else base
                fill = skia.Paint(AntiAlias=True, Color=color(col, 1.0 if active else 0.55))
                canvas.drawString(texts[i], x, yy, f, fill)
                x += widths[i] + space
        canvas.restore()
        return


def prep_captions(timeline, **kw):
    for tl in timeline:
        tl["_chunks"] = chunk_words(tl["words"], **kw)


# ---------------------------------------------------------------- encode
class SceneWriter:
    """Pipes RGBA frames to ffmpeg; writes to a temp .mp4 and renames on success."""

    def __init__(self, path):
        self.path = path
        self.tmp = path.replace(".mp4", ".part.mp4")
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
             "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), self.tmp],
            stdin=subprocess.PIPE)

    def write(self, surface):
        arr = surface.toarray(colorType=skia.kRGBA_8888_ColorType)
        self.p.stdin.write(arr.tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError("ffmpeg failed for " + self.path)
        os.replace(self.tmp, self.path)


def concat_and_mux(scene_files, wav, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for s in scene_files:
            f.write(f"file '{s}'\n")
    silent = out.replace(".mp4", ".silent.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                           "-i", lst, "-c", "copy", silent])
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
                           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                           "-b:a", "160k", "-shortest", "-movflags", "+faststart", out])
    os.remove(silent)
    os.remove(lst)


def new_surface():
    return skia.Surface(W, H)


def save_png(surface, path):
    surface.makeImageSnapshot().save(path, skia.kPNG)
