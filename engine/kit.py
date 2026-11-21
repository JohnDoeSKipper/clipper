"""Tonight's posting kit: one phone-friendly page with each channel's video and captions.

Runs from .github/workflows/kit.yml every evening before 8 pm Malaysia time.
For each account in catalog/posting.json it takes the oldest finished video not
handed out yet, copies it into site/, writes site/index.html, and records it in
catalog/posted.json. GitHub Pages then serves site/ at
https://<owner>.github.io/clipper/

  python engine/kit.py            build the kit (and record the videos as handed out)
  python engine/kit.py --dry-run  build it without recording anything
"""
import html, json, os, sys, urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from post import ROOT, CONFIG, LEDGER, MYT, pick  # noqa: E402

SITE = ROOT / "site"
DRY = "--dry-run" in sys.argv
LABEL = {"paintings": "Behind the Painting", "philosophy": "Philosophy"}


def spec_of(vid):
    for d in ("done", "review", "queue"):
        p = ROOT / "specs" / d / f"{vid}.json"
        if p.exists():
            return json.loads(p.read_text())
    return {}


def youtube_title(spec, caption):
    first = caption.split("\n")[0].split(". ")[0].strip().rstrip(".")
    t = spec.get("post", {}).get("youtube_title") or first or (spec.get("title") or "").title()
    t = t if len(t) <= 90 else t[:87].rsplit(" ", 1)[0] + "…"
    return t + " #Shorts"


def card(acc, item, today):
    name = LABEL.get(acc["name"], acc["name"].title())
    if not item:
        return f"""<section><h2>{name}</h2><p class=none>Nothing new tonight. Approve a script on GitHub to make the next video.</p></section>"""
    date, vid, ch, mp4_url, txt_url = item
    caption = urllib.request.urlopen(txt_url).read().decode().strip() if txt_url else ""
    ytt = youtube_title(spec_of(vid), caption)
    if not DRY or not (SITE / f"{vid}.mp4").exists():
        urllib.request.urlretrieve(mp4_url, SITE / f"{vid}.mp4")
    e = html.escape
    k = f"{today}-{vid}"
    boxes = "".join(f'<label><input type=checkbox data-k="{k}-{p}"> {p}</label>' for p in ("Instagram + Facebook", "TikTok", "YouTube"))
    return f"""<section>
<h2>{name}</h2>
<video src="{vid}.mp4#t=0.5" controls playsinline preload="metadata"></video>
<button class=big onclick="saveVideo('{vid}.mp4')">1 · Save video to phone</button>
<button class=big onclick="copy('cap-{vid}', this)">2 · Copy caption</button>
<textarea id="cap-{vid}" readonly rows=6>{e(caption)}</textarea>
<button onclick="copy('yt-{vid}', this)">YouTube title · copy</button>
<input id="yt-{vid}" readonly value="{e(ytt)}">
<div class=checks>{boxes}</div>
<p class=small>{e(vid)} · made {e(date)}</p>
</section>"""


PAGE = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Tonight's posts · CLIPPER</title>
<style>
body{margin:0;font:16px/1.45 -apple-system,system-ui,sans-serif;background:#111;color:#eee}
main{max-width:520px;margin:auto;padding:16px}
h1{font-size:22px;margin:8px 0 2px}h2{font-size:19px;margin:0 0 10px}
.sub{color:#999;margin:0 0 16px}
section{background:#1c1c1e;border-radius:14px;padding:14px;margin:0 0 18px}
video{width:100%;max-height:60vh;border-radius:10px;background:#000;margin-bottom:10px}
button{display:block;width:100%;padding:12px;margin:8px 0;border:0;border-radius:10px;background:#2c2c2e;color:#eee;font-size:16px}
button.big{background:#0a84ff;color:#fff;font-weight:600;padding:15px}
textarea,input{width:100%;box-sizing:border-box;background:#000;color:#ccc;border:1px solid #333;border-radius:8px;padding:8px;font-size:13px}
.checks{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}.checks label{font-size:15px;display:flex;align-items:center;gap:6px}.checks input{width:22px;height:22px;margin:0}
.none{color:#aaa}.small{color:#777;font-size:12px;margin:10px 0 0}
</style></head><body><main>
<h1>Tonight's posts</h1><p class=sub>__DATE__ · post at 8:00 pm</p>
__CARDS__
<p class=small>Older videos: <a style="color:#0a84ff" href="https://github.com/__REPO__/releases">Releases page</a></p>
</main><script>
function copy(id,b){var el=document.getElementById(id);var t=el.value;
 (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).catch(function(){el.select();document.execCommand('copy')});
 var o=b.textContent;b.textContent='Copied ✓';setTimeout(function(){b.textContent=o},1500)}
async function saveVideo(u){try{var r=await fetch(u);var b=await r.blob();
 var f=new File([b],u,{type:'video/mp4'});
 if(navigator.canShare&&navigator.canShare({files:[f]})){await navigator.share({files:[f]});return}}catch(e){if(e.name==='AbortError')return}
 var a=document.createElement('a');a.href=u;a.download=u;document.body.appendChild(a);a.click();a.remove()}
document.querySelectorAll('input[type=checkbox]').forEach(function(c){
 try{c.checked=localStorage.getItem(c.dataset.k)==='1'}catch(e){}
 c.onchange=function(){try{localStorage.setItem(c.dataset.k,c.checked?'1':'0')}catch(e){}}});
</script></body></html>"""


def main():
    cfg = json.loads(CONFIG.read_text())
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    SITE.mkdir(exist_ok=True)
    now = datetime.now(MYT)
    today = now.strftime("%Y-%m-%d")
    cards, summary = [], []
    for acc in cfg["accounts"]:
        # a video already handed out today stays tonight's video if the kit is rebuilt
        done = ledger.get(acc["name"], {})
        again = [v for v, r in done.items() if r.get("handed_out") == today]
        item = None
        if again:
            from post import ready_videos
            item = next((v for v in ready_videos() if v[1] == again[0]), None)
        if not item:
            item = pick(acc, ledger)
            if item and not DRY:
                ledger.setdefault(acc["name"], {})[item[1]] = {
                    "channel": item[2], "handed_out": today, "at": now.isoformat(timespec="minutes")}
        cards.append(card(acc, item, today))
        summary.append(f"{acc['name']}: {item[1] if item else 'nothing new'}")
    page = (PAGE.replace("__DATE__", now.strftime("%A %d %B %Y"))
                .replace("__CARDS__", "\n".join(cards))
                .replace("__REPO__", os.environ.get("GITHUB_REPOSITORY", "JohnDoeSKipper/clipper")))
    (SITE / "index.html").write_text(page)
    if not DRY:
        LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n")
    print("; ".join(summary))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("summary=" + "; ".join(summary) + "\n")


if __name__ == "__main__":
    main()
