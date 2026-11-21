"""Post one finished video per account per day.

Runs from .github/workflows/post.yml at 8 pm Malaysia time.

  python engine/post.py            post for real (needs the token secrets)
  python engine/post.py --dry-run  only say what would be posted

What it does, for each account in catalog/posting.json:
  1. find the oldest video on the Releases page that this account has not posted
     (only videos from the channels the account carries, taking turns between them)
  2. download it, and its caption (the .txt next to it)
  3. post it as a Reel to Instagram and to the Facebook Page
  4. write what happened to catalog/posted.json, so nothing is posted twice

The only secret an account needs is a Facebook Page access token (see the guide).
The Page id and the linked Instagram account are looked up from the token.
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "catalog" / "posting.json"
LEDGER = ROOT / "catalog" / "posted.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "JohnDoeSKipper/clipper")
GRAPH = "https://graph.facebook.com/v25.0"
MYT = timezone(timedelta(hours=8))
DRY = "--dry-run" in sys.argv


def log(*a):
    print(*a, flush=True)


def http(method, url, data=None, headers=None, body=None, tries=3):
    """Small JSON HTTP helper. data = form fields; body = raw bytes."""
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    for attempt in range(tries):
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                raw = r.read()
                return json.loads(raw) if raw[:1] in (b"{", b"[") else raw
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="replace")
            if e.code >= 500 and attempt < tries - 1:
                time.sleep(10 * (attempt + 1)); continue
            raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {text[:600]}")
        except urllib.error.URLError as e:
            if attempt < tries - 1:
                time.sleep(10 * (attempt + 1)); continue
            raise


def gh_api(path):
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    return http("GET", f"https://api.github.com/repos/{REPO}/{path}", headers=headers)


# ---------- what is ready to post ----------

def channel_of(vid):
    for d in ("done", "review", "queue"):
        p = ROOT / "specs" / d / f"{vid}.json"
        if p.exists():
            return json.loads(p.read_text()).get("channel")
    return None


def ready_videos():
    """[(release date, id, channel, mp4 url, txt url)], oldest first."""
    out = []
    page = 1
    while True:
        rels = gh_api(f"releases?per_page=50&page={page}")
        if not rels:
            break
        for r in rels:
            if not r["tag_name"].startswith("videos-") or r.get("draft"):
                continue
            assets = {a["name"]: a["browser_download_url"] for a in r["assets"]}
            for name, url in assets.items():
                if name.endswith(".mp4"):
                    vid = name[:-4]
                    out.append((r["tag_name"][7:], vid, channel_of(vid), url, assets.get(vid + ".txt")))
        if len(rels) < 50:
            break
        page += 1
    # newest release wins if the same video was re-made
    latest = {}
    for item in sorted(out):
        latest[item[1]] = item
    return sorted(latest.values())


def pick(account, ledger):
    done = ledger.get(account["name"], {})
    channels = account["channels"]
    todo = [v for v in ready_videos() if v[2] in channels and v[1] not in done]
    if not todo:
        return None
    # take turns: the channel that posted least recently goes first
    last = {c: "" for c in channels}
    for vid, rec in done.items():
        c = rec.get("channel")
        if c in last:
            last[c] = max(last[c], rec.get("at", ""))
    for c in sorted(channels, key=lambda c: (last[c], channels.index(c))):
        for v in todo:
            if v[2] == c:
                return v
    return todo[0]


# ---------- the platforms ----------

def page_info(token):
    me = http("GET", f"{GRAPH}/me?fields=id,name,instagram_business_account{{id,username}}&access_token={token}")
    ig = me.get("instagram_business_account") or {}
    return me["id"], me.get("name"), ig.get("id"), ig.get("username")


def post_instagram(ig_id, token, video, caption):
    size = video.stat().st_size
    c = http("POST", f"{GRAPH}/{ig_id}/media",
             data={"media_type": "REELS", "upload_type": "resumable", "caption": caption,
                   "share_to_feed": "true", "access_token": token})
    cid = c["id"]
    uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v25.0/{cid}"
    http("POST", uri, body=video.read_bytes(),
         headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    for _ in range(60):                      # up to 10 minutes of processing
        time.sleep(10)
        st = http("GET", f"{GRAPH}/{cid}?fields=status_code,status&access_token={token}")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram could not process the video: {st}")
    else:
        raise RuntimeError("Instagram took more than 10 minutes to process the video")
    pub = http("POST", f"{GRAPH}/{ig_id}/media_publish", data={"creation_id": cid, "access_token": token})
    link = http("GET", f"{GRAPH}/{pub['id']}?fields=permalink&access_token={token}").get("permalink")
    return {"id": pub["id"], "link": link}


def post_facebook(page_id, token, video, caption):
    size = video.stat().st_size
    s = http("POST", f"{GRAPH}/{page_id}/video_reels", data={"upload_phase": "start", "access_token": token})
    vid = s["video_id"]
    url = s.get("upload_url") or f"https://rupload.facebook.com/video-upload/v25.0/{vid}"
    http("POST", url, body=video.read_bytes(),
         headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    http("POST", f"{GRAPH}/{page_id}/video_reels",
         data={"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
               "description": caption, "access_token": token})
    return {"id": vid, "link": f"https://www.facebook.com/reel/{vid}"}


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


# ---------- main ----------

def wait_for_post_time(hhmm):
    """GitHub starts scheduled runs early or late; wait (at most 40 min) for the set time."""
    h, m = map(int, hhmm.split(":"))
    now = datetime.now(MYT)
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    wait = (target - now).total_seconds()
    if 0 < wait <= 40 * 60:
        log(f"Waiting {wait/60:.0f} min for {hhmm} Malaysia time")
        time.sleep(wait)


def main():
    cfg = json.loads(CONFIG.read_text())
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    if not DRY and os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        wait_for_post_time(cfg.get("time", "20:00"))
    report, failed = [], False
    for acc in cfg["accounts"]:
        name = acc["name"]
        token = os.environ.get(acc["token_secret"], "").strip()
        v = pick(acc, ledger)
        if not v:
            report.append(f"- {name}: nothing new to post. Approve a script to make the next video.")
            continue
        date, vid, ch, mp4_url, txt_url = v
        if DRY or not token:
            why = "dry run" if DRY else f"secret {acc['token_secret']} is not set yet"
            report.append(f"- {name}: would post **{vid}** ({ch}, made {date}) — {why}")
            continue
        work = ROOT / "out" / "post"
        work.mkdir(parents=True, exist_ok=True)
        video = work / f"{vid}.mp4"
        urllib.request.urlretrieve(mp4_url, video)
        caption = urllib.request.urlopen(txt_url).read().decode().strip() if txt_url else ""
        secs = duration(video)
        rec = {"channel": ch, "at": datetime.now(MYT).isoformat(timespec="minutes"), "release": date}
        try:
            page_id, page_name, ig_id, ig_name = page_info(token)
        except Exception as e:
            report.append(f"- {name}: the token did not work ({e}). Make a new one (guide, section 7).")
            failed = True
            continue
        targets = [t for t in acc.get("platforms", ["instagram", "facebook"])]
        for t in targets:
            try:
                if t == "instagram":
                    if not ig_id:
                        raise RuntimeError(f"no Instagram account is linked to the Page {page_name}")
                    rec["instagram"] = post_instagram(ig_id, token, video, caption)
                elif t == "facebook":
                    if secs > 90:
                        raise RuntimeError(f"Facebook only takes Reels up to 90 s through its API; this one is {secs:.0f} s")
                    rec["facebook"] = post_facebook(page_id, token, video, caption)
                log(f"{name}: posted {vid} to {t}")
            except Exception as e:
                rec[t] = {"error": str(e)[:500]}
                failed = True
                log(f"{name}: {t} failed: {e}")
        ok = [t for t in targets if "id" in rec.get(t, {})]
        if ok:   # a video counts as posted once any platform took it; errors stay in the record
            ledger.setdefault(name, {})[vid] = rec
        links = ", ".join(f"[{t}]({rec[t]['link']})" if rec[t].get("link") else t for t in ok) or "nothing"
        errs = "; ".join(f"{t}: {rec[t]['error']}" for t in targets if "error" in rec.get(t, {}))
        report.append(f"- {name}: **{vid}** ({secs:.0f} s) posted to {links}" + (f". Problems: {errs}" if errs else ""))
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n")
    text = "\n".join(report)
    log(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("## Posting " + datetime.now(MYT).strftime("%Y-%m-%d %H:%M") + " MYT\n\n" + text + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
