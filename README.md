# CLIPPER

Makes two short vertical videos a day, automatically and for free:

- **Behind the Painting** – the story hidden in a famous painting.
- **Thought experiments** – philosophy and psychology in 30 seconds, in a clay-toy or a PS2-game look.

## How it works

1. Once a day Claude writes a small text file (a "spec") for each video and pushes it to `specs/queue/`.
2. GitHub then does the heavy work on its own computers: fetches pictures from Wikimedia Commons, speaks the narration, plays the piano piece, draws every frame and builds the video.
3. The finished videos appear on the **Releases** page of this repository, each with a `.txt` holding the caption, hashtags and credits to paste when posting, and a `_sheet.jpg` of check frames.

Nothing here costs money: public repositories get free GitHub Actions minutes, and every tool, font, sound and score used is free or open.

## Folders

| Folder | What is in it |
|---|---|
| `specs/queue` | Videos waiting to be made. `specs/done` = made. `specs/failed` = something went wrong (with a log). |
| `requests`, `inbox` | Picture requests for upcoming paintings, and the previews GitHub found for them. |
| `topics` | The lists of upcoming video ideas for each channel. Edit freely. |
| `catalog/music.json` | The piano pieces the Paintings channel can choose from. |
| `PLAYBOOK.md` | The rules the daily writer follows, including every correction from the owner. |
| `engine` | The code that draws and voices the videos. |

## Making a video by hand

Open the **Actions** tab → **Render videos** → **Run workflow**. Everything in `specs/queue` is rendered.

## Credits

See `CREDITS.md`.
