"""Build one or more videos from JSON specs:  python engine/build.py specs/queue/*.json
Options: --draft   quick check for the writer: no voice, no downloads; estimated timing; prints warnings and writes out/<id>_sheet.jpg
         --frames  real voice and assets, but only the check sheet (no video)
         --at=1.5,7  extra moments (seconds) to add to the check sheet"""
import copy, hashlib, json, os, pickle, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import core as C
import fetch

ROOT = C.ROOT
CUE_KEYS = {"at", "to", "from", "until", "ring", "zoom", "labelAt", "out", "bars"}
CUE = re.compile(r"^(\d+|end)(?::([^+#]+?))?(?:#(\d+))?([+-]\d+(?:\.\d+)?)?$")
BEATS = ["hook", "question", "reveal1", "reveal2", "reveal3", "turn", "payoff"]
LINKS = {"but", "so", "because", "detail", "answer"}
PACE = {"paintings": dict(within=0.4, between=0.8, big=1.0), "philosophy": dict(within=0.28, between=0.55, big=0.75)}
TAIL = 1.6          # seconds held after the last word, so the ending lands and the music resolves
DEFAULT_VOICE = {"paintings": dict(name="bf_emma", speed=0.8, gap=0.65), "philosophy": dict(name="am_michael", speed=1.04, gap=0.38)}


def pace(spec):
    """With a "beat" on every sentence, breathing is automatic: one take per 1-2 sentences of the same beat,
    a short pause inside a beat, a longer one between beats, the longest before the turn and the payoff.
    A "gap" written on a sentence still wins."""
    s = spec["script"]
    if not all(x.get("beat") in BEATS for x in s):
        return
    P = PACE[spec["channel"]]
    passages, cur = [], []
    for i, x in enumerate(s):
        if cur and (x["beat"] != s[cur[-1]]["beat"] or len(cur) == 2):
            passages.append(cur)
            cur = []
        cur.append(i)
    passages.append(cur)
    spec["passages"] = passages
    for a, b in zip(passages, passages[1:]):
        last, nb = s[a[-1]], s[b[0]]["beat"]
        if "gap" not in last:
            last["gap"] = P["within"] if nb == last["beat"] else (P["big"] if nb in ("turn", "payoff") else P["between"])


def hook_until(spec, TL):
    """The on-screen hook line stays up while the spoken hook is said (2.5-6 s)."""
    s = spec["script"]
    idx = [i for i, x in enumerate(s) if x.get("beat") == "hook"] or [0]
    return round(min(6.0, max(2.5, TL[idx[-1]]["end"] + 0.5)), 2)


def check_story(spec, TL, out):
    """The spine (PLAYBOOK, Writing the script): beats in order, every sentence linked to the one before."""
    s, total = spec["script"], TL[-1]["scene_end"]
    if not all("beat" in x for x in s):
        out.append('every sentence needs "beat" and "link" (PLAYBOOK: the spine)')
        return
    bad = [i for i, x in enumerate(s) if x["beat"] not in BEATS]
    if bad:
        out.append(f"sentence {bad[0]}: beat must be one of " + ", ".join(BEATS))
        return
    order = [BEATS.index(x["beat"]) for x in s]
    if order != sorted(order):
        i = next(i for i in range(1, len(order)) if order[i] < order[i - 1])
        out.append(f'sentence {i}: beat "{s[i]["beat"]}" comes after "{s[i - 1]["beat"]}"; the beats must run in order: ' + " > ".join(BEATS))
    counts = {b: sum(1 for x in s if x["beat"] == b) for b in BEATS}
    limits = {"hook": (1, 2), "question": (1, 2), "reveal1": (2, 4), "reveal2": (2, 4), "reveal3": (2, 4), "turn": (1, 2), "payoff": (1, 2)}
    for b, (lo, hi) in limits.items():
        if not lo <= counts[b] <= hi:
            out.append(f'beat "{b}" has {counts[b]} sentence(s); it needs {lo}-{hi}')
    if len(s[0]["text"].split()) > 12:
        out.append(f"the first sentence has {len(s[0]['text'].split())} words; the hook must land in about 2 seconds (12 words at most)")
    first = {b: next((i for i, x in enumerate(s) if x["beat"] == b), None) for b in BEATS}
    if first["question"] is not None and TL[first["question"]]["start"] > 12:
        out.append(f"the question starts at {TL[first['question']]['start']:.0f}s; ask it by 12s so the viewer knows what they are waiting for")
    if first["reveal2"] is not None and not 0.25 <= TL[first["reveal2"]]["start"] / total <= 0.55:
        out.append(f"reveal2 starts at {TL[first['reveal2']]['start']:.0f}s; it is the mid-video re-hook and belongs between 25% and 55% of the video")
    if first["payoff"] is not None and TL[first["payoff"]]["start"] / total < 0.75:
        out.append(f"the payoff starts at {TL[first['payoff']]['start']:.0f}s, too early; keep the answer for the last quarter")
    buts = 0
    for i, x in enumerate(s[1:], 1):
        l = x.get("link")
        if l not in LINKS:
            out.append(f'sentence {i}: "link" must say how it follows the sentence before: ' + ", ".join(sorted(LINKS)) + ' (never "and" / a new topic)')
            continue
        buts += l == "but"
        if x["beat"] != s[i - 1]["beat"] and l == "detail" and x["beat"] != "question":
            out.append(f'sentence {i} starts {x["beat"]} with "detail"; a new beat must be caused by the last one (so / because) or cut against it (but)')
    if buts < 2:
        out.append(f'only {buts} "but" link(s); a story needs at least two moments where the expected answer breaks')
    ht = spec.get("hook_text", "")
    if not 3 <= len(ht.split()) <= 7:
        out.append('"hook_text" (the big on-screen line in the first seconds) needs 3-7 words; it sharpens the spoken hook, it does not repeat it')
    lg = " " + spec.get("logline", "").lower() + " "
    if " but " not in lg or not (" so " in lg or " therefore " in lg):
        out.append('"logline" must tell the whole story in one line with "but" and "so"/"therefore" (write it before the script)')
    beats = []
    for b in BEATS:
        idx = [i for i, x in enumerate(s) if x["beat"] == b]
        if idx:
            beats.append(f"{b} {TL[idx[0]]['start']:.0f}-{TL[idx[-1]]['end']:.0f}s")
    print("   beats: " + " | ".join(beats))


def narrate(spec, tmp):
    import voice as V
    v = {**DEFAULT_VOICE[spec["channel"]], **spec.get("voice", {})}
    script = spec["script"]
    passages = spec.get("passages") or [[i] for i in range(len(script))]
    key = hashlib.sha1(json.dumps([script, passages, v], sort_keys=True).encode()).hexdigest()[:16]
    cache = os.path.join(ROOT, "cache", "voice", key + ".pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    audio, sr, TL, matched = V.narrate(script, passages, v["name"], speed=v["speed"], gap=v["gap"], tail=TAIL)
    print(f"  narration {len(audio) / sr:.1f}s, caption alignment {matched * 100:.0f}%")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump((audio, sr, TL), open(cache, "wb"))
    return audio, sr, TL


def estimate(spec):
    """A timeline without running the voice: good enough to check staging, framing and cue words."""
    v = {**DEFAULT_VOICE[spec["channel"]], **spec.get("voice", {})}
    script = spec["script"]
    passages = spec.get("passages") or [[i] for i in range(len(script))]
    last_of = {idxs[-1] for idxs in passages}
    TL, t = [], 0.12
    for i, sen in enumerate(script):
        words = []
        for w in sen["text"].split():
            d = (0.085 + 0.056 * len(re.sub(r"[^\w']", "", w))) * 1.04 / v["speed"]
            words.append((w, round(t, 3), round(t + d, 3)))
            t += d + (0.25 if re.search(r"[,;:.?!]$", w) else 0)
        end = words[-1][2]
        t = end + (sen.get("gap", v["gap"]) if i in last_of else 0.3)
        TL.append(dict(words=words, start=words[0][1], end=end))
    total = TL[-1]["end"] + TAIL
    for i, tl in enumerate(TL):
        tl["scene_start"] = 0.0 if i == 0 else TL[i - 1]["scene_end"]
        tl["scene_end"] = total if i == len(TL) - 1 else max(tl["end"], TL[i + 1]["start"] - 0.1)
    return TL


def draft_assets(spec):
    """Stand-ins so a Paintings draft can be drawn from the small previews in inbox/ (nothing is downloaded)."""
    from PIL import Image
    if spec["channel"] != "paintings":
        return
    p, d = spec["painting"], os.path.join("inbox", spec["id"])
    if not os.path.exists(os.path.join(ROOT, p.get("file", "__none__"))):
        p["file"] = os.path.join(d, "painting_preview.jpg")
        if not os.path.exists(os.path.join(ROOT, p["file"])):
            raise FileNotFoundError(f'{p["file"]} is missing: push requests/{spec["id"]}.json first and wait for the inbox')
    meta = json.load(open(os.path.join(ROOT, d, "meta.json"))) if os.path.exists(os.path.join(ROOT, d, "meta.json")) else {"inserts": {}}
    for ev in spec["timeline"]:
        if ev.get("type") == "insert" and ev.get("kind") == "image" and not os.path.exists(os.path.join(ROOT, ev.get("file", "__none__"))):
            key, n = ev["pick"]
            found = meta["inserts"].get(key, [])
            if n >= len(found):
                raise ValueError(f'insert pick ["{key}", {n}] does not exist in inbox/{spec["id"]}/meta.json (have: ' + ", ".join(f"{k}:{len(v)}" for k, v in meta["inserts"].items()) + ")")
            w, h = found[n]["width"], found[n]["height"]
            ph = os.path.join(ROOT, "cache", "tmp", f'{spec["id"]}_{key}_ph.jpg')
            Image.new("RGB", (800, max(200, round(800 * h / w))), "#6C7689").save(ph)
            ev["file"] = os.path.relpath(ph, ROOT)
            if found[n].get("credit"):
                ev.setdefault("credit", "Photo: " + found[n]["credit"])


def check(spec, TL):
    """Cheap sanity checks, printed as WARNING lines."""
    out, ch = [], spec["channel"]
    total, words = TL[-1]["scene_end"], sum(len(s["words"]) for s in TL)
    check_story(spec, TL, out)
    lo, hi = 75, 88          # Facebook's posting API refuses Reels over 90 s
    if total > 89.5:
        out.append(f"the video runs {total:.0f}s: over 90 s Facebook will not take it; cut to {lo}-{hi}s")
    elif not lo <= total <= hi:
        out.append(f"the video runs {total:.0f}s; aim for {lo}-{hi}s")
    for i, s in enumerate(spec["script"]):
        if len(s["text"].split()) > 22:
            out.append(f"sentence {i} is long ({len(s['text'].split())} words); split it so captions and shots can keep up")
    if ch == "philosophy":
        gaps = [b["at"] - a["at"] for a, b in zip(spec["shots"], spec["shots"][1:])] + [total - spec["shots"][-1]["at"]]
        if max(gaps) > 6.5:
            out.append(f"a shot lasts {max(gaps):.1f}s; cut to a new angle at least every 5s or so")
        if spec.get("style") not in ("clay", "ps2"):
            out.append('style must be "clay" or "ps2"')
    if ch == "paintings":
        n_ins = sum(1 for e in spec["timeline"] if e.get("type") == "insert")
        if n_ins < 2:
            out.append(f"{n_ins} insert(s): every Paintings video needs at least 2 things that are not the painting (photos first, map or illustration last)")
        evs = [(e.get("at", e.get("ring", 0)), e.get("to", e.get("out", e.get("until", 0))), e["type"]) for e in spec["timeline"]]
        for (a0, a1, an), (b0, b1, bn) in zip(evs, evs[1:]):
            if b0 < a1 - 0.01:
                out.append(f"timeline: a {bn} starts at {b0:.1f}s before the previous {an} has ended ({a1:.1f}s)")
    print(f"   {total:.0f}s, {words} words, {len(spec['script'])} sentences")
    for w in out:
        print("WARNING:", w)


def cue_time(cue, TL):
    m = CUE.match(cue.strip())
    if not m:
        raise ValueError(f"bad cue '{cue}'")
    head, word, nth, off = m.groups()
    if head == "end":
        t = TL[-1]["scene_end"]
    else:
        s = TL[int(head)]
        if word is None:
            t = s["scene_start"]
        else:
            norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
            hits = [t0 for w, t0, _ in s["words"] if norm(w) == norm(word)]
            if not hits:
                raise ValueError(f"cue '{cue}': word '{word}' is not in sentence {head}: " + " ".join(w for w, _, _ in s["words"]))
            t = hits[int(nth) - 1 if nth else 0]
    return round(t + (float(off) if off else 0.0), 3)


def resolve(node, TL):
    if isinstance(node, dict):
        return {k: (cue_time(v, TL) if k in CUE_KEYS and isinstance(v, str) else resolve(v, TL)) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve(v, TL) for v in node]
    return node


def contact_sheet(paths, out, cols=6):
    from PIL import Image
    ims = [Image.open(p).convert("RGB").resize((270, 480)) for p in paths]
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (270 * min(cols, len(ims)), 480 * rows), "#000")
    for i, im in enumerate(ims):
        sheet.paste(im, (270 * (i % cols), 480 * (i // cols)))
    sheet.save(out, quality=85)


def video_sheet(video, times, tmp, sid):
    """Check frames taken from the finished video (published next to it, for review)."""
    paths = []
    for t in times:
        p = os.path.join(tmp, f"{sid}_v{t:06.2f}.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", "scale=270:480", p])
        if os.path.exists(p):
            paths.append(p)
    return paths


def build(path, frames_only=False, draft=False):
    spec = json.load(open(path))
    sid, ch = spec["id"], spec["channel"]
    print("==", sid, ch, flush=True)
    out_dir, tmp = os.path.join(ROOT, "out"), os.path.join(ROOT, "cache", "tmp")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(tmp, exist_ok=True)
    pace(spec)
    if draft:
        draft_assets(spec)
        credits, audio, sr, TL, frames_only = [], None, 24000, estimate(spec), True
    else:
        credits = fetch.resolve_spec_assets(spec)
        audio, sr, TL = narrate(spec, tmp)
        TL = copy.deepcopy(TL)
    for k in ("timeline", "shots", "actions", "overlays", "sfx"):
        if k in spec:
            spec[k] = resolve(spec[k], TL)
    spec["hook_until"] = hook_until(spec, TL)
    check(spec, TL)
    mids = [round((s["scene_start"] + s["end"]) / 2, 2) for s in TL]
    at = [a for a in sys.argv if a.startswith("--at=")]
    if at:
        mids = [float(x) for x in at[0][5:].split(",")]
    out = os.path.join(out_dir, sid + ".mp4")
    if ch == "paintings":
        import paint
        cat = {e["id"]: e for e in json.load(open(os.path.join(ROOT, "catalog/music.json")))}
        if spec["music"]["piece"] not in cat:
            raise ValueError(f'music piece "{spec["music"]["piece"]}" is not in catalog/music.json. Choose one of: ' + ", ".join(cat))
        entry = cat[spec["music"]["piece"]]
        spec["music"] = {**entry.get("play", {}), **spec["music"], "midi": "" if draft else os.path.relpath(fetch.ensure_score(entry), ROOT)}
        credits += [f'Music: {entry["composer"]}, {entry["title"]}. Score: Mutopia Project ({entry["licence"]}), rendered by the channel.',
                    "Piano samples: Salamander Grand Piano by Alexander Holm (CC BY 3.0)."]
        if frames_only:
            sheet = paint.render(spec, TL, audio, sr, ROOT, out, tmp, frames_only=mids)
        else:
            paint.render(spec, TL, audio, sr, ROOT, out, tmp)
            sheet = None
    else:
        import stage
        sheet = stage.render(spec, TL, audio, sr, out, tmp, frames_only=mids if frames_only else None)
        credits += ["Sound effects: Kenney.nl interface sounds (CC0) and original synthesis."]
    if not sheet and not frames_only:
        sheet = video_sheet(out, mids, tmp, sid)
    if sheet:
        contact_sheet(sheet, os.path.join(out_dir, sid + "_sheet.jpg"))
    post = spec.get("post", {})
    if draft:
        print("   draft sheet:", os.path.relpath(os.path.join(out_dir, sid + "_sheet.jpg"), ROOT), flush=True)
        if os.path.basename(os.path.dirname(os.path.abspath(path))) == "review":
            # a smaller copy goes next to the draft, so the review issue can show it
            from PIL import Image
            im = Image.open(os.path.join(out_dir, sid + "_sheet.jpg")).convert("RGB")
            im.thumbnail((1400, 1400))
            im.save(os.path.join(os.path.dirname(os.path.abspath(path)), sid + "_sheet.jpg"), quality=78)
        return
    with open(os.path.join(out_dir, sid + ".txt"), "w") as f:
        f.write(post.get("caption", spec.get("title", sid)) + "\n\n" + " ".join(post.get("tags", [])) + "\n\nCredits\n" + "\n".join(credits) + "\n")
    print("   done", os.path.relpath(out if not frames_only else os.path.join(out_dir, sid + "_sheet.jpg"), ROOT), flush=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    failed = []
    for p in args:
        try:
            build(p, frames_only="--frames" in sys.argv, draft="--draft" in sys.argv)
        except Exception as e:
            import traceback
            traceback.print_exc()
            failed.append((p, str(e)))
    if failed:
        print("FAILED:", failed)
        sys.exit(1)
