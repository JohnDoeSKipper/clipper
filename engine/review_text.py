"""Text of a script-review issue, made from a draft spec.
python engine/review_text.py specs/review/<id>.json          -> issue body (markdown)
python engine/review_text.py specs/review/<id>.json --title  -> issue title"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WPM = {"paintings": 125, "philosophy": 145}      # measured on the approved videos, pauses included


def sentence_of(cue):
    m = re.match(r"^(\d+)", str(cue))
    return int(m.group(1)) + 1 if m else None


def main():
    path = sys.argv[1]
    spec = json.load(open(path))
    sid, ch = spec["id"], spec["channel"]
    if ch == "paintings":
        p = spec["painting"]
        name = f'{p["title"]}, {p["artist"]} ({p.get("year", "")})'
        kind = "Paintings"
    else:
        small = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to"}
        words = spec.get("title", sid).lower().split()
        name = " ".join(w if (i and w in small) else w[:1].upper() + w[1:] for i, w in enumerate(words))
        kind = f'Philosophy, {spec.get("style", "?")} style'
    if "--title" in sys.argv:
        print(f"[{sid}] {name} · {kind}")
        return

    words = sum(len(s["text"].split()) for s in spec["script"])
    secs = round(words / WPM.get(ch, 135) * 60)
    out = [f"**{name}** · {kind} · about {secs} seconds ({words} words)", ""]
    if spec.get("angle"):
        out += [f"**The question this video answers:** {spec['angle']}", ""]

    out += ["### Script", ""]
    out += [f"{i}. {s['text']}" for i, s in enumerate(spec["script"], 1)]
    if spec.get("hooks"):
        out += ["", "**Other opening lines I considered** (the script's own first line is opening 1; reply e.g. \"use opening 2\"):", ""]
        out += [f"{i}. {h}" for i, h in enumerate(spec["hooks"], 2)]

    out += ["", "### On screen", ""]
    if ch == "paintings":
        for e in spec.get("timeline", []):
            n = sentence_of(e.get("at", e.get("ring", "")))
            at = f"sentence {n}" if n else "start"
            if e["type"] == "insert":
                what = e.get("caption") or e.get("place") or e.get("kind")
                out.append(f"- {at}: {'photo' if e.get('kind') == 'image' else e.get('kind')} of {what}")
            elif e["type"] == "highlight":
                out.append(f"- {at}: ring and zoom on {(e.get('label') or 'a detail').lower()}"
                           + (f", then {(e['then'].get('label') or 'a closer detail').lower()}" if e.get("then") else ""))
        piece = spec.get("music", {}).get("piece")
        cat = {c["id"]: c for c in json.load(open(os.path.join(ROOT, "catalog", "music.json")))}
        if piece in cat:
            c = cat[piece]
            out.append(f"- Music: {c['composer']}, {c['title']}" + ("" if c.get("approved") else " (a piece you have not heard in a video yet)"))
    else:
        kinds = sorted({o.get("kind") for o in spec.get("objects", []) if o.get("kind") not in ("person", "track", "arrows", "arc")})
        people = sum(1 for o in spec.get("objects", []) if o.get("kind") == "person")
        out.append(f"- {len(spec.get('shots', []))} camera shots, {people} people" + (f", props: {', '.join(kinds)}" if kinds else ""))
        out.append(f"- Scenery: {spec.get('world', {}).get('scenery', 'default')}; music mood: {spec.get('music', {}).get('mood', 'neutral')}")

    sheet = os.path.join(os.path.dirname(path), f"{sid}_sheet.jpg")
    if os.path.exists(sheet):
        repo = os.environ.get("GITHUB_REPOSITORY", "JohnDoeSKipper/clipper")
        sha = os.environ.get("GITHUB_SHA", "main")
        out += ["", f"![Draft frames, one per sentence](https://raw.githubusercontent.com/{repo}/{sha}/specs/review/{sid}_sheet.jpg)",
                "", "_Draft frames: the timing is estimated and the pictures are low-resolution previews._"]

    if spec.get("sources"):
        out += ["", "### Sources checked", ""] + [f"- {u}" for u in spec["sources"]]
    post = spec.get("post", {})
    if post:
        out += ["", "### Post caption", "", post.get("caption", ""), "", " ".join(post.get("tags", []))]
        if post.get("youtube_title"):
            out += ["", f"**YouTube title:** {post['youtube_title']} #Shorts"]

    out += ["", "---", "",
            "**To make this video:** reply `approve` (one word).",
            "**To change it:** reply with what to change, in your own words. The writer rewrites it the next morning and posts the new version here. "
            f"For a faster rewrite, tell Claude in the CLIPPER project: *revise {sid}*."]
    print("\n".join(out))


if __name__ == "__main__":
    main()
