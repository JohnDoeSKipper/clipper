"""Runs on GitHub when Jared comments on a script-review issue (see .github/workflows/approve.yml).
A one-word approval moves the draft to the queue and starts the render; anything else is saved as feedback for the writer."""
import datetime
import os
import re
import subprocess
import sys

APPROVE = re.compile(r"^\s*(approve|approved|ok|okay|yes|go|go ahead|lgtm|looks good|good|make it|\U0001F44D|✅)\s*[.!]*\s*$", re.I)


def sh(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout.strip()


def comment(num, text):
    sh("gh", "issue", "comment", num, "--body", text)


def push(message):
    sh("git", "config", "user.name", "clipper-bot")
    sh("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    sh("git", "commit", "-q", "-m", message)
    for _ in range(3):
        if subprocess.run(["git", "pull", "-q", "--rebase"]).returncode == 0 and subprocess.run(["git", "push", "-q"]).returncode == 0:
            return
    sys.exit("could not push")


def remember_approved(sid, spec_path):
    """Keep the latest approved scripts in one short file the writer reads as its standard."""
    import json
    spec = json.load(open(spec_path))
    path = "catalog/approved-scripts.md"
    head = "# Scripts Jared approved (newest first)\nThe writer reads the top two of its channel before writing. Kept to the last 12.\n"
    entries = []
    if os.path.exists(path):
        entries = [e for e in open(path).read().split("\n## ")[1:]]
    day = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
    new = f"{sid} ({spec['channel']}, approved {day})\n\n" + "\n".join(s["text"] for s in spec["script"]) + "\n"
    entries = [new] + [e for e in entries if not e.startswith(sid + " ")]
    open(path, "w").write(head + "".join("\n## " + e.rstrip("\n") + "\n" for e in entries[:12]))
    sh("git", "add", path)


def main():
    title, body, num = os.environ["TITLE"], os.environ["BODY"], os.environ["NUM"]
    m = re.match(r"^\[([a-z0-9-]+)\]", title)
    if not m:
        return
    sid = m.group(1)
    draft = f"specs/review/{sid}.json"
    if not os.path.exists(draft):
        comment(num, "I can't find this draft any more: it may already be approved, or replaced by a newer version.")
        return
    if APPROVE.match(body):
        os.makedirs("specs/queue", exist_ok=True)
        sh("git", "mv", "-f", draft, f"specs/queue/{sid}.json")
        for extra in (f"specs/review/{sid}.feedback.md", f"specs/review/{sid}_sheet.jpg"):
            if os.path.exists(extra):
                sh("git", "rm", "-q", "-f", extra)
        remember_approved(sid, f"specs/queue/{sid}.json")
        push(f"Approved {sid}")
        sh("gh", "workflow", "run", "render.yml", "--ref", "main")
        sh("gh", "issue", "edit", num, "--remove-label", "changes-requested", check=False)
        comment(num, "Approved. The video is being made now and will be on the Releases page in about 5 to 25 minutes. This issue closes itself when it is done.")
    else:
        day = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        with open(f"specs/review/{sid}.feedback.md", "a") as f:
            f.write(f"### Jared, {day}\n\n{body.strip()}\n\n")
        sh("git", "add", f"specs/review/{sid}.feedback.md")
        push(f"Feedback on {sid}")
        sh("gh", "issue", "edit", num, "--add-label", "changes-requested", check=False)
        comment(num, "Got it. The writer will rewrite this script tomorrow morning and post the new version here. "
                     f"For a faster rewrite, tell Claude in the CLIPPER project: *revise {sid}*.")


if __name__ == "__main__":
    main()
