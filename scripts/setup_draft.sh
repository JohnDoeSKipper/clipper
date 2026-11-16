#!/bin/sh
# One-time setup for drawing draft check sheets (no voice model needed). Run from the repo root.
pip install -q --break-system-packages numpy pillow skia-python mido 2>/dev/null || pip install -q numpy pillow skia-python mido
(cd engine/stage && npm install --no-audit --no-fund --silent)
echo "draft tools ready"
