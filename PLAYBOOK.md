# CLIPPER playbook

For the daily writer (Claude). Read this file fully at the start of every run; read nothing else unless a step says so.
The owner is Jared. He reviews videos and gives corrections; every correction is added to "What Jared has asked for" at the bottom.

## What you do each day

Output per day: **1 Paintings spec + 1 Philosophy spec** in `specs/queue/`, and enough Paintings requests to stay two paintings ahead.
You never render videos. Pushing to `main` makes GitHub render and publish them (Releases page).

1. `git pull`, then `sh scripts/setup_draft.sh` (once per session).
2. **Failures first.** If `status/` holds a `.txt`, a workflow failed: read it, fix the cause if it is in a spec or request (otherwise report it to Jared), and delete the file. If `specs/failed/` has files: read the `.log` next to each, fix the spec, `git mv` it back to `specs/queue/`, delete the log.
3. **Paintings.** In `topics/paintings.md`:
   - A line marked `inbox` has pictures waiting in `inbox/<id>/`. Take the oldest: write its spec (see Paintings), mark the line `queued`.
   - Count lines marked `inbox` or `requested`. If fewer than 2, write `requests/<id>.json` for the next `todo` lines and mark them `requested`. (A `requested` line whose `inbox/<id>/meta.json` now exists becomes `inbox`.)
4. **Philosophy.** Take the next `todo` line in `topics/philosophy.md`, write its spec (see Philosophy), mark it `queued`.
5. For each new spec: `python engine/build.py specs/queue/<id>.json --draft`. Fix every `WARNING`. Then look at `out/<id>_sheet.jpg` **once**; fix what is wrong; redraw and look once more only if you changed staging.
6. `git add -A && git commit -m "<date>: <ids>" && git push`. Finish with a three-line report: what was queued, what was requested, anything Jared should know (e.g. first use of a music piece or a new prop).

Keeping the run cheap: do not open engine code, do not print specs back, do not view an image twice, do not web-search except to confirm the facts a script states (one search per video, results noted in `"sources"`).

## Rules for every script

- Every claim must be true and checkable. Confirm dates, names, places and "firsts" with one search; put the URLs in `"sources": [...]`. If a popular story is doubtful, say "it's said that" or leave it out.
- Spoken English, short sentences, no filler, no "in this video". One idea per sentence. First sentence is the hook: a surprise or a tension, under 14 words.
- Write numbers the voice may misread with `"say"`: `{"text": "In 1889, ...", "say": "In eighteen eighty-nine, ..."}`. Same for foreign names it would mangle (spell them phonetically in `say`).
- `passages` groups sentences spoken in one breath (2-3 sentences each). `"gap"` (seconds) on the last sentence of a passage sets the pause after it; use 0.5-0.75 before a reveal.
- Captions are automatic. Never add emoji. `post.caption` is one or two plain sentences plus 4-6 hashtags in `post.tags`.

## Cues (how things are timed)

Any `at / to / from / until / ring / zoom / labelAt / out / bars` value may be a number of seconds or a cue string:
`"3"` = start of sentence 3 (first is 0) · `"3:word"` = when that word is spoken in sentence 3 · `"3:word#2"` = its 2nd occurrence · `"3:word+0.4"` / `"3-0.3"` = offset in seconds · `"end"`.
The word must appear in that sentence's `text` exactly (punctuation and case ignored).

---

## Paintings channel ("Behind the Painting")

Look approved by Jared: the framed painting on a blurred backdrop, slow continuous camera, white serif captions, a classical piano piece under a calm British female voice. 40-55 s, 85-110 words, 6-8 sentences.

Story shape: hook → where and when (show the place: **photo first**, map or illustration only when no usable photo exists) → 2-3 details in the painting, each one found by the camera → a closing line that lands.

**Never show only the painting.** Every video needs at least 2 inserts (things that are not the painting): the place, the artist, the model, a sketch, the object depicted, the room it hangs in.

**Never cut into a detail.** A highlight always goes: whole painting → ring drawn around the detail → camera glides in. The engine does this; you only give the region and the cue words.

### Step 1: request pictures (a day ahead)

`requests/<id>.json`:
```json
{"items": [{"id": "girl-pearl-earring",
  "painting": "File:1665 Girl with a Pearl Earring.jpg",
  "look_for": {"delft": "View of Delft Vermeer painting", "museum": "Mauritshuis The Hague exterior", "artist": "Johannes Vermeer The Procuress self-portrait detail"}}]}
```
`painting` is an exact Wikimedia Commons file title if you are sure of it, otherwise search words ("Girl with a Pearl Earring Vermeer Mauritshuis"). `look_for` holds 3-5 searches; each returns up to 3 candidates. Ask for real photos and period images; prefer the artist's own works and museum photographs. Only public-domain and CC-licensed files are returned, and credits are added automatically.

### Step 2: write the spec (when the inbox has arrived)

Look once at `inbox/<id>/painting_preview.jpg` (to place highlights) and once at `inbox/<id>/inserts_preview.jpg` (tiles labelled `key #n`). `meta.json` lists titles and descriptions if you need to tell candidates apart. If the painting preview is the wrong picture, re-request with a better title and take the next inbox instead.

```json
{"id": "girl-pearl-earring", "channel": "paintings",
 "painting": {"title": "Girl with a Pearl Earring", "artist": "Johannes Vermeer", "year": "c. 1665", "museum": "Mauritshuis, The Hague"},
 "script": [{"text": "...", "gap": 0.7}, {"text": "..."}],
 "passages": [[0], [1, 2], [3], [4, 5], [6]],
 "music": {"piece": "bach-goldberg-aria"},
 "timeline": [
  {"type": "reveal", "from": [0.5, 0.4, 2.6], "until": 3.2},
  {"type": "insert", "kind": "image", "pick": ["delft", 0], "caption": "Delft, painted by Vermeer himself", "at": "1", "to": "2-0.3"},
  {"type": "insert", "kind": "map", "place": "Delft", "sub": "Dutch Republic, 1665", "lat": 52.01, "lon": 4.36, "at": "2", "to": "3-0.3"},
  {"type": "highlight", "region": [0.56, 0.62, 0.05, 0.05], "ring": "3:pearl", "zoom": "3:pearl+0.5", "label": "NO HOOK, NO LOOP", "labelAt": "3:hook", "out": "4-0.4"},
  {"type": "highlight", "region": [0.5, 0.25, 0.2, 0.12], "ring": "4:turban", "zoom": "4:turban+0.4", "out": "5-0.4",
   "then": {"region": [0.47, 0.45, 0.04, 0.03], "ring": "4:eyes", "zoom": "4:eyes+0.4", "label": "...", "labelAt": "4:light"}},
  {"type": "highlight", "region": [0.5, 0.5, 0.1, 0.4], "ring": "5:dark", "zoom": "5:dark+0.3", "out": "6-0.4",
   "tilt": {"start": [0.5, 0.8], "to": [0.5, 0.2], "from": "5:rises", "until": "5:top+0.5"}}
 ],
 "sources": ["https://..."],
 "post": {"caption": "...", "tags": ["#vermeer", "#arthistory"]}}
```
- `region` = `[centre x, centre y, half-width, half-height]` as fractions of the painting (0,0 = top-left). Measure on the preview. Keep the ring a little larger than the detail.
- `reveal.from` = `[x, y, zoom]`: the video opens close on that point and pulls back to the whole painting by `until` (3-3.5 s). Open on the most striking detail.
- `highlight`: `ring` (ring starts drawing; the whole painting must be on screen), `zoom` (camera starts moving in, 0.3-0.6 s after `ring`), `out` (camera has left; must be before the next event). Optional `label` (2-4 words, CAPITALS) at `labelAt`; `labelSide` 1/-1 to move it right/left; `then` = a second, smaller detail inside the first; `tilt` = a slow pan from `start` to `to` while zoomed (for tall things). `scale` is automatic; set it only to override.
- `insert` kinds: `image` (`pick`: `[key, n]` from the inbox, plus a short `caption`), `map` (`place`, `sub`, `lat`, `lon`; the last resort for "where"), `window` (barred asylum window; Van Gogh only). An insert covers the screen from `at` to `to`; leave 0.3 s before the next highlight's `ring`.
- Events must not overlap, and are listed in time order. Between events the whole painting is shown.
- **Music**: choose from `catalog/music.json` by matching the painting's mood and era to `mood` and `fits`. Pick the piece that is *right for this painting*, not the nearest familiar one; do not use the same piece on consecutive days. Pieces with `"approved": false` have not been heard by Jared yet: fine to use, but say so in your report the first time.

---

## Philosophy channel ("thought experiments")

Look approved by Jared: a small 3D stage with toy people, shown in one of two styles; plain white serif captions with a soft shadow; sound effects on actions; a calm male voice. 22-40 s, 60-90 words, 9-12 short sentences. The last sentence is a question to the viewer.

**Choose the style per idea** (`"style"`), and say why in your report in five words:
- `clay`: glossy pastel toys, soft daylight. For warm, human, everyday or moral ideas: dilemmas about people, fairness, kindness, choices.
- `ps2`: early-2000s console graphics at sunset, fog, scanlines. For eerie, uncanny or nostalgic ideas: identity, simulations, machines, memory, death, paranoia.
- If either fits, use the one not used yesterday.

Story shape: set the scene in one line → the rule or the catch → the choice → what most people say → the twist that breaks the easy answer → the question.

### Spec

```json
{"id": "experience-machine", "channel": "philosophy", "style": "ps2", "title": "THE EXPERIENCE MACHINE",
 "world": {"scenery": "room"},
 "script": [{"text": "Imagine a machine that gives you any life you want."}, {"text": "..."}],
 "passages": [[0, 1], [2, 3, 4], [5], [6, 7], [8, 9]],
 "objects": [
  {"id": "pod", "kind": "pod", "at": [0, 0, 0], "face": 20},
  {"id": "you", "kind": "person", "look": "you", "at": [2.6, 0, 1.0], "face": "pod"},
  {"id": "door", "kind": "door", "at": [7.5, 0, 4.2], "face": "pod"}],
 "groups": {"crowd": ["a", "b", "c"]},
 "shots": [
  {"at": 0, "cam": {"preset": "mid", "on": ["pod", "you"]}, "focus": ["pod", "you"]},
  {"at": "1", "cam": {"preset": "close", "on": "you"}, "focus": ["you"]},
  {"at": "8", "cam": {"preset": "wide", "on": ["pod", "door"]}}],
 "actions": [
  {"id": "you", "at": "0:machine", "dur": 0.4, "pose": "point"},
  {"id": "you", "at": "8+0.3", "until": "9+0.6", "pos": [6.2, 0, 3.5], "walk": true, "ease": "linear"},
  {"id": "door", "at": "9", "dur": 0.6, "part": "leaf", "rot": [0, -100, 0]}],
 "overlays": [
  {"type": "icon", "icon": "heart", "pos": [540, 430], "from": "1:Love", "to": "2"},
  {"type": "cross", "from": "6:no-0.1", "to": "7"},
  {"type": "pill", "text": "Would you plug in?", "from": "9:real+0.4"}],
 "sfx": [{"at": "3:plug", "s": "switch", "gain": 0.35}],
 "music": {"mood": "wonder"},
 "sources": ["https://..."],
 "post": {"caption": "...", "tags": ["#philosophy"]}}
```
Full working examples: `specs/examples/trolley-problem.json` (hand-set cameras, the video Jared approved) and `specs/examples/experience-machine.json` (presets). Open one only if you are unsure of something.

**The stage.** Units are metres; a person is 2.2 tall. `at` = `[x, y, z]`: x right, y up, z towards the default viewer. Keep the action within about 8 m of the origin. `face` = degrees (0 faces +z) or the id of something to look at.
- `world.scenery`: `default` (clay: park with hills and lollipop trees; ps2: city at sunset) · `room` (an office: peach and mint in clay, sunset windows in ps2; walls 13 m left/right and 11 m front/back of the origin) · `open` (bare ground and sky; set `world.ground` to a colour for sea, sand, snow) · `none`.
- **People**: `kind: "person"`, `look`: `you` (yellow; always the viewer's stand-in), `stranger`, `one`, `elder`, or `a`-`e` for a varied crowd. `"ghost": true` = see-through (imagined or possible outcomes). `"behave": "panic"` = waving for help.
  Poses: `stand pull push think pushed point reach cheer shrug wave sad shock sit carry`. `"tip": -90` lays someone on their back.
- **Props** (`"kind": "<name>"`, optional `"tint": "#hex"`, `"scale"`): `crate table chair button pedestal screen pod bed door wall veil box glassbox coin cash book rock scale brainjar ship plank fire cat robot mirror sign house tree ball block pillar`. Moving parts: `door.leaf`, `box.lid`, `scale.beam`, `lever.arm`.
  Also `trolley`, `lever`, `bridge` (`height`, `length`), `track` and `arrows` (`path`: `[[x, z], ...]`, `"smooth": true` for curves), `arc` (dotted arc `from`/`via`/`to`, revealed with `progress`).
  Need something else? Build it once from parts and add it to `engine/stage/props.json` (copy an entry; parts are `box / ball / cyl / cone / capsule` with `size`, `at`, `color`, optional `rot`, `mat`: `plastic clay matte glow glass`; `"$"` as a colour means "tintable"). One colour serves both styles. Mention new props in your report.
- **Shots**: a new shot every 2-5 s; never hold one longer than 6 s. `cam.preset` with `on` (ids or a group):
  `close` (one subject, low three-quarter view: the default hero shot) · `tight` (face, for a reaction or a question) · `mid` (two or three subjects at eye level) · `wide` (high overview; use it to show the whole layout, counts and routes) · `side` (far side view, for falls and distances).
  The engine picks an unobstructed angle. Nudge with `"dist": 0.8`, `"side": 1`, `"azimuth": <degrees>`, `"lift"`, or give an exact camera: `{"pos": [x, y, z], "look": [x, y, z], "fov": 46, "to": {"pos": [...]}}` (optional `"rel": "<id>"` to follow an object).
  `focus` lists what stays sharp; in clay everything else is softly blurred (use it on every close shot; omit it for wide shots).
- **Actions** (`id` may be a list): `pos` (+ `"walk": true` for people) · `y` · `face` · `scale` · `pose` · `tip` / `roll` · `show` true/false · `part` + `rot` `[x, y, z]` degrees · `part` + `osc` `[a, b]` with `period` and `to` (swing back and forth) · `panic` 0-1 · `progress` 0-1 (arc) · `wobble`. Each has `at`, and `dur` or `until` (default 0.4 s); `ease`: `inout` (default), `out`, `linear`.
- **Overlays**: `label` (`text`, `"color": "yellow"` for YOU) · `number` · `check` · `cross` · `xmark` (cross something out) · `stop` · `question` · `pill` (the closing question; put it on the last sentence) · `icon` (`heart star bolt coin clock eye lock crown skull mountain brain zzz`). Pin to an object with `"on": "<id>"` (`"up"` = height) or to a point `"on": [x, y, z]`, or place on screen with `"pos": [x, y]` (1080×1920; keep y between 300 and 1300). `from` / `to` are cues.
- **Sound**: checks, crosses, question marks, numbers, stop signs, the closing pill and wide shots make their sounds automatically. Add `sfx` for physical actions: `whistle clatter whoosh thud clank brake` and `pluck select switch bong question tick confirmation error drop click maximize scratch` (`gain` 0.2-0.4; `every` + `until` to repeat). Whenever something visibly happens (a lever, a door, a fall, a train), it should make a sound.
- **Music** is a quiet pad: `music.mood` = `neutral warm dark tense wonder`.

### What makes these work
- Show, don't caption: when the script says a number, a choice or an outcome, something on stage or an overlay must change within half a second.
- Label the viewer's character `YOU` the first time it appears.
- Counting matters in dilemmas: put `number` overlays on the groups when the script compares them.
- A draft sheet with a person's back to the camera, a subject cut off, or a prop in front of a face is a bug: change the preset, `dist` or `azimuth`.

---

## What Jared has asked for (do not break these)

Paintings
- Whole painting first, then circle the detail, then zoom. No sudden cuts into details.
- Do not show only the painting: bring in photos of the place, the view, the people, related works. Use an exact photo when one exists; an illustration or map only as a last resort.
- Classical music on every video, chosen to suit the painting; quiet, slow, good quality. It sits about 12 dB under the voice. (Engine default; do not raise `under_db`.)
- Subtitles: plain white, classy serif, no coloured background, soft shadow only.
- Narration is slow and unhurried (engine default voice and speed; do not change `voice`).

Philosophy
- Clay and PS2 styles are both approved; choose per idea.
- Subtitles: plain white serif with shadow, no background plate.
- Sound effects on actions (a train gets its whistle).
- Keep the in-house voice (engine default). Do not use other voice services.

General
- Free tools only. No paid services.
- Quality first, token use second: fix what the draft sheet shows, but do not polish beyond it.

## Corrections log
Add dated one-line entries here whenever Jared corrects a video, and fold lasting rules into the section above.
- 2026-11-17: pipeline created from the two approved sample videos (Starry Night; Trolley Problem in clay and PS2).
