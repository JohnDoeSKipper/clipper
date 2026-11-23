# CLIPPER playbook

For the daily writer (Claude). Read this file fully at the start of every run; read nothing else unless a step says so.
The owner is Jared. He reviews videos and gives corrections; every correction is added to "What Jared has asked for" at the bottom.

## What you do each day

**No approval step (Jared, 2026-11-22).** You write each script straight into `specs/queue/`; your push makes GitHub render it, and it is posted on a coming evening. Nobody reads it before it is made, so your own checks are the only gate: be strict. Jared watches every video after it is made; his feedback arrives in `feedback/inbox.md` and must improve the next videos.

Output per day: up to **1 Paintings video + 1 Philosophy video**, plus picture requests to stay two paintings ahead.

1. `git pull`, then `sh scripts/setup_draft.sh` (once per session).
2. **Failures.** If `status/` holds a `.txt`, a workflow failed: read it, fix the cause if it is in a spec or request (otherwise report it), and delete the file. If `specs/failed/` has files: read the `.log` next to each, fix the spec, `git mv` it back to `specs/queue/`, delete the log.
3. **Feedback first.** Read `feedback/inbox.md`. Turn every point into a lasting rule: add it to "What Jared has asked for" and a dated line in the corrections log, so all future scripts follow it. If he asks for a particular video to be remade, do it (see Remaking). Then empty the file below its header, and say in the report what you changed.
4. **Don't pile up.** For each channel count the videos ready to post: specs in `specs/queue/` plus specs in `specs/done/` of that channel whose id is not yet in `catalog/posted.json` under that channel. If there are 3 or more, make nothing for that channel today and say so.
5. **Paintings.** In `topics/paintings.md`:
   - A line marked `inbox` has pictures waiting in `inbox/<id>/`. Take the oldest: write its spec (see Writing the script, then Paintings), save it as `specs/queue/<id>.json`, mark the line `made` (older lines marked `drafted` count as made).
   - Count lines marked `inbox` or `requested`. If fewer than 2, write `requests/<id>.json` for the next `todo` lines and mark them `requested`. (A `requested` line whose `inbox/<id>/meta.json` now exists becomes `inbox`.)
6. **Philosophy.** Philosophy videos show real pictures too (see "Show what you say"), so they also request pictures a day ahead: in `topics/philosophy.md` keep the next two `todo` lines `requested` (a request with only `look_for`, no `painting`; a `requested` line whose `inbox/<id>/meta.json` exists becomes `inbox`). Take the oldest `inbox` line (or, if none has arrived yet, request it, wait for it as described under Remaking, then go on), write its spec as `specs/queue/<id>.json`, mark it `made`.
7. **Check before you push.** For each new spec: `python engine/build.py specs/queue/<id>.json --draft`. Fix every `WARNING`. Look at `out/<id>_sheet.jpg` **once**; fix what is wrong; redraw and look once more only if you changed staging. Re-read the script once against the self-check below. Then add the script to the top of `catalog/approved-scripts.md` (same format; keep the newest 12).
8. Write the report to `notes/<date>.md` (Malaysia date, `TZ=Asia/Kuala_Lumpur date +%F`), at most five short lines: what was made (with the Philosophy style and why, in five words), what feedback you applied, what was requested, and anything Jared should know (first use of a music piece, a new prop, a problem you could not fix).
9. `git add -A && git commit -m "<date>: <ids>" && git push`. The push starts the render. End the run with the same report.

**When Jared gives feedback in a chat** instead of on GitHub: apply it as in step 3 (rules for future videos), and remake a video only if he asks.

**Remaking a video** (when Jared asks): edit `specs/done/<id>.json` and `git mv` it to `specs/queue/`. If it needs pictures it doesn't have yet, first push `requests/<id>.json` (Paintings: include the `painting` again, plus every `look_for`), then wait for the pictures in the same run: `git pull` every 2 minutes until `inbox/<id>/meta.json` appears (usually 3-8 minutes; give up after 25 and report it). The new inbox replaces the old picture list, so pick every picture again from the new previews. If the id is marked `skipped` in `catalog/posted.json`, delete that entry so the remade video gets posted. A Paintings remake reuses the picture list kept in `specs/meta/<id>.json` (the previews are gone; to choose a different photo, pick another candidate by its title there, or push a new request).

**Where to spend tokens.** Spend them on research and writing; that is what Jared judges. Save them everywhere else (Jared asked for token use to be kept as low as possible):
- **Stop early.** After steps 2-4, if there is no failure, no feedback and both channels already have 3 videos ready, write a one-line report and end the run. Do not research or draw anything.
- **Research lean.** Search in standard mode. Read pages with a focused question ("list the surprising, checkable facts about X with numbers and dates") instead of whole pages. About 6-10 page reads per video; stop once you have 6+ facts rated 4-5 with sources.
- **Write once.** Write each spec in one go, then change it with small edits; never print a spec, a sheet or this file back. Do not open engine code or the examples unless a WARNING forces you to.
- **Look once.** View each draft sheet once (twice only if you changed staging).
- **Run independent steps together** (several searches or page reads in one turn) and keep the report to five lines.

## Writing the script (the part that matters most)

Jared's verdicts so far: the first videos were *not informative, interesting or complex enough*; the next ones were *educational but jumpy, cutting abruptly from point to point*. The standard below fixes both: deep research, one thread, a fixed spine, and every sentence linked to the one before.

**Length: 75-88 seconds for both channels** (decided 2026-11-21). Reach on TikTok and Instagram grows past 60 s when people keep watching, and Facebook's posting API refuses Reels over 90 s, so 88 s is the ceiling. Longer is only worth it if every extra sentence is a new surprise; never pad.

**Surprise is the product.** Jared wants surprising, little-known facts. Build each script on facts that make a smart friend say *"wait, really?"*: a hidden detail, a number nobody expects, a myth the evidence overturns, a cause that is not the obvious one, a strange afterlife of the work or idea. Facts everyone already knows (Van Gogh cut off his ear, the Mona Lisa is small) may appear only as the setup for something they don't know.

### 1. Research first (about 4-6 searches or page reads per video)
- Read at least **three real sources** and open the pages (search snippets are not enough):
  - **Paintings:** the museum's own page for the work (and its collection-API text where there is one: Art Institute of Chicago, Cleveland Museum of Art, the Met, Rijksmuseum, National Gallery); a curator's or scholar's essay (Smarthistory, museum essays and blogs, Google Arts & Culture stories, conservation and technical studies); Wikipedia only to find leads, never as the only source for a claim.
  - **Philosophy:** the Stanford Encyclopedia of Philosophy (or Internet Encyclopedia of Philosophy) entry; the original paper or book (who, when, and what problem the idea was invented to test); at least one empirical study or survey with numbers if one exists; one real-world case where the question matters today.
- Build a fact bank in your scratch work (not in the spec): 15-20 specific, checkable facts, each tied to a source. Prefer facts with a number, a name, a material, a place, a date or a cause.
- **Rate every fact for surprise** (1 = on the Wikipedia first paragraph, 3 = a curious adult might know, 5 = almost nobody knows and it changes the picture). Dig where the 5s live: conservation and X-ray studies, letters and diaries, sales and inventory records, the museum's own blog, the original paper's footnotes, follow-up experiments, court cases. Build the script around the 4s and 5s.
- Read the top two scripts for your channel in `catalog/approved-scripts.md` (the most recent scripts made). Match or beat them, and never repeat their facts or hooks.

### 2. One thread: the question, the answer, the logline
Jared's verdict on the first longer videos (2026-11-23): *more educational, but the story jumps all over the place and cuts abruptly.* Twelve facts in twelve sentences is a list, not a story. A viral explainer follows **one thread from a question to its answer**, and every sentence is pulled out of the one before it.
- `"angle"`: the one question the video answers ("How did a print that cost two bowls of noodles become worth $2.76 million?"). A topic is not an angle.
- Decide the **answer** before writing a word. The payoff says it.
- `"logline"`: the whole story in one line, built on *but* and *so/therefore* (the South Park rule: beats joined by "and then" are a list; beats joined by "but" or "therefore" are a story). Example: *"It was printed as a cheap souvenir, but a new foreign blue made it a hit, so it was printed until the blocks wore out, therefore the crisp early copies became treasures, but Hokusai thought it was beginner's work."*
- **Fact budget: 5-7 facts, each told properly** (what, then why or how, then what it caused), chosen because they move the thread, rated 4-5 for surprise. A brilliant fact that does not serve the question goes in the topics file as a spare for another video, never in this one.

### 3. The spine (every video, no exceptions)
Every sentence in the spec carries `"beat"` and (from the second sentence on) `"link"`. The beats run in this order; the timings are for an 80-second video:

| Beat | Sentences | When | What it does |
|---|---|---|---|
| `hook` | 1-2 | 0-5 s | Stops the scroll. Sentence 1 is at most 12 words: a specific, surprising, true claim with a number, name or object (formula: context in a few words, then the snap that breaks the expectation). Use your **second-best** fact here; keep the best for later. Never "Did you know", "Have you ever", "In this video", a greeting or a vague superlative. |
| `question` | 1-2 | by 12 s | Says out loud the question the video will answer (the open loop), in plain words, with the stakes if there are any. The viewer must now know what they are waiting for. |
| `reveal1` | 2-4 | ~10-28 s | First part of the answer: one surprising fact, then why or how, then the consequence that hands over to the next beat. |
| `reveal2` | 2-4 | 25-55 % | The mid-video re-hook. Opens with a line that cuts against what we just learned ("But a popular print had a problem: it wore out its own woodblocks."), specific, never a stock phrase like "but that's not all". |
| `reveal3` | 2-4 | ~45-65 s | The strongest fact of the video, the one that matters most to the answer. |
| `turn` | 1-2 | ~65-75 s | The fact that changes how you see everything before it. |
| `payoff` | 1-2 | last quarter | Answers the question from the hook in so many words. The last line lands on a picture, or calls back to the hook so a replay feels natural (a loop), or (Philosophy) asks a sharper question than the first one. Never a summary, never "and that's why it's a masterpiece". |

**Links (the flow test).** `"link"` says how a sentence follows the one before it, and the checker refuses anything else:
- `but`: it breaks what we expected. At least two per video.
- `so`: it is caused by the sentence before.
- `because`: it explains the sentence before.
- `detail`: it zooms into something the sentence before just named (same subject, closer look). Only inside a beat.
- `answer`: it answers, or starts to answer, a question just asked (the usual way into `reveal1` and `payoff`).

There is no link for "and also" or "now, a different thing": if a sentence can only be joined with "and", cut it or move it. A new beat always starts with `but`, `so`, `because` or `answer`. In the words themselves, pick up something from the sentence before (its object, number or person) so the ear follows the thread; write the connecting word when it helps ("So", "But", "That's why", "Which means").

**On-screen hook.** `"hook_text"`: 3-7 words shown big at the top while the hook is spoken (about 2.5-6 s). It sharpens the spoken line; it does not repeat it. For "This print cost about two bowls of noodles" the text is "SOLD FOR $2.76 MILLION"; for a thought experiment, the dilemma in a phrase.

**Pacing is automatic.** With beats set, the generator breathes for you: one take per one or two sentences, a short pause inside a beat, a longer one between beats, the longest before the turn and the payoff, and 1.6 s held after the last word. Do not write `passages`; write a `"gap"` only to override one pause.

### 3b. Show what you say (every sentence, both channels)
Jared (2026-11-23): *add as many reference pictures as needed, source them all, and always make sure the video shows what the script is saying.*
- **Name it, show it.** Whenever a sentence names a real person, place, object, document, event or another artwork, the screen shows a real picture of it while it is said: a portrait, a photograph, the letter, the other painting, the building, the map. Find them on Wikimedia Commons (public-domain and CC files only; credits are added automatically). An illustration, map or stage prop is the fallback only when no real picture exists.
- **Request as many as the script needs**, usually 5-8 per video. Plan them from the beat sheet: one `look_for` entry per thing the script names. If a search returns nothing usable, try a second wording before you give up on the picture.
- **Paintings:** every sentence of the reveals and the turn shows something specific: a ring on the exact detail it talks about (starting as the sentence starts, not on its last word) or an insert picture of what it names. At least 4 inserts.
- **Philosophy:** every sentence starts something new on screen (a prop action, an overlay, a photo or a new angle), and every real person, place, study or event named gets a `photo` overlay.
- The draft check enforces this: `sentence N shows only the plain painting`, `nothing on screen changes`, `no real pictures`. Fix every one.

### 4. Write it in this order
1. Fact bank with surprise ratings (step 1).
2. Angle, answer, logline (step 2).
3. Beat sheet in your scratch work: one line per beat saying which fact goes there and how it links to the next ("reveal1: the new Prussian blue, so publishers advertised it" → "but: popular prints wore out their blocks").
4. Write the sentences beat by beat, tagging `beat` and `link`. Spoken English, 6-16 words each, varied length; one idea per sentence.
5. Write the hook **last**, then `hook_text` and two alternative hooks in `"hooks"`.
6. Read the whole script once as one paragraph, aloud in your head, as a viewer. Mark the exact sentence where you would swipe away; fix it. Check: does each sentence come out of the one before? Does the payoff answer the question asked at the start?
7. Run the draft check. It prints the beat map (`beats: hook 0-4s | question 4-9s | ...`) and a WARNING for anything that breaks the spine; fix every one.

### 5. Depth (the "complex enough" test)
- 5-7 facts a curious adult would not already know (surprise 4-5), at least one in every reveal, and at least **two real explanations of why or how** (a cause and its effect), not only *what*.
- **Myth-check:** if the topic has a popular story, find out whether it is true. A popular belief the evidence overturns makes an excellent `but`.
- **Paintings:** choose the thread from: the human story (the artist's situation and what they risked); how it was made (material or technique, and why that choice mattered); a detail the eye misses; the context that changes its meaning (history, politics, science, money); what happened to it afterwards. Show what you say: every reveal gets a highlight or an insert.
- **Philosophy:** who proposed it and the problem it was built to test; the strongest case on at least two sides; one real-world case where it matters now (law, medicine, AI, everyday life); one piece of evidence with a number when it exists; the move most people miss. End on a question harder than the one you started with.
- No filler. Cut "very", "really", "iconic", "masterpiece", "little did he know", "in this video", "but that's not all".

### Self-score
Score 1-5: hook, question clarity, flow (every link real?), surprise (count the 4-5 facts), depth (the why/how), escalation (is reveal3 the strongest?), payoff (does it answer the question?), accuracy. Rewrite anything under 4.

### 6. Mechanics
- Spoken English. Sentences under about 20 words, one idea each, written to be heard: read it at speaking pace in your head.
- Write numbers and names the voice may misread with `"say"`: `{"text": "In 1889, ...", "say": "In eighteen eighty-nine, ..."}`. Spell foreign names phonetically in `say`.
- Pauses come from the beats (above). Only for a spec without beats (old videos): `passages` groups sentences spoken in one breath and `"gap"` sets the pause after one.
- Every claim true and checkable. Put the pages you actually used in `"sources"`. If a popular story is doubtful, say "the story goes" or leave it out.
- On-screen captions are automatic. The **post** is drafted by you, ready to paste (Jared posts by hand every night, so it must need no editing). No emoji.
  - `post.caption`: line 1 = one or two sentences that tease the most surprising fact (a question or a tease, never a summary); line 2 = one short question that invites a comment ("Ship 1 or ship 2?").
  - `post.tags`: 4-6 hashtags: one broad (#arthistory / #philosophy), two specific to the topic, one or two in between.
  - `post.youtube_title`: at most 60 characters, a curiosity line that is true (no clickbait the video doesn't pay off); " #Shorts" is added automatically.
  - Credits are added to the posted text automatically; don't write them.

## Cues (how things are timed)

Any `at / to / from / until / ring / zoom / labelAt / out / bars` value may be a number of seconds or a cue string:
`"3"` = start of sentence 3 (first is 0) · `"3:word"` = when that word is spoken in sentence 3 · `"3:word#2"` = its 2nd occurrence · `"3:word+0.4"` / `"3-0.3"` = offset in seconds · `"end"`.
The word must appear in that sentence's `text` exactly (punctuation and case ignored).

---

## Paintings channel ("Behind the Painting")

Look approved by Jared: the framed painting on a blurred backdrop, slow continuous camera, white serif captions, a classical piano piece under a calm British female voice. **75-88 s, 155-185 words, 13-17 sentences.**

Staging the structure: the hook over the opening pull-back from a detail → context with a photo of the place, person or object (**photo first**, map or illustration only when no usable photo exists) → each reveal found by the camera (ring, then zoom) or shown as an insert → the turn → the payoff on the whole painting.

**Never show only the painting.** Every video needs at least 2 inserts, ideally 3, (things that are not the painting): the place, the artist, the model, a sketch, the object depicted, the room it hangs in.

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
 "angle": "Why is a painting of a nameless girl one of the most famous faces in art?",
 "hooks": ["<other opening line>", "<other opening line>"],
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

Look approved by Jared: a small 3D stage with toy people, shown in one of two styles; plain white serif captions with a soft shadow; sound effects on actions; a calm male voice. **75-88 s, 185-215 words, 18-24 short sentences.** The last sentence is a question to the viewer, harder than the first.

**Choose the style per idea** (`"style"`), and say why in your report in five words:
- `clay`: glossy pastel toys, soft daylight. For warm, human, everyday or moral ideas: dilemmas about people, fairness, kindness, choices.
- `ps2`: early-2000s console graphics at sunset, fog, scanlines. For eerie, uncanny or nostalgic ideas: identity, simulations, machines, memory, death, paranoia.
- If either fits, use the one not used yesterday.

Staging the structure: the hook on a striking image of the dilemma → the set-up acted out → each reveal changes something on stage (a new person, a number, a choice made) → the turn as a new scene or a ghost of the other outcome → the payoff on a tight shot of `you`, ending on the closing question pill.

### Spec

```json
{"id": "experience-machine", "channel": "philosophy", "style": "ps2", "title": "THE EXPERIENCE MACHINE",
 "angle": "If a machine could make you feel happy forever, why do most people refuse it?",
 "hooks": ["<other opening line>", "<other opening line>"],
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
- **Photos** (real pictures over the stage, a white card with a caption): `{"type": "photo", "pick": ["hobbes", 0], "caption": "Thomas Hobbes, 1669", "from": "7", "to": "8-0.2"}`. `pick` is `[key, n]` from the inbox previews (`requests/<id>.json` with `look_for` only), exactly as for Paintings inserts; the credit is added automatically. Default place is the middle of the screen (`"pos": [540, 820]` to move it); it covers the stage, so keep the stage action for the sentences around it. Show one for every real person, place, study or event the script names, held for most of its sentence.
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
- No approval step (2026-11-22): scripts go straight to `specs/queue/` and are made. Jared watches every video and his feedback (in `feedback/inbox.md` or a chat) shapes the next ones.
- Scripts must be informative, interesting and complex: real research, one clear question, an escalating story with a payoff (see "Writing the script"). Short, shallow fact lists are not acceptable.
- Longer videos: 75-88 s on both channels, filled with surprising, little-known facts (at least 6 per video), never padding.
- One video per channel every day: `kit.yml` builds the posting page at 7 pm and Jared posts by hand at 8 pm Malaysia time. Keep 1-3 videos ready per channel.
- Every script follows the spine: hook (≤12 words, on-screen hook text) → question → three escalating reveals → turn → payoff that answers the question; every sentence linked to the one before with but / so / because / detail / answer; 5-7 facts told properly rather than many facts listed.
- Show what you say: every person, place, object, document or artwork the script names is shown with a real picture while it is said (as many pictures as needed, usually 5-8, all sourced and credited); every sentence puts something on screen that matches it. Philosophy videos use `photo` overlays for this.
- Free tools only. No paid services.
- Quality first, token use second: spend effort on research and writing; save it everywhere else.

## Corrections log
Add dated one-line entries here whenever Jared corrects a video, and fold lasting rules into the section above.
- 2026-11-17: pipeline created from the two approved sample videos (Starry Night; Trolley Problem in clay and PS2).
- 2026-11-17: first run on GitHub worked (picture search, both renderers, Releases). Music used so far: chopin-nocturne-op9-2 (Starry Night), bach-goldberg-aria (Girl with a Pearl Earring, not yet heard by Jared).
- 2026-11-18: Jared found the first videos not informative, interesting or complex enough. Added the review step (GitHub issues) and the "Writing the script" standard; videos are now 60-80 s (Paintings) and 45-70 s (Philosophy).
- 2026-11-21: Jared asked for longer videos with more surprising, less-known facts, and daily automatic posting at 8 pm MYT. Both channels now 75-88 s (Facebook API max 90 s); surprise rating added to research; post.yml posts to Instagram and Facebook.
- 2026-11-22: Jared dropped the script approval step: scripts go straight to the queue; he watches each video and sends feedback for the next ones (reply on the evening reminder issue → `feedback/inbox.md`).
- 2026-11-23: Jared: new videos are more educational but jump from point to point and cut abruptly. Added the spine (beats + links, checked by build.py), logline, fact budget 5-7, on-screen hook text, automatic beat pacing, a 1.6 s held ending, and camera glides between nearby shots.
- 2026-11-23: Jared: add as many reference pictures as needed, source them all, and make the video show what the script says. Added "Show what you say", Philosophy `photo` overlays and picture requests, and draft-check warnings for sentences with nothing matching on screen.
- 2026-11-24: last remakes done (girl-pearl-earring, experience-machine); the 2026-11-23 remake list is finished.
