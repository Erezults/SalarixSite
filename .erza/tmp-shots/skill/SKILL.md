---
name: erez-pics-video-canvas-asc
description: >
  End-to-end, fully-autonomous production of App-Store marketing assets for ANY Expo/RN (or native)
  iOS app: dedicated per-platform simulators (iPhone, iPad, and a LANDSCAPE iPad used to source Mac
  shots) running the PRODUCTION build, screenshots in two languages at each platform's exact resolution
  (MANDATORY 10 per language per platform, spanning Dark + Light — not a suggestion, this is the
  completion gate), a polished in-app demo VIDEO per language per platform (MANDATORY 2 videos per
  platform — one per language), and upload of every image + video to App Store Connect via the ASC API,
  verified COMPLETE. Use when asked to "create App Store screenshots/previews", "make a marketing video
  from the app", "frame screenshots with Canvas", or "upload assets to ASC".
---

# erez-pics-video-canvas-asc — App Store screenshots + preview video, end-to-end

A generic, reproducible pipeline that turns any running iOS app into a full set of App-Store-ready
marketing assets and pushes them live — **autonomously**, no human in the loop. Nothing here is
app-specific: fill the **Config block** once per app and every phase follows.

Companion skills: `erez-ios-build-and-ota` (builds the prod binary / `.app`), `erez-release-versioning`.

## Config block (fill once per app)

```bash
APP_BUNDLE="com.example.myapp"          # PRODUCTION bundle id (NOT the .dev one)
APP_PATH="/path/to/MyApp.app"           # a PRODUCTION-config build to install on the sim
APP_DIR="$HOME/GitSync/MyApp"           # repo root (for Info.plist landscape patch)
BRAND_FONT="$APP_DIR/assets/fonts/Brand-ExtraBold.ttf"   # a real TTF for captions (bold display face)
# Premium palette (frame.py + overlay_gen.py). Two accent hues + a deep "ink" base — match your brand.
BRAND_A1="#10B981"; BRAND_A2="#34D3EE"  # accent gradient: kicker dot, keyword, glow, caption underline
BRAND_INK="#0A1420"; BRAND_INK2="#0F2634"  # deep atmospheric framing background (NOT a pale wash)
BRAND_WORDMARK="MYAPP"                   # optional faint wordmark on framed shots ("" to hide)
CAPTION_LANGS=("he" "en")               # asset languages (RTL handled automatically)
N_SCREENS=10                            # EXACTLY 10 per language per platform (ASC max per localization)
WORK="/tmp/asc_assets"; mkdir -p "$WORK"/{raw,html,framed,video}
# ASC
ASC_KEY="$HOME/.appstoreconnect/private_keys/AuthKey_<KID>.p8"
ASC_KID="<KID>"; ASC_ISS="<ISSUER-UUID>"
ASC_VERSION_ID="<appStoreVersion id you're attaching assets to>"
```

## The five phases

| Phase | Output | Tooling |
|---|---|---|
| **A. Simulators** | booted sims per platform (incl. **landscape iPad**), PROD app, appearance+language | `simctl`, `idb`, `osascript` |
| **B. Screenshots** | raw PNGs: platform × language × Dark/Light | `simctl io screenshot`, `idb ui` |
| **C. Canvas framing** | framed marketing PNGs at exact ASC resolutions | Chrome headless (HTML→PNG) |
| **D. Video** | 15-30 s App Preview (taps + captions + feature browse) | `simctl recordVideo`, PIL driver, ffmpeg |
| **E. ASC upload** | screenshots + previews live on the listing | ASC API (JWT ES256) |

**Non-negotiables (each cost real debugging time):**
- **Use the PRODUCTION app** (`$APP_BUNDLE`, never the `.dev`). Marketing assets ship from prod.
- **The asset matrix is a REQUIREMENT, not a recommendation — this is the definition of done, not an
  aspirational target.** Per platform (iPhone, iPad, Mac), deliver **exactly 10 screenshots for EACH
  language** (`he` **and** `en`), and those 10 must **span both Dark and Light** (a curated mix, minimum
  3 of each — never all-one-mode; 10 is App Store Connect's hard maximum per localization, so you can't
  ship 10 dark *plus* 10 light). So **10 he + 10 en = 20 framed screenshots per platform**; across
  iPhone + iPad + Mac = **60 total**. Do not stop at a partial curated set (e.g. 4/10) and call it done —
  verify the actual uploaded count via the ASC API (Phase E) before reporting completion.
- **Video is likewise a hard requirement: 2 App Previews per platform (one per language) minimum** — not
  "a video if time allows". Across iPhone + iPad + Mac = **6 previews minimum**. A video that gets
  produced but freezes/stalls mid-playback (see D2/D3 gotchas) does NOT count as delivered — montage-verify
  motion across the FULL duration, not just presence of *a* file.
- **App Previews REQUIRE a stereo audio track** — silent/mono ⇒ Apple rejects `MOV_RESAVE_STEREO`.
- `idb` taps/swipes use **device POINTS** (e.g. 440×956), not screenshot PIXELS (e.g. 1320×2868).
  A swipe to `y=1300` on a 956-pt-tall device silently no-ops.
- Presigned S3 upload PUTs carry **no Authorization header** — only the headers ASC hands you.
- **Before declaring the job done, run the Phase E completion-gate check** (query every screenshotSet
  and previewSet's actual item count + `assetDeliveryState` per locale/platform) — do not trust local
  file counts or an earlier partial run's report. See "Definition of done" below.

### Exact App Store resolutions (portrait unless noted)

| Slot | Screenshot px | App Preview px | ASC `displayType` / `previewType` |
|---|---|---|---|
| iPhone 6.9" | **1320 × 2868** | **886 × 1920** | `APP_IPHONE_67` / `IPHONE_67` |
| iPad 13"/12.9" | **2048 × 2732** ⚠️ | 1200 × 1600 | `APP_IPAD_PRO_129` / `IPAD_PRO_129` |
| Mac (landscape 16:10) | **2880 × 1800** | 1920 × 1080 | `APP_DESKTOP` / `DESKTOP` |

`simctl io screenshot` natively emits **1320×2868** for a matching iPhone (@3×), and **2064×2752** for an
iPad Pro 13" (M4) simulator (@2×) — but **ASC's `APP_IPAD_PRO_129` slot only accepts 2048×2732** (the
legacy 12.9" marketing spec; it does NOT accept the M4 simulator's native 2064×2752 and rejects it with
`IMAGE_INCORRECT_DIMENSIONS`, all screenshots FAILED/invisible on the listing — confirmed on OwnestNative
2026-07-09). **Always resize/re-frame the iPad screenshot to 2048×2732 in Phase C** (frame.py's `size`
config), never ship the simulator's raw 2064×2752. **Mac has no marketing simulator → source Mac shots
from a LANDSCAPE iPad** (Phase A + B).

---

## Phase A — Simulators (PROD app on iPhone, iPad, and a LANDSCAPE iPad)

Create/boot one dedicated sim per platform. The Mac slot needs a **third sim: an iPad forced into
landscape**, because Mac screenshots are 2880×1800 landscape and there is no Mac marketing sim.

```bash
# --- create the three devices ---
xcrun simctl create "ASC-iphone"        "iPhone 16 Pro"          >/dev/null   # 1320×2868
xcrun simctl create "ASC-ipad"          "iPad Pro 13-inch (M4)"  >/dev/null   # native 2064×2752 → RESIZE to 2048×2732 in Phase C
xcrun simctl create "ASC-ipad-landscape" "iPad Pro 13-inch (M4)" >/dev/null   # → Mac shots (landscape)
udid(){ xcrun simctl list devices | grep "$1 (" | grep -oE '[0-9A-F-]{36}' | head -1; }
IP=$(udid ASC-iphone); PAD=$(udid ASC-ipad); PADL=$(udid ASC-ipad-landscape)
for u in $IP $PAD $PADL; do xcrun simctl boot $u; done

# --- install & launch the PRODUCTION build on each ---
for u in $IP $PAD $PADL; do
  xcrun simctl install $u "$APP_PATH"
  xcrun simctl privacy $u grant photos "$APP_BUNDLE"   # if the demo imports images
  xcrun simctl launch  $u "$APP_BUNDLE"
done
```

### Making the iPad sim LANDSCAPE (for Mac shots) — two methods

**Method 1 — rotate the Simulator window (preferred when the Mac GUI is available & unlocked).**
`simctl`/`idb` have no rotate verb, so drive the Simulator UI with AppleScript (⌘→ = rotate right):
```bash
open -a Simulator                                   # bring the landscape sim to front
osascript -e 'tell application "Simulator" to activate' \
          -e 'tell application "System Events" to key code 124 using command down'   # ⌘→ (right)
# verify: a screenshot is now 2752×2064 (landscape). Repeat key code 124 to keep rotating if needed.
xcrun simctl io $PADL screenshot "$WORK/_probe.png"   # identify: expect landscape wxh
```
Requires the machine to be **unlocked** (a locked Mac blocks System-Events UI scripting).

**Method 2 — force the APP to landscape (robust, fully headless).** Patch the installed prod app's
`Info.plist` so it only supports landscape; it then renders landscape even inside a portrait sim frame,
and you crop the landscape content band in framing (Phase C):
```bash
PLIST="$APP_PATH/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :UISupportedInterfaceOrientations~ipad" "$PLIST" 2>/dev/null
/usr/libexec/PlistBuddy -c "Add :UISupportedInterfaceOrientations~ipad array" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :UISupportedInterfaceOrientations~ipad:0 string UIInterfaceOrientationLandscapeRight" "$PLIST"
xcrun simctl install $PADL "$APP_PATH"; xcrun simctl launch $PADL "$APP_BUNDLE"
# screenshot is portrait-framed (native 2064×2752) but the CONTENT is landscape → crop band in Phase C.
```
Use Method 2 in CI / unattended runs (no GUI dependency). Keep a pristine copy of the app so you can
reinstall the un-patched build for other passes.

### Per-pass state — appearance & language
Set **before each capture pass**; you will loop passes over `{dark,light} × CAPTION_LANGS`.
```bash
xcrun simctl ui $IP appearance dark      # or light
```
**Language** — prefer whichever the app exposes, in this order:
- **In-app language toggle** (drive the settings/auth toggle with `idb ui tap`) — deterministic,
  locale-independent. Best for apps that self-manage locale.
- **Device locale**: relaunch the app process with `-AppleLanguages '(he)'` / `'(en)'` (Expo/RN reads it),
  or set the sim's system language.

**Sim hygiene.** Long automation can orphan procs and spike load. If a sim wedges:
`pkill -9 -f "iOS_<runtime>"`, re-boot. Prefer capturing one platform at a time.

---

## Phase B — Screenshots (10 per language, spanning Dark + Light)

**Target per platform: 10 framed screenshots for `he` AND 10 for `en` (= 20).** Because App Store
Connect caps a localization at 10 screenshots, the 10 you ship for each language are a **curated mix of
Dark and Light** (e.g. capture your 10 hero screens, then take ~5 in Dark and ~5 in Light and pick the
best 10). Drive the app to each screen with `idb ui tap/swipe`, then screenshot. **During calibration,
screenshot BEFORE every tap** — a blind tap at the wrong coordinate silently derails the whole run.

Capture strategy: shoot each hero screen in both appearances, then curate down to 10 per language so the
final set alternates Dark/Light for visual variety on the listing.

```bash
shot(){  xcrun simctl io "$1" screenshot "$2"; }             # $1=udid $2=out.png
tap(){   idb ui tap  $2 $3 --udid "$1"; }                    # POINTS, not pixels
swipe(){ idb ui swipe $2 $3 $4 $5 --duration ${6:-0.5} --udid "$1"; }

for mode in dark light; do
  xcrun simctl ui $IP appearance $mode
  for lang in "${CAPTION_LANGS[@]}"; do
    set_app_language $IP $lang           # in-app toggle or relaunch with -AppleLanguages
    for i in $(seq -w 1 $N_SCREENS); do
      drive_to_screen $IP $i             # your per-screen tap/swipe recipe
      shot $IP "$WORK/raw/iphone_${lang}_${mode}_${i}.png"
    done
  done
done
# ^ captures candidates in BOTH appearances. Then CURATE to exactly 10 per language
#   (a Dark+Light mix) before framing — ASC accepts max 10 per localization.
# repeat for $PAD (portrait iPad) and $PADL (landscape iPad → Mac)
```

**Coordinate math (points↔pixels).** `pixel = point × scale` (iPhone/iPad @3× or @2×). If your viewer shows
a screenshot downscaled, convert back to native px first, then `÷ scale` to get the point you feed `idb`.
**Valid tap range = device POINTS** (iPhone 16 Pro x∈[0,440], y∈[0,956]). Passing a pixel value like 1300
no-ops — the classic silent failure.

**Framing the Mac crop (Method 2).** A landscape-forced iPad screenshot is portrait-framed with a landscape
content band. Detect the band once (scan for the non-background rows) and reuse the crop rectangle for all
Mac shots; frame it to 2880×1800 in Phase C.

**Large-screen font size (iPad + Mac) — REQUIRED.** If the app exposes a display / font-size setting, set
it to the **LARGEST** option before capturing **iPad and Mac** screenshots. On big canvases the default
size reads as tiny-font and looks unprofessional on the listing. Set it via the app's settings screen
(drive the largest pill/option with `idb ui tap`) at the start of the iPad and landscape-iPad passes, and
reset to default afterwards if you also shoot iPhone from the same install. (iPhone keeps the default size.)

---

## Phase C — Canvas framing (HTML → PNG, PREMIUM editorial look)

Composite each raw screenshot into a branded frame rendered by **Chrome headless** — perfect RTL, real
fonts, CSS gradients/glows. Output = the exact ASC px. See `scripts/frame.py` (generic; reads `WORK/raw/*`
and the Config block). **A flat pale-gradient wash with a small dark caption reads as generic "AI slop" —
do NOT ship that.** The look that tested as premium ("editorial fintech", à la Linear/Stripe/Revolut):

**THE LOOK — every knob (frame.py implements this; keep it):**
- **Background — deep + atmospheric, universal (works under light AND dark screenshots):** a near-black
  brand-navy base with **layered radial glows** in the two accent hues, plus a faint dot-grid texture
  masked to the centre. Not a solid colour, not a pale wash.
  `radial-gradient(mint@18%,-12%) , radial-gradient(cyan@96%,112%) , linear-gradient(158deg, ink→ink2→ink)`.
- **Device — floats:** rounded corners, a **2px light rim** (`box-shadow 0 0 0 2px rgba(255,255,255,.10)`),
  a **big soft drop shadow**, a **mint under-glow** (blurred radial behind it), and a top **gloss**
  highlight. `object-fit:contain` — NEVER distort the screenshot.
- **Caption — editorial hierarchy, BIG:** an **eyebrow KICKER** (small, uppercase, wide letter-spacing,
  cyan, with a glowing dot) above a **huge bold HEADLINE** (~7.9% of the frame's short side — deliberately
  large; the old size was too small) with **one keyword in a mint→cyan gradient**. Optional brand wordmark,
  faint, centred at the bottom.
- **Palette (override in config):** accent `#10B981`→`#34D3EE` (mint→cyan), ink `#0A1420`/`#0F2634`.
- **Config knobs:** `kicker` (per item), `*keyword*` in the caption → mint gradient span, `brand`,
  `accent1/accent2/ink/ink2`. Font = your BRAND_FONT, base64-embedded.
```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --virtual-time-budget=6000 --window-size=1320,2868 \
  --screenshot="$WORK/framed/iphone_he_dark_01.png" \
  "file://$WORK/html/iphone_he_dark_01.html"     # body authored at 1320×2868, window = same, sf=1
```

**Rules:**
- One caption per screen, **short and benefit-led**, in the image's language (RTL captions on RTL shots —
  the framer runs bidi/`direction:rtl`).
- Output size must equal the ASC px for the slot exactly. Author the HTML `body` at the **full target px**
  and set `--window-size` to the **same** full px with `--force-device-scale-factor=1`. **Do NOT** use a
  half-window + `scale-factor=2` — the body then overflows the CSS viewport and, in RTL, you screenshot a
  **blank left edge** (silent all-white PNG). Add `--virtual-time-budget=6000` so the big embedded
  base64 font+image decode before the capture (otherwise Chrome snaps a blank frame).
- **Embed the font as base64** in `@font-face`; a `file://` render cannot fetch a remote font and silently
  falls back to a system face (wrong look). Verify the TTF is real: `file BRAND_FONT` → "TrueType font".
- Mac: crop the landscape band out of the landscape-iPad screenshot, then fit to 2880×1800.

Produce the full matrix `{iphone,ipad,mac} × CAPTION_LANGS × {dark,light}` → `N_SCREENS` framed per lang/plat.

---

## Phase D — The demo video (the hard part)

A 15-30 s App Preview showing a real end-to-end flow with **tap indicators**, **marketing captions**,
**smooth pacing (~1.2×, dead time cut)**, and the app's **key feature / analytics browse** — PROD app.

### D0. Demo data
If the flow needs input, generate it and inject it. Pick a **fresh entity** so any "add/save" step never
hits a duplicate/conflict dialog:
```bash
xcrun simctl addmedia $IP "$WORK/sample_input.png"   # e.g. an image the import flow consumes (newest → picker top-left)
```

### D1. Record reliably with a poll-driven driver (never fixed sleeps)
Fixed `sleep`s desync the instant a picker or a network/AI step is slow (they vary wildly). Drive with a
Python loop that **screenshots and detects screen state via PIL**, taps dynamically, and logs tap times.
See `scripts/drive.py`. Generic detectors it provides:
- **region_std(box)** — grayscale std-dev; a blank/loading region is low-variance, a loaded grid/content is
  high. Use to detect "picker/list ready".
- **find_cta_button(im, rgb)** — scan rows for the widest band of a target colour → the primary button's
  live `(x,y)`. CTAs move vertically with content; never hard-code them.
- **region_is_colour(box, rgb)** — detect a return-to-home / branded hero state.
Record the whole session (`simctl io recordVideo --codec h264 --force raw.mp4`) via `Popen`, stamp `t0`
right after, and log every tap `(label,x,y,t-t0)` — those timestamps drive the overlay in D4.

**Record in reliable SEGMENTS, and keep any slow step OUTSIDE a recording** (hard-won — the single
take failed repeatedly). The winning shape for an AI-parse flow was **3 recordings**:
- **segA (import):** dashboard → start-action → pick input → the processing spinner. Record only a few
  seconds of the spinner, then STOP. **Do NOT wait for the AI result inside the recording** — an AI/network
  step can spike from ~35 s to **90 s+**, and a long in-recording poll times out or bloats the file.
- **between segA and segB:** poll for the result screen (e.g. CTA button appears) with a **generous 90 s**
  timeout — this wait is NOT recorded, so its length doesn't matter.
- **segB (review→form):** the result/review screen → use-the-data → the auto-filled form → a scroll. STOP.
- **commit + segC (results):** a SEPARATE reliable step — **scroll fully to the bottom**, detect the green
  CTA, tap it, and **verify the next screen appeared** (poll the hero/home) BEFORE recording; then record
  dashboard → feature/analytics browse. A **blind** CTA tap fails when the button needs full scroll to reach
  its final position — always scroll-to-bottom + detect + verify. (`scripts/recflow.py` = segA+segB,
  `scripts/recresults.py` = commit+segC — Salarix-calibrated reference recorders.)

### D2. Verify every take with a montage BEFORE editing
```bash
ffmpeg -y -i raw.mp4 -vf "fps=1/2,scale=260:-1,tile=6x5" -frames:v 1 montage.png   # then Read it
```
Confirm the flow actually reached each intended screen (the money shot; the analytics/feature payoff).

### D3. Build the base — the SMOOTH method (PREFERRED; `scripts/build_smooth.sh`)
Replaying the recorded in-app scroll/tap gestures looks **janky** (unnatural swipes, jumpy pans) — users
notice. The premium result comes from **clean STILLS + programmatic motion + crossfades**, not from the raw
gestures:
1. **Extract one clean STILL per beat** from the recordings — a *settled* frame with nothing mid-gesture:
   `ffmpeg -y -ss <t> -i segX.mp4 -frames:v 1 stills/<beat>.png`. Montage them to confirm each is clean.
2. **Give each still a subtle Ken Burns move** — centre push-in (`zin`) for most beats, a **down-pan**
   (`zpan`) for scrollable content (analytics/lists) which reads as a smooth scroll. Use a short **real**
   clip only for an inherently-animated beat (a spinner).
   **zoompan gotcha:** with `-loop 1` you MUST bound output with `-frames:v N` (N = dur·30), NEVER `-t` —
   `-t` makes zoompan's per-input `d` explode into a multi-minute clip. Prescale the still 2× first to kill
   jitter.
3. **Join beats with XFADE crossfades** (`xfade=transition=fade:duration=0.45`, offsets auto-chained).
   `build_smooth.sh` does steps 2-3 from a `stills/` folder and prints the duration.
```bash
W=1320 H=2868 bash build_smooth.sh   # -> base_smooth.mp4 (edit the BEATS table for your storyboard)
```
Generic storyboard: start-action → input/pick → (short processing) → AI result → auto-filled form →
**the feature payoff (charts/analytics)** → more of it. Target 15-30 s (App Preview HARD limit). ALWAYS
montage the base and confirm every beat is present + smooth BEFORE overlaying.

*(Fallback — cut real clips: `scripts/build_base.sh` cuts the recordings with `-ss START -t DUR` BEFORE
`-i` — VFR breaks the `trim` filter — and concats. Only if a beat genuinely needs live motion throughout.)*

### D4. Overlay layer — captions + tap ripples + progress bar (one transparent PNG sequence, PIL)
Build a single RGBA overlay the length of the base and composite once. See `scripts/overlay_gen.py`.
- **Caption CHIP — high-contrast, BIG, always legible.** A bright-teal pill with white text **washes out**
  over the app's light screens (tested — "barely visible"). Use a **DARK glass chip** instead: near-black
  vertical gradient at ~94% opacity, a **mint→cyan accent underline bar**, **white bold** text with one
  **keyword tinted mint** (`*stars*`, LTR), a **strong drop shadow + a mint outer glow**, and a **slide-up +
  fade** entrance. Font **large** — ~88 px at 1320-wide (the old ~60 was too small); bidi-reorder RTL
  (`python-bidi get_display`). Dark-on-content is legible over BOTH light and dark app screens. **No emoji**
  (PIL renders them as tofu with a text TTF) — use words.
- **Tap ripples**: at each logged tap `(t, x_px, y_px)` (x_px = point×scale) a ~0.7 s **dual-colour** pulse —
  white expanding ring + accent halo + finger-core + white centre dot, ease-out. Visible on any background.
- **Progress bar**: a thin mint→cyan bar along the very bottom, filling L→R over the duration — a premium
  "guided tour" cue and gentle motion. (`progress:true` in the config.)
```bash
ffmpeg -i base_smooth.mp4 -framerate 30 -i ov/f%04d.png -filter_complex "[0][1]overlay=0:0[v]" -map "[v]" out_ov.mp4
```

### D5. Scale to preview px + **stereo audio** (required) + finalize
```bash
ffmpeg -i out_ov.mp4 -filter_complex "
 [0:v]scale=886:1920:flags=lanczos,setsar=1[v];
 anullsrc=r=44100:cl=stereo,atrim=0:DUR[s];
 sine=f=1046:d=0.11,afade=t=out:st=0:d=0.11,volume=0.26,adelay=T1|T1[p1]; /* …one soft tone per tap… */
 [s][p1..pN]amix=inputs=N+1:duration=longest:normalize=0,alimiter=limit=0.9[a]
" -map "[v]" -map "[a]" -t DUR -c:v libx264 -crf18 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 128k -ar 44100 -ac 2 -movflags +faststart preview.mp4
```
Synth **soft tap tones** synced to the ripples (an ascending motif over the taps) — reinforces "show the
clicks" and provides the mandatory audio without licensing music. Silent stereo is the safe fallback, but a
track MUST exist. Produce one preview per **platform × language × mode (light/dark)** — ASC accepts up to
3 previews per localization, so a light+dark pair per language is ideal (reuse the pipeline with each slot's px).

---

## Phase E — Upload to App Store Connect (ASC API)

Every upload is **reserve → chunked presigned PUT → commit**. JWT ES256 from the `.p8`. See
`scripts/asc_upload.py` (does screenshots and previews; reads the Config block).

```python
jwt.encode({'iss':ISS,'iat':now,'exp':now+1200,'aud':'appstoreconnect-v1'}, KEY,
           algorithm='ES256', headers={'kid':KID})
def req(url, method='GET', payload=None, raw=None, headers=None):
    h = {} if raw is not None else {'Authorization': f'Bearer {token()}'}   # ← NO auth on the presigned PUT
    ...
```

**Screenshots** (per locale × displayType):
1. `appStoreVersionLocalizations` for `ASC_VERSION_ID` → pick each `locale` id (he, en-US, …).
2. Find or create `appScreenshotSets` with `screenshotDisplayType = APP_IPHONE_67 | APP_IPAD_PRO_129 | APP_DESKTOP`.
3. `POST appScreenshots {fileName,fileSize, rel→set}` → returns `uploadOperations`.
4. For each op: PUT `blob[offset:offset+length]` to `op.url` with **only** `op.requestHeaders` (no Authorization).
5. `PATCH appScreenshots/{id} {uploaded:true, sourceFileChecksum: md5(blob)}`.
6. (Optional) order the set via `appScreenshotSets/{id}/relationships/appScreenshots`.

**App Previews** (per locale × previewType) — identical shape, different types:
- `appPreviewSets` `previewType = IPHONE_67 | IPAD_PRO_129 | DESKTOP`; `appPreviews` reserve/upload/commit.
- **Overwrite** = delete existing members first (`DELETE appPreviews/{id}`), then upload the new one.
- After commit, **poll** `appPreviews/{id}?fields[appPreviews]=assetDeliveryState` until `state=COMPLETE`
  (or `FAILED` + `errors`). `MOV_RESAVE_STEREO` ⇒ the video lacks stereo audio (fix D5, re-upload).

**Gotchas that cost real time:**
| Symptom | Cause | Fix |
|---|---|---|
| Preview stuck / `MOV_RESAVE_STEREO` | video has no/mono audio | add a stereo AAC track (D5), re-upload |
| Presigned PUT → 400 | sent `Authorization` on the S3 PUT | send only `op.requestHeaders` |
| `idb` tap/swipe no-op | pixel coords used as points, or y > device height | use points; y ≤ device-height |
| Wrong item picked in demo | picker slow, blind tap landed elsewhere | poll picker-ready (region std-dev) first |
| Clip missing / wrong length after cut | `trim` filter on VFR recording drops frames to ~0 | cut with `-ss START -t DUR` BEFORE `-i` (input seek) |
| Zoom clip is minutes long | `-t` used with `-loop 1` + zoompan (per-input `d` explodes) | bound output with `-frames:v N` (N=dur·30) |
| Commit/CTA tap doesn't fire | blind tap; button not at final position until fully scrolled | scroll-to-bottom → detect green CTA → tap → verify next screen |
| AI-parse recording times out / bloats | waited for the slow parse INSIDE the recording | record to the spinner, STOP; poll the result OUTSIDE any recording |
| Framed PNG is all-white | half-window + `scale-factor=2` (RTL body clipped) | full window + `--force-device-scale-factor=1` + `--virtual-time-budget=6000` |
| Caption barely visible on light screens | bright pill + light text | DARK glass chip + white text + accent underline + big font |
| Video looks janky | replaying in-app scroll/tap gestures | build from clean STILLS + Ken Burns + xfade (`build_smooth.sh`) |
| Caption reversed / tofu boxes | no bidi / emoji in PIL text | `python-bidi get_display`; words, not emoji |
| iPad/Mac shots tiny-font | app display size not maxed | set the app's LARGEST display size before iPad+Mac capture |
| System-Events rotate fails | Mac locked / Simulator not frontmost | use Method 2 (Info.plist force-landscape) |
| iPad screenshots all FAILED, `IMAGE_INCORRECT_DIMENSIONS` | shipped the M4 simulator's native 2064×2752 instead of ASC's required 2048×2732 | re-frame at 2048×2732 (Phase C `size` config), delete+re-upload |
| Video "freezes on one frame" / doesn't advance | a `zoompan`/xfade beat produced 1 real frame then held (loop math wrong, or an xfade offset ran past the shorter clip's duration so ffmpeg froze the last frame for the remainder) | montage the FULL base at `fps=1` (not `1/2`) across its whole duration and confirm every beat visibly changes frame-to-frame; verify each `xfade` `offset` < `min(clipA_dur, clipB_dur)` before the transition point |
| Debug sim build shows LogBox "Render Error" overlays (e.g. a navigation-context error on a tab that works fine in the real app) and requires a running Metro server | `-configuration Debug` builds load JS from Metro (port 8081) and surface dev-only LogBox render errors that do NOT reproduce in Release; marketing capture on a Debug build wastes hours chasing phantom bugs | ALWAYS build the capture app with `-configuration Release` (`xcodebuild -sdk iphonesimulator -configuration Release CODE_SIGNING_ALLOWED=NO`) — bundle embeds, no Metro, no LogBox, and the render path matches the shipped app |
| App needs dark-mode screenshots but the theme toggle lives behind a crash-unsafe menu (Method 2) or the app ignores the system appearance | app persists an explicit theme preference (e.g. AsyncStorage `@<app>/theme` = plain string `light`/`dark`/`system`) that overrides `simctl ui appearance` | inject the theme straight into the AsyncStorage manifest.json (same technique as the session/language injection) and relaunch — no UI navigation needed |
| Tapping a hamburger/menu icon on the Method-2 landscape-forced sim "exits to the home screen" (Mac shots) | **not a coordinate bug — it's an app CRASH.** `UISupportedInterfaceOrientations~ipad` restricted to landscape-only (Method 2) makes `-[UIViewController __supportedInterfaceOrientations]` throw `NSException` → `EXC_CRASH`/`SIGABRT` the instant a React Native `<Modal>` (`RCTModalHostViewComponentView presentViewController:`) tries to present — because the modal's orientation-mask reconciliation with the landscape-restricted root fails. Visually indistinguishable from "exited to home screen" in the simulator; recalibrating tap coordinates never fixes it. Confirm via `~/Library/Logs/DiagnosticReports/<App>-*.ips` (not by re-guessing coordinates) | any nav that opens a `<Modal>` (hamburger drop-down, sheet, dialog) is off-limits under Method 2. Instead capture MORE Mac content via non-modal PUSH navigation (React Navigation stack push, e.g. tapping into a list item's detail screen) — that never calls `presentViewController` and is crash-safe under the same restricted Info.plist. Sibling apps (Salarix, Fundiva) never hit this because their nav is a bottom tab bar, not a hamburger→modal — they didn't solve it, they never triggered it |

---

## Definition of done — verify before reporting completion

**Never report "screenshots/video done" from an in-progress plan or a partial run's memory — always
re-query ASC directly**, because earlier partial runs (e.g. 4/10 curated as a first pass) are easy to
mistake for the finished set:
```
for each platform in {iPhone, iPad, Mac}:
  for each locale in {he, en-US}:
    screenshotSet.appScreenshots.count MUST == 10, ALL assetDeliveryState == COMPLETE
    (mix check) at least 3 of the 10 sourced from a "dark" raw file, at least 3 from "light"
    previewSet.appPreviews.count MUST == 1, assetDeliveryState == COMPLETE
    (video quality check) montage the delivered preview at fps=1 across its FULL duration —
    every sampled frame must differ from its neighbor; a run of identical frames == a frozen/stalled
    video, NOT acceptable even if assetDeliveryState says COMPLETE (Apple's processing check does not
    catch this — only a human/visual montage check does)
```
Anything short of this (missing count, FAILED state, or a frozen video) is unfinished work — fix it
before telling the user the asset pipeline is complete.

---

## End-to-end runbook (autonomous)

```
1. A  create+boot ASC-iphone, ASC-ipad, ASC-ipad-landscape; install PROD app; grant photos.
      make the landscape iPad landscape (Method 1 rotate, else Method 2 Info.plist).
2. B  for plat in iphone, ipad, ipad-landscape(→mac):
        for mode in dark,light:  for lang in CAPTION_LANGS:
          set appearance+language; drive to the hero screens; screenshot → raw/  (both appearances)
        curate to EXACTLY 10 per language (Dark+Light mix) — ASC max per localization.
3. C  frame the curated 10/lang/plat (Chrome HTML→PNG) → framed/ at exact ASC px (crop the Mac band).
      => 10 he + 10 en per platform = 20; iPhone+iPad+Mac = 60 framed screenshots.
4. D  inject fresh demo data; record (recflow=segA import + parse-wait OUTSIDE recording + segB review→form,
      then recresults=verified commit + segC results); montage-verify each; extract clean STILLS per beat;
      build_smooth (Ken Burns zin/zpan + xfade) → overlay(big dark chip caps + taps + progress) →
      scale to preview px + stereo → preview_<plat>_<lang>_<mode>.mp4
5. E  ASC: upload all framed screenshots (locale×displayType) + previews (locale×previewType);
      poll previews to COMPLETE.
6.    Report: counts uploaded, any FAILED states, the listing URL.
```
Produce previews per **platform × language × mode (light/dark)** — up to 3 per localization on ASC.
Scale to the ask: "just an iPhone He preview" → one D+E pass; "the full set" → the whole matrix.

## Files in this skill
- `scripts/frame.py` — HTML→PNG Canvas framing, **premium editorial** (deep glow bg + floating device +
  kicker/headline/`*accent*` caption; Mac-crop aware).
- `scripts/drive.py` — poll-driven simulator recorder (PIL screen detection, CTA-button finder, tap log).
- `scripts/recflow.py` — reference: segA (import→spinner) + parse-wait outside recording + segB (review→form).
- `scripts/recresults.py` — reference: scroll-to-bottom + VERIFIED commit, then record dashboard→analytics.
- `scripts/build_smooth.sh` — **PREFERRED** base builder: clean stills → Ken Burns zin/zpan → xfade crossfades.
- `scripts/build_base.sh` — fallback base builder: cut real clips with `-ss/-t` (VFR-safe) → concat.
- `scripts/overlay_gen.py` — **high-contrast dark chip** captions (big font, RTL via bidi, `*keyword*` tint)
  + tap-ripple + progress-bar overlay generator.
- `scripts/asc_upload.py` — ASC screenshots + previews upload (JWT ES256, presigned PUT, poll to COMPLETE).

Every script reads the **Config block** env vars and takes CLI args — no app-specific values are baked in.
`recflow.py`/`recresults.py` carry Salarix-calibrated coordinates as a concrete reference — recalibrate the
tap points + `SCALE` (3 for iPhone/most iPad, 2 for some iPad) per app/device.
