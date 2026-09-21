#!/usr/bin/env python3
"""
Generic poll-driven simulator recorder for App-Preview capture.
Records the whole session, drives the app with idb, and DETECTS screen state via PIL
(so it never desyncs when a picker / network / AI step is slow). Logs every tap's
(label, x, y, t) relative to record start — feed those into overlay_gen.py.

Env:  UDID (simulator udid).   Usage: python3 drive.py out.mp4
Fill in `flow()` with your app's tap/swipe recipe using the helpers + detectors below.
Coordinates are DEVICE POINTS (e.g. iPhone 16 Pro 440x956), NOT screenshot pixels.
"""
import os, sys, time, subprocess, statistics
from PIL import Image

D = os.environ["UDID"]
SCALE = int(os.environ.get("SCALE", "3"))   # screenshot px per point: iPhone/most iPad=3, some iPad=2
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/asc_assets/video/raw.mp4"
POLL = "/tmp/_poll.png"
LOG = []
T0 = None


def run(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
def tap(x, y): run(f"idb ui tap {x} {y} --udid {D}")
def swipe(a, b, c, d, dur=0.5): run(f"idb ui swipe {a} {b} {c} {d} --duration {dur} --udid {D}")
def now(): return time.time() - T0


def logt(label, x=None, y=None):
    t = now(); LOG.append((label, x, y, round(t, 2)))
    print(f"  t={t:5.2f}  {label}" + (f"  ({x},{y})" if x is not None else ""))


def shot():
    run(f"xcrun simctl io {D} screenshot {POLL}")
    return Image.open(POLL).convert("RGB")


# ---------- generic detectors ----------
def region_std(im, box):
    """grayscale std-dev of a region; low = blank/loading, high = loaded content/grid."""
    return statistics.pstdev(list(im.crop(box).convert("L").getdata()))


def region_is_colour(im, box, rgb, tol=45):
    px = list(im.crop(box).getdata()); n = len(px)
    r = sum(p[0] for p in px) / n; g = sum(p[1] for p in px) / n; b = sum(p[2] for p in px) / n
    return abs(r - rgb[0]) < tol and abs(g - rgb[1]) < tol and abs(b - rgb[2]) < tol


def find_cta_button(im, rgb=(16, 185, 129)):
    """Find the widest horizontal band of a target colour (the primary CTA). Return device (x,y) or None."""
    W, H = im.size; px = im.load(); by, bc, bx = None, 0, None
    r0, g0, b0 = rgb
    for y in range(int(H * 0.30), H - 40, 4):
        xs = [x for x in range(30, W - 30, 6)
              if abs(px[x, y][0] - r0) < 60 and abs(px[x, y][1] - g0) < 55 and abs(px[x, y][2] - b0) < 70
              and px[x, y][1] - px[x, y][0] > 60]
        if len(xs) > bc:
            bc, by, bx = len(xs), y, xs
    if by is None or bc < 60:
        return None
    return ((min(bx) + max(bx)) // 2 // SCALE, by // SCALE)   # px -> device points


def poll(cond, timeout, label, iv=1.0):
    t = time.time(); last = None
    while time.time() - t < timeout:
        im = shot(); ok, info = cond(im); last = info
        if ok:
            print(f"    [{label}] ready ({info}) {time.time()-t:.1f}s"); return im
        time.sleep(iv)
    print(f"    [{label}] TIMEOUT ({last})"); return shot()


# ---------- CUSTOMISE: your app's flow ----------
def flow():
    """Example skeleton — replace taps/swipes/polls with your app's hero flow.
    Use points (not pixels). Use poll(...) around any slow transition (picker, network, parse)."""
    GRID = (30, 1380, 1290, 2450)          # a content region to gate 'loaded vs blank' (tune per app)
    time.sleep(2.5); logt("home")
    tap(219, 894); logt("tap primary-action", 219, 894); time.sleep(2.6)
    tap(322, 379); logt("tap pick-source", 322, 379); time.sleep(1.0)
    poll(lambda im: (region_std(im, GRID) > 42, f"std={region_std(im,GRID):.0f}"), 28, "list-ready")
    tap(77, 203);  logt("tap select-item", 77, 203)         # e.g. newest photo top-left
    time.sleep(14)                                           # slow step (parse/network) — or poll a signal
    btn = find_cta_button(shot())
    (tap(*btn), logt("tap CTA", *btn)) if btn else (tap(220, 852), logt("tap CTA FALLBACK", 220, 852))
    time.sleep(3.0)
    for _ in range(4):
        swipe(220, 770, 220, 240); time.sleep(0.7)          # scroll a form/list
    btn = find_cta_button(shot())
    (tap(*btn), logt("tap save", *btn)) if btn else (tap(220, 852), logt("tap save FALLBACK", 220, 852))
    time.sleep(4.0)
    tap(350, 884); logt("tap feature/analytics", 350, 884); time.sleep(3.2)   # go to the payoff screen
    swipe(220, 770, 220, 250); logt("browse charts"); time.sleep(2.6)


def main():
    global T0
    rec = subprocess.Popen(f"xcrun simctl io {D} recordVideo --codec h264 --force {OUT}",
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    T0 = time.time()
    flow()
    time.sleep(0.5); rec.send_signal(2); time.sleep(3)      # SIGINT stops recording cleanly
    print("\n=== TAP LOG (feed to overlay_gen taps, x*scale for px) ===")
    for l in LOG:
        print(l)


if __name__ == "__main__":
    main()
