"""Philosophy channel: films the 3D stage (engine/stage/stage.js) in headless Chrome and adds the sound.
render(spec, TL, voice, sr, out_path, tmp, frames_only=None)"""
import json, os, socket, subprocess, sys, time
import numpy as np
import core as C
import audio as A

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stage")
PADS = {"neutral": [98.0, 146.83, 196.0, 246.94], "warm": [130.81, 196.0, 261.63, 329.63], "dark": [110.0, 164.81, 220.0, 261.63],
        "tense": [103.83, 146.83, 207.65, 246.94], "wonder": [116.54, 174.61, 233.08, 293.66]}
FILES = ["pluck", "select", "switch", "bong", "question", "tick", "confirmation", "error", "drop", "click", "maximize", "scratch"]
# overlay type -> (sound, gain, offset) played automatically when the overlay appears
AUTO = {"question": [("question", 0.32, 0)], "check": [("confirmation", 0.38, 0)], "cross": [("error", 0.42, 0)], "xmark": [("error", 0.4, 0)],
        "number": [("pluck", 0.2, 0)], "pill": [("click", 0.3, 0)], "stop": [("brake", 0.16, -0.05), ("thud", 0.3, 0.45)]}


def sound(name, dur=None, seed=3):
    if name in FILES:
        return A.load_wav(name + "_001.wav")
    if name == "whistle":
        return A.whistle()
    if name == "clatter":
        return A.rail_clatter(dur or 2.5, seed=seed)
    if name == "whoosh":
        return A.whoosh(dur or 0.45, seed=seed)
    if name == "thud":
        return A.thud()
    if name == "clank":
        return A.clank()
    if name == "brake":
        return A.brake(dur or 0.6)
    raise ValueError(f"unknown sound '{name}'. Known: {FILES + ['whistle', 'clatter', 'whoosh', 'thud', 'clank', 'brake']}")


def soundtrack(spec, voice, sr, total, path):
    mix = A.Mix(total)
    cues = []
    if spec.get("autoSfx", True):
        seen = set()
        for o in spec.get("overlays", []):
            t = o.get("from", o.get("at", 0))
            for name, gain, off in AUTO.get(o["type"], []):
                if (name, round(t, 1)) not in seen:
                    seen.add((name, round(t, 1)))
                    cues.append(dict(at=t + off, s=name, gain=gain))
        for i, sh in enumerate(spec["shots"][1:]):
            if sh.get("focus", "all") == "all" or sh.get("whoosh"):
                cues.append(dict(at=sh["at"], s="whoosh", gain=0.2, seed=9 + i))
    cues += spec.get("sfx", [])
    for c in cues:
        x = sound(c["s"], c.get("dur"), c.get("seed", 3))
        t, gain = c["at"], c.get("gain", 0.25)
        if "every" in c:
            while t < c["until"] - 0.1:
                mix.add(t, x, gain)
                t += c["every"]
        else:
            mix.add(t, x, gain)
    m = spec.get("music", {})
    chord = m.get("pad") if isinstance(m.get("pad"), list) else PADS[m.get("mood", "neutral")]
    mix.write(path, voice, sr, C.pad_music(total, chord, level=m.get("level", 0.03)), music_gain=1.0, duck=0.3)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def render(spec, TL, voice, sr, out, tmp, frames_only=None):
    sid = spec["id"]
    style = os.environ.get("CLIPPER_STYLE") or spec.get("style", "clay")
    total = TL[-1]["scene_end"]
    C.prep_captions(TL, max_words=4, max_chars=20)
    js = {k: spec[k] for k in ("title", "world", "objects", "groups", "shots", "actions", "overlays", "seed", "hook_text", "hook_until") if k in spec}
    for a in js.get("actions", []):
        if "until" in a:
            a["dur"] = max(0.0, a["until"] - a["at"])
    js["shots"] = sorted(js["shots"], key=lambda s: s["at"])
    js["TL"] = {"total": total, "sentences": [dict(start=s["scene_start"], end_scene=s["scene_end"], end=s["end"], chunks=s["_chunks"]) for s in TL]}
    work = os.path.join(HERE, "work", sid)
    os.makedirs(work, exist_ok=True)
    json.dump(js, open(os.path.join(work, "spec.json"), "w"), default=float)
    if not os.path.exists(os.path.join(HERE, "node_modules", "three")):
        subprocess.check_call(["npm", "install", "--no-audit", "--no-fund", "--silent"], cwd=HERE)
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    node = ["node", os.path.join(HERE, "render.mjs"), str(port), sid, style]
    try:
        if frames_only is not None:
            ts = sorted(set(frames_only) | {round((a["at"] + b["at"]) / 2, 2) for a, b in zip(js["shots"], js["shots"][1:] + [{"at": total}])})
            keep = []
            for t in ts:
                if not keep or t - keep[-1] > 0.45:
                    keep.append(t)
            subprocess.check_call(node + ["frames", tmp] + [f"{t:.2f}" for t in keep])
            return [os.path.join(tmp, f"{sid}_{t:06.2f}.jpg") for t in keep]
        n = round(total * C.FPS)
        k = max(1, min(int(os.environ.get("CLIPPER_WORKERS", os.cpu_count() or 2)), 4, n // 120))
        cuts = [round(n * i / k) for i in range(k + 1)]
        parts = [os.path.join(tmp, f"{sid}_{style}_{i}.mp4") for i in range(k)]
        t0 = time.time()
        procs = [subprocess.Popen(node + ["video", parts[i], str(cuts[i]), str(cuts[i + 1])]) for i in range(k)]
        if any(p.wait() != 0 for p in procs):
            raise RuntimeError("3D render failed")
        print(f"   {n} frames in {time.time() - t0:.0f}s ({k} workers, {style})", flush=True)
        wav = os.path.join(tmp, sid + ".wav")
        soundtrack(spec, voice, sr, total, wav)
        C.concat_and_mux(parts, wav, out)
        for p in parts:
            os.remove(p)
    finally:
        server.terminate()
    return None
