#!/bin/bash
# SMOOTH App-Preview base builder — the PREFERRED method.
# Instead of replaying janky in-app scroll/tap gestures, it builds the video from CLEAN STILL frames
# (one settled screenshot per beat), gives each a subtle Ken Burns motion, and joins them with XFADE
# crossfades. Result: buttery, premium, "flowing" — no unnatural swipes. Use a short REAL clip ONLY for
# inherently-animated beats (e.g. a loading spinner).
#
# Prep: extract one clean still per beat from your recordings (a frame where nothing is mid-gesture):
#   ffmpeg -y -ss <t> -i segX.mp4 -frames:v 1 stills/<beat>.png
# For scrollable content (analytics/lists), a single still + a down-PAN reads as a smooth scroll; if you
# want to reveal a lot, stitch 2 stills vertically into one tall PNG and zpan over it.
#
# Usage: W=1320 H=2868 bash build_smooth.sh   -> base_smooth.mp4   (then overlay + scale + audio)
set -u
export PATH="/opt/homebrew/bin:$PATH"
WORK="${WORK:-/tmp/asc_assets/video}"; cd "$WORK"
W="${W:-1320}"; H="${H:-2868}"; XF="${XF:-0.45}"      # crossfade seconds
US=$((W*2)); UH=$((H*2))                              # 2x prescale removes zoompan jitter

# CRITICAL: with -loop 1 you MUST bound output with -frames:v N (NOT -t) or zoompan's per-input-frame `d`
# explodes into a multi-minute clip. fr = dur*30.
zin(){  local fr=$(python3 -c "print(int($2*30))")    # Ken Burns push-in (centre zoom 1.0 -> ~1.14)
  ffmpeg -y -loop 1 -i "$1" -filter_complex \
   "[0]scale=$US:$UH,zoompan=z='min(1.0+0.0011*on,1.14)':d=$fr:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${W}x${H}:fps=30,setsar=1[v]" \
   -map "[v]" -frames:v $fr -r 30 -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p "$3" 2>/dev/null
  echo "  $3 $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $3)s"; }
zpan(){ local fr=$(python3 -c "print(int($2*30))")    # down-pan at fixed slight zoom = smooth "scroll"
  ffmpeg -y -loop 1 -i "$1" -filter_complex \
   "[0]scale=$US:$UH,zoompan=z=1.08:d=$fr:x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/$fr':s=${W}x${H}:fps=30,setsar=1[v]" \
   -map "[v]" -frames:v $fr -r 30 -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p "$3" 2>/dev/null
  echo "  $3 $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $3)s"; }
rclip(){ ffmpeg -y -i "$1" -t $2 -vf "fps=30,scale=$W:$H,setsar=1" -r 30 -an \
   -c:v libx264 -crf 18 -pix_fmt yuv420p "$3" 2>/dev/null                # normalize a short REAL clip
  echo "  $3 $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $3)s"; }

# ---- BEATS (edit for your storyboard; kind = zin|zpan|rclip). Total ≈ Σdur - (n-1)·XF; keep 15-30 s. ----
echo "building beat clips..."
zin   stills/add.png       2.6 z_1.mp4     # start-action sheet
zin   stills/picker.png    2.4 z_2.mp4     # pick the input
rclip stills/analyzing.mp4 2.0 z_3.mp4     # processing spinner (real motion)
zin   stills/review.png    3.0 z_4.mp4     # AI result / detected fields
zin   stills/form.png      3.2 z_5.mp4     # auto-filled form
zpan  stills/an_top.png    3.4 z_6.mp4     # feature / analytics (down-pan)
zpan  stills/an_scroll.png 3.8 z_7.mp4     # more analytics

# ---- XFADE chain (offsets auto-computed: offset_i = running_length - XF) ----
CLIPS="z_1.mp4 z_2.mp4 z_3.mp4 z_4.mp4 z_5.mp4 z_6.mp4 z_7.mp4"
python3 - "$XF" $CLIPS <<'PY'
import sys, subprocess
xf = float(sys.argv[1]); clips = sys.argv[2:]
dur = lambda f: float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
      "-of","default=nw=1:nk=1", f], capture_output=True, text=True).stdout)
ds = [dur(c) for c in clips]
args = ["ffmpeg", "-y"]
for c in clips: args += ["-i", c]
fc = ""; prev = "[0]"; run = ds[0]
for i in range(1, len(clips)):
    off = round(run - xf, 3); lab = f"[x{i}]"
    fc += f"{prev}[{i}]xfade=transition=fade:duration={xf}:offset={off}{lab};"
    prev = lab; run += ds[i] - xf
fc += f"{prev}format=yuv420p[v]"
args += ["-filter_complex", fc, "-map", "[v]", "-r", "30",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "base_smooth.mp4"]
subprocess.run(args)
print("=== base_smooth.mp4 dur (want 15-30s):", round(dur("base_smooth.mp4"), 2), "s ===")
PY
