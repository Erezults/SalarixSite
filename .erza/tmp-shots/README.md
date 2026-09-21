# App Store assets

Marketing screenshots for HomeNetIP — simulator captures composited with a brand
frame + caption. Frame theme auto-matches each capture (dark shot → dark frame +
light caption; light shot → light frame + dark caption). Hebrew renders RTL.

## Live on App Store Connect (source of truth)

The **full marketing matrix is uploaded to ASC and verified COMPLETE** on the
1.7.0 versions (iOS + macOS), per the `erez-pics-video-canvas-asc` skill:

- **Screenshots — 10 per locale per platform** (60 total), dark/light mix,
  exact slot resolutions: iPhone 6.9" 1320×2868 (`APP_IPHONE_67`),
  iPad 2048×2732 (`APP_IPAD_PRO_129` — the legacy 12.9" spec ASC requires,
  NOT the M4 simulator's native 2064×2752), Mac 2880×1800 (`APP_DESKTOP`).
  Screens: dashboard · device view · insights · IP map · network scan ·
  settings · categories · rooms · export · add device.
- **App Previews — 6 videos** (iPhone/iPad/Mac × he/en), 17 s each, stereo AAC,
  captions + tap ripples + progress bar; motion verified frame-by-frame
  (fps=1 montage — no frozen segments).

Verify anytime (read-only):

```bash
ASC_API_KEY_ID=… ASC_API_KEY_ISSUER_ID=… node scripts/asc-assets-audit.mjs 1.7.0   # counts + delivery states
ASC_API_KEY_ID=… ASC_API_KEY_ISSUER_ID=… node scripts/asc-assets-verify.mjs        # fileNames + download URLs (JSON)
```

The uploaded masters are downloadable via `asc-assets-verify.mjs` output URLs
(screenshots at full resolution; previews via their HLS `videoUrl`), so the
heavy binaries are intentionally NOT committed here.

## Archived local sets (earlier 6-shot pass)

- `screenshots/iphone-6.9/{en,he}/` — 1320×2868
- `screenshots/ipad-13/{en,he}/`    — 2752×2064 (pre-dates the 2048×2732 requirement)
- `screenshots/mac/{en,he}/`        — 2880×1800

`en/` → en-US locale · `he/` → Hebrew locale.
PNGs are RGB / no alpha / sRGB / 72dpi (App Store compliant).

## Regenerate

- Raw captures: `ios/ASCUITests/ASCUITests.swift` is the reusable marketing-capture
  tour (EN/HE, dark/light, iPad huge-text, Mac landscape).
- Framing: `screenshots/_raw/{iphone,ipad}/<slug>.png` are archived source captures;
  `python3 appstore/frame.py` rebuilds the local sets (headless Chrome for correct
  Hebrew RTL). Edit captions in `CAPS` / layout in `DEVICES`.
- Full pipeline (sims → capture → frame → video → upload):
  `~/.claude/skills/erez-pics-video-canvas-asc/SKILL.md`.
