"""Everything that touches the network: models, piano samples, scores, paintings and photos.
Runs on GitHub's servers (open internet). Nothing here needs an API key."""
import json, os, re, subprocess, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
UA = {"User-Agent": "clipper-pipeline/1.0 (https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "JohnDoeSKipper/clipper") + "; educational short videos) python-urllib"}
# Wikimedia only serves these thumbnail widths freely; any other width is heavily rate-limited
def sized(url, w):
    return re.sub(r"/\d+px-", f"/{w}px-", url)
OK_LICENCES = ("public domain", "pd", "cc0", "cc by", "cc-by", "no restrictions")


def get(url, dest=None, timeout=120):
    import time, urllib.error
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:            # Wikimedia throttles busy servers: wait and try again
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            time.sleep(8 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(8 * (attempt + 1))
    if dest:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest + ".part", "wb") as f:
            f.write(data)
        os.replace(dest + ".part", dest)
        return dest
    return data


def need(path, url):
    if not (os.path.exists(path) and os.path.getsize(path) > 1000):
        print("download", os.path.relpath(path, ROOT), flush=True)
        get(url, path, timeout=900)
    return path


# ---------------------------------------------------------------- fixed assets
def ensure_models():
    m = os.path.join(CACHE, "models")
    rel = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    need(os.path.join(m, "kokoro-v1.0.onnx"), rel + "kokoro-v1.0.onnx")
    need(os.path.join(m, "voices-v1.0.bin"), rel + "voices-v1.0.bin")
    pk = os.path.join(m, "parakeet")
    if not os.path.exists(os.path.join(pk, "tokens.txt")):
        tar = need(os.path.join(m, "parakeet.tar.bz2"),
                   "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2")
        subprocess.check_call(["tar", "xjf", tar, "-C", m])
        os.rename(os.path.join(m, "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"), pk)
        os.remove(tar)


def ensure_piano():
    d = os.path.join(CACHE, "piano48")
    base = "https://raw.githubusercontent.com/sfzinstruments/SalamanderGrandPiano/master/Samples/"
    names = ["A0"] + [f"{n}{o}" for o in range(1, 8) for n in ("C", "D#", "F#", "A")] + ["C8"]
    for n in names:
        for v in (2, 5, 8, 11):
            f = f"{n}v{v}.flac"
            need(os.path.join(d, f), base + urllib.parse.quote(f))


def ensure_countries():
    need(os.path.join(CACHE, "countries.geojson"),
         "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson")


def ensure_score(entry):
    """Compile a Mutopia LilyPond score to MIDI once. entry comes from catalog/music.json."""
    d = os.path.join(CACHE, "scores")
    midi = os.path.join(d, entry["id"] + ".midi")
    if os.path.exists(midi):
        return midi
    import lilypond
    bindir = os.path.dirname(str(lilypond.executable()))
    ly = need(os.path.join(d, entry["id"] + ".ly"),
              "https://raw.githubusercontent.com/MutopiaProject/MutopiaProject/master/" + urllib.parse.quote(entry["ly"]))
    for inc in entry.get("includes", []):
        need(os.path.join(d, os.path.basename(inc)),
             "https://raw.githubusercontent.com/MutopiaProject/MutopiaProject/master/" + urllib.parse.quote(inc))
    subprocess.run([os.path.join(bindir, "convert-ly"), "-e", ly], cwd=d, capture_output=True)
    subprocess.run([os.path.join(bindir, "lilypond"), "-dno-print-pages", "-o", entry["id"], os.path.basename(ly)],
                   cwd=d, capture_output=True, timeout=600)
    for ext in (".midi", ".mid"):
        if os.path.exists(os.path.join(d, entry["id"] + ext)):
            os.replace(os.path.join(d, entry["id"] + ext), midi)
            return midi
    raise RuntimeError("score did not compile: " + entry["id"])


# ---------------------------------------------------------------- Wikimedia Commons
API = "https://commons.wikimedia.org/w/api.php"


def _strip(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def commons_search(query, limit=6, min_width=1000):
    """Files on Wikimedia Commons matching a search or an exact 'File:...' title, with licence details.
    Only freely reusable results are returned."""
    if query.lower().startswith("file:"):
        params = dict(action="query", titles=query, prop="imageinfo")
    else:
        params = dict(action="query", generator="search", gsrsearch=query + " filetype:bitmap", gsrnamespace=6, gsrlimit=limit * 3, prop="imageinfo")
    params.update(format="json", iiprop="url|size|mime|extmetadata", iiurlwidth=3840)
    data = json.loads(get(API + "?" + urllib.parse.urlencode(params)))
    pages = sorted((data.get("query", {}).get("pages", {}) or {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = _strip(meta.get("LicenseShortName", {}).get("value", ""))
        if not ii.get("url") or ii.get("width", 0) < min_width or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if not any(k in lic.lower() for k in OK_LICENCES):
            continue
        artist = _strip(meta.get("Artist", {}).get("value", ""))[:80]
        free = any(k in lic.lower() for k in ("public domain", "pd", "cc0", "no restrictions"))
        out.append(dict(title=p["title"], url=ii.get("thumburl") or ii["url"], full=ii["url"], width=ii["width"], height=ii["height"],
                        licence=lic, artist=artist, credit="" if free else f"{artist} / {lic}",
                        desc=_strip(meta.get("ImageDescription", {}).get("value", ""))[:160]))
        if len(out) >= limit:
            break
    return out


def run_request(path):
    """Phase 1 of a Paintings video. A request names a painting and things to look for; this downloads
    candidates and writes small previews into inbox/<id>/ for the writer to look at."""
    from PIL import Image, ImageDraw
    req = json.load(open(path))
    for item in req["items"]:
        d = os.path.join(ROOT, "inbox", item["id"])
        os.makedirs(d, exist_ok=True)
        meta = dict(id=item["id"], painting=None, inserts={})
        cands = commons_search(item["painting"], limit=3, min_width=1500)
        if cands:
            best = next((c for c in cands if c["width"] >= 2000), cands[0])
            tmp = get(sized(best["url"], 960), os.path.join(CACHE, "tmp", item["id"] + "_p.jpg"))
            im = Image.open(tmp).convert("RGB")
            im.thumbnail((1024, 1024))
            im.save(os.path.join(d, "painting_preview.jpg"), quality=82)
            meta["painting"] = best
        sheet, cell = [], 380
        for key, query in item.get("look_for", {}).items():
            try:
                found = commons_search(query, limit=3)
            except Exception as e:
                print("search failed:", query, e)
                found = []
            meta["inserts"][key] = found
            for n, c in enumerate(found):
                try:
                    tmp = get(sized(c["url"], 500), os.path.join(CACHE, "tmp", f"{item['id']}_{key}_{n}.jpg"))
                    im = Image.open(tmp).convert("RGB")
                    im.thumbnail((cell, cell - 40))
                    sheet.append((f"{key} #{n}", im))
                except Exception as e:
                    print("preview failed", c["title"], e)
        if sheet:
            cols = 3
            rows = (len(sheet) + cols - 1) // cols
            canvas = Image.new("RGB", (cols * cell, rows * cell), "#111")
            dr = ImageDraw.Draw(canvas)
            for i, (label, im) in enumerate(sheet):
                x, y = (i % cols) * cell, (i // cols) * cell
                canvas.paste(im, (x + (cell - im.width) // 2, y + 30))
                dr.text((x + 8, y + 8), label, fill="#fff")
            canvas.save(os.path.join(d, "inserts_preview.jpg"), quality=78)
        json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
        print("inbox ready:", item["id"], "painting" if meta["painting"] else "NO PAINTING FOUND", {k: len(v) for k, v in meta["inserts"].items()})


def resolve_spec_assets(spec):
    """Phase 2: download the full-size files a spec points at (by inbox choice) just before rendering."""
    if spec.get("channel") != "paintings":
        return []
    credits = []
    d = os.path.join(ROOT, "inbox", spec["id"])
    meta = json.load(open(os.path.join(d, "meta.json"))) if os.path.exists(os.path.join(d, "meta.json")) else None
    p = spec["painting"]
    if not os.path.exists(os.path.join(ROOT, p.get("file", "__none__"))):
        src = meta["painting"]
        p["file"] = os.path.relpath(get(src["url"], os.path.join(CACHE, "img", spec["id"] + "_painting.jpg")), ROOT)
        if src.get("credit"):
            credits.append(f'Painting image: {src["credit"]}')
    for ev in spec["timeline"]:
        if ev.get("type") == "insert" and ev.get("kind") == "image" and not os.path.exists(os.path.join(ROOT, ev.get("file", "__none__"))):
            key, n = ev["pick"]
            src = meta["inserts"][key][n]
            ev["file"] = os.path.relpath(get(sized(src["url"], 1920), os.path.join(CACHE, "img", f"{spec['id']}_{key}.jpg")), ROOT)
            if src.get("credit"):
                ev.setdefault("credit", "Photo: " + src["credit"])
                credits.append(f'{ev.get("caption", key)}: {src["credit"]} (Wikimedia Commons)')
    return credits


if __name__ == "__main__":
    if sys.argv[1] == "request":
        for path in sys.argv[2:]:
            run_request(path)
    elif sys.argv[1] == "base":
        ensure_models(); ensure_piano(); ensure_countries()
