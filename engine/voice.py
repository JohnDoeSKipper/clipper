"""Narration v2: whole passages in one take (so the rhythm carries across
sentences), captions aligned to the real audio with a speech recognizer."""
import difflib, os, re
import numpy as np
import core as C

PK = os.path.join(C.ROOT, "cache/models/parakeet")
_rec = None


def recognizer():
    global _rec
    if _rec is None:
        import sherpa_onnx
        _rec = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=f"{PK}/encoder.int8.onnx", decoder=f"{PK}/decoder.int8.onnx",
            joiner=f"{PK}/joiner.int8.onnx", tokens=f"{PK}/tokens.txt",
            num_threads=2, model_type="nemo_transducer")
    return _rec


def _norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def heard_words(audio, sr):
    """[(word, start_seconds)] as recognised from the audio."""
    n = int(len(audio) * 16000 / sr)
    x = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)
    r = recognizer()
    s = r.create_stream()
    s.accept_waveform(16000, x)
    r.decode_stream(s)
    toks, ts = s.result.tokens, s.result.timestamps
    words, cur, t0 = [], "", 0.0
    for tok, t in zip(toks, ts):
        if tok.startswith(" ") or tok.startswith("▁") or not cur:
            if cur.strip():
                words.append((cur.strip(), t0))
            cur, t0 = tok.replace("▁", " "), t
        else:
            cur += tok
    if cur.strip():
        words.append((cur.strip(), t0))
    return words


def narrate(sentences, passages, voice, speed=1.0, gap=0.38, lead=0.12, tail=0.7):
    """passages: list of lists of sentence indices spoken in one take.
    Each sentence dict may set 'gap' = pause after its passage."""
    k = C.kokoro()
    sr = 24000
    parts, t = [np.zeros(int(lead * sr), np.float32)], lead
    for pi, idxs in enumerate(passages):
        text = " ".join(sentences[i].get("say", sentences[i]["text"]) for i in idxs)
        x, sr = k.create(text, voice=voice, speed=speed, lang="en-us")
        x = C._trim(np.asarray(x, np.float32), sr, thr=0.008, pad=0.06)
        fi, fo = int(0.008 * sr), int(0.04 * sr)
        x[:fi] *= np.linspace(0, 1, fi)
        x[-fo:] *= np.linspace(1, 0, fo)
        g = sentences[idxs[-1]].get("gap", gap) if pi < len(passages) - 1 else tail
        parts += [x, np.zeros(int(g * sr), np.float32)]
        t += len(x) / sr + g
    audio = np.concatenate(parts)
    total = len(audio) / sr

    heard = heard_words(audio, sr)
    script = [(si, w) for si, s in enumerate(sentences) for w in s["text"].split()]
    a = [_norm(w) for _, w in script]
    b = [_norm(w) for w, _ in heard]
    starts = [None] * len(script)
    for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for j in range(m.size):
            starts[m.a + j] = heard[m.b + j][1]
    # fill unmatched words by interpolating between matched neighbours
    known = [i for i, v in enumerate(starts) if v is not None]
    matched = len(known) / len(script)
    for i in range(len(script)):
        if starts[i] is None:
            prev = max([q for q in known if q < i], default=None)
            nxt = min([q for q in known if q > i], default=None)
            if prev is None:
                starts[i] = max(0.0, starts[nxt] - 0.25 * (nxt - i))
            elif nxt is None:
                starts[i] = starts[prev] + 0.3 * (i - prev)
            else:
                starts[i] = starts[prev] + (starts[nxt] - starts[prev]) * (i - prev) / (nxt - prev)
    timeline = []
    for si, s in enumerate(sentences):
        ids = [i for i, (q, _) in enumerate(script) if q == si]
        words = []
        for i in ids:
            nxt = starts[i + 1] if i + 1 < len(script) else total - tail + 0.1
            words.append((script[i][1], starts[i], min(nxt, starts[i] + 0.7)))
        timeline.append(dict(words=words, start=words[0][1], end=words[-1][2]))
    for si, tl in enumerate(timeline):
        tl["scene_start"] = 0.0 if si == 0 else timeline[si - 1]["scene_end"]
        tl["scene_end"] = total if si == len(timeline) - 1 else max(tl["end"], timeline[si + 1]["start"] - 0.1)
    return audio, sr, timeline, matched
