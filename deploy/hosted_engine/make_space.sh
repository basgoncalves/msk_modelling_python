#!/usr/bin/env bash
# Copies what the engine needs into ./space, ready to push to the Hugging Face Space.
# Usage (Git Bash, from the bioscout repo root):  bash deploy/hosted_engine/make_space.sh <hf-space-git-url>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/../.." && pwd)"
url="${1:?give the Space git url, e.g. https://huggingface.co/spaces/basgoncalves/bioscout-engine}"
out="$here/space"
[ -d "$out/.git" ] || git clone "$url" "$out"
rm -rf "$out/bioscout" "$out/example_data"
mkdir -p "$out/example_data"
cp "$here/Dockerfile" "$here/README.md" "$out/"
# Leave out the Windows CEINMS binaries, logs and build junk (~700 MB).
(cd "$root" && tar cf - --exclude=__pycache__ --exclude='*.exe' --exclude='*.dll' \
    --exclude='*.log' --exclude='log.txt' --exclude='*.pkl' --exclude='*.zip' --exclude='*.png' --exclude='*.jpg' --exclude='*.jpeg' --exclude='*.gif' --exclude='*.task' --exclude='*.mp4' --exclude='*.pdf' --exclude='bioscout/tests' \
    --exclude='bioscout/gui' --exclude='bioscout/utils/ceinms' bioscout) | (cd "$out" && tar xf -)
(cd "$root" && tar cf - --exclude='*.png' --exclude='*.jpg' --exclude='*.pdf' --exclude='*.mp4' example_data/orthoload) | (cd "$out" && tar xf -)
find "$out" -name __pycache__ -type d -prune -exec rm -rf {} +
cd "$out" && git add -A && git commit -m "Update engine" --author="Bas <basilio.goncalves7@gmail.com>" && git push "$url" HEAD:main
