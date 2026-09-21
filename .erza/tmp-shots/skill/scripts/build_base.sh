#!/bin/bash
# Generic base-video builder: cut clips from the raw screen-recordings with per-clip speed, concat.
# Edit the CLIPS table for your storyboard. Sources may be 1..N recordings (import + results + ...).
#
# WHY -ss/-t (input seeking) and NOT the `trim` filter:
#   simctl recordVideo produces VARIABLE-frame-rate (VFR) files. The `trim=A:B` filter on a raw VFR
#   source silently drops clips to near-zero frames (or empty) — you get a base that is missing beats
#   or the wrong duration. `-ss START -t DUR` BEFORE `-i` seeks by input timestamp and is reliable on
#   VFR; the per-clip re-encode to CFR 30 then makes the concat frame-accurate. (Learned the hard way.)
#
# Usage: bash build_base.sh   (set W,H to your recording px; edit SRC list + CLIPS)
set -u
export PATH="/opt/homebrew/bin:$PATH"
WORK="${WORK:-/tmp/asc_assets/video}"; cd "$WORK"
W="${W:-1320}"; H="${H:-2868}"                       # recording px (iPhone 6.9" default)

clip(){ # src START DUR SPEED out   (START,DUR = seconds in the RAW source; robust on VFR)
  ffmpeg -y -ss "$2" -t "$3" -i "$1" \
    -vf "setpts=(PTS-STARTPTS)/$4,fps=30,scale=$W:$H,setsar=1" \
    -an -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p "$5" 2>/dev/null
  echo "  $5 dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $5)"
}

# CLIPS table — one line per beat. Keep hero beats ~1.15-1.3x; compress dead time (loading) more.
# Target 18-28s total (App Preview MUST be 15-30s). Verify with a montage before overlaying.
echo "cutting clips..."
clip s1.mp4   3.0  2.0  1.15 c01.mp4    # start-action sheet (scan feature)
clip s1.mp4   7.0  3.0  1.2  c02.mp4    # pick source (gallery/picker)
clip s1.mp4  18.5  2.2  1.3  c03.mp4    # processing (short)
clip s2.mp4   3.0  3.5  1.25 c04.mp4    # AI review / detected fields
clip s2.mp4  15.0  3.5  1.2  c05.mp4    # auto-filled form
clip s3.mp4   3.0  9.4  1.15 c06.mp4    # feature / analytics browse (money shot)

# concat (order = list.txt)
: > list.txt; for c in c01 c02 c03 c04 c05 c06; do echo "file $c.mp4" >> list.txt; done
ffmpeg -y -f concat -safe 0 -i list.txt -c copy base.mp4 2>/dev/null
echo "=== base.mp4 dur (want 15-30s) ==="; ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 base.mp4
