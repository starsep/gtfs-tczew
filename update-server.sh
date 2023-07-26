#!/usr/bin/env bash
set -eu
date=$(/bin/date '+%Y%m%d')
git clone https://$GITHUB_USERNAME:$GITHUB_TOKEN@github.com/starsep/gtfs --depth 1 --branch main output
python main.py
(
    cd output || exit 1
    git config user.name "GitHub Actions Bot"
    git config user.email "<>"
    git add gtfs-tczew.zip
    git commit -m "Update $date"
    git push origin main
)
