#!/usr/bin/env python3
"""
PREMIUM Canvas framer: composite a raw simulator screenshot into a distinctive editorial-fintech frame
— a deep atmospheric background (layered accent glows + dot-grid), a FLOATING device (rim + big shadow +
under-glow + gloss), and a big editorial caption (KICKER + HEADLINE with one *accent* keyword) — rendered
to the EXACT ASC px via Chrome headless. Handles RTL captions and the Mac crop (landscape-iPad band).
(A flat pale-gradient wash with a small caption reads as generic "AI slop" — this deliberately avoids that.)

Config JSON (argv[1]):
{
  "font": "/abs/Brand-ExtraBold.ttf",      # bold display TTF (base64-embedded so file:// renders offline)
  "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "work": "/tmp/asc_assets",
  "accent1": "#10B981", "accent2": "#34D3EE",  # accent gradient: kicker dot, *keyword*, glow, under-glow
  "ink": "#0A1420", "ink2": "#0F2634",         # deep atmospheric background base (NOT a pale wash)
  "brand": "MYAPP",                             # optional faint wordmark at the bottom ("" hides it)
  "items": [
    {"raw":"raw/iphone_he_dark_01.png", "kicker":"KICKER LABEL",
     "caption":"Big headline, *one word tinted*",   # *stars* -> mint→cyan gradient span
     "out":"framed/iphone_he_dark_01.png", "size":[1320,2868], "rtl":false},
    {"raw":"raw/mac_he_dark_01.png","caption":"…","kicker":"…","out":"framed/mac_he_dark_01.png",
     "size":[2880,1800],"rtl":true,"crop":[0,596,2064,2180]}   # landscape-iPad band -> Mac
  ]
}
Usage: python3 frame.py config.json
"""
import os, sys, json, base64, subprocess, html

C = json.load(open(sys.argv[1]))
WORK = C["work"]; CHROME = C["chrome"]
FONT_B64 = base64.b64encode(open(C["font"], "rb").read()).decode()
# Brand palette (override in config): a1->a2 = accent gradient (mint->cyan), ink = deep bg base.
A1 = C.get("accent1", "#10B981"); A2 = C.get("accent2", "#34D3EE")
INK = C.get("ink", "#0A1420"); INK2 = C.get("ink2", "#0F2634")
BRAND = C.get("brand", "")            # optional small wordmark in the corner
os.makedirs(os.path.join(WORK, "html"), exist_ok=True)
os.makedirs(os.path.join(WORK, "framed"), exist_ok=True)


def data_uri(path):
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def caption_html(text):
    """*keyword* -> mint-gradient accent span; everything else HTML-escaped."""
    return "".join(
        f'<span class="accent">{html.escape(p)}</span>' if i % 2 else html.escape(p)
        for i, p in enumerate(text.split("*")))


def render(item):
    raw = os.path.join(WORK, item["raw"])
    w, h = item["size"]
    rtl = item.get("rtl", False)
    landscape = w > h                                  # Mac/iPad-landscape frames
    if "crop" in item:
        from PIL import Image
        im = Image.open(raw).convert("RGB").crop(tuple(item["crop"]))
        raw2 = os.path.join(WORK, "html", "_crop.png"); im.save(raw2); src = raw2
    else:
        src = raw
    uri = data_uri(src)
    S = min(w, h)                                      # scale metric
    head_fs = int(S * (0.079 if not landscape else 0.060))   # big, legible headline
    kick_fs = int(head_fs * 0.30)
    rad = int(S * 0.028)
    kicker = item.get("kicker", "")
    align = "center"
    doc = f"""<!doctype html><html dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8"><style>
@font-face{{font-family:Brand;src:url(data:font/ttf;base64,{FONT_B64}) format('truetype');}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:{w}px;height:{h}px;font-family:Brand,sans-serif;position:relative;overflow:hidden;
  display:flex;flex-direction:column;align-items:center;
  background:
    radial-gradient(135% 95% at 16% -12%, rgba(16,185,129,.32), transparent 52%),
    radial-gradient(120% 85% at 96% 112%, rgba(34,211,238,.22), transparent 48%),
    linear-gradient(158deg, {INK} 0%, {INK2} 50%, {INK} 100%);}}
body::before{{content:"";position:absolute;inset:0;pointer-events:none;
  background-image:radial-gradient(rgba(255,255,255,.055) 1.5px, transparent 1.5px);
  background-size:{int(S*0.045)}px {int(S*0.045)}px;
  -webkit-mask:radial-gradient(95% 72% at 50% 38%, #000, transparent 76%);opacity:.7;}}
.cap{{z-index:3;text-align:{align};padding:{int(h*0.05)}px {int(w*0.055)}px {int(h*0.018)}px;width:100%;}}
.kicker{{font-size:{kick_fs}px;font-weight:800;letter-spacing:.26em;text-transform:uppercase;
  color:{A2};display:{'inline-flex' if kicker else 'none'};align-items:center;gap:.7em;margin-bottom:{int(head_fs*0.34)}px;}}
.kicker::before{{content:"";width:{int(kick_fs*0.7)}px;height:{int(kick_fs*0.7)}px;border-radius:50%;
  background:linear-gradient(120deg,{A1},{A2});box-shadow:0 0 {int(kick_fs)}px {A1};}}
.head{{font-size:{head_fs}px;font-weight:800;color:#EAF2F6;line-height:1.08;letter-spacing:-.01em;
  text-shadow:0 2px 30px rgba(0,0,0,.35);}}
.head .accent{{background:linear-gradient(96deg,{A1},{A2});-webkit-background-clip:text;background-clip:text;color:transparent;}}
.dev{{flex:1;position:relative;display:flex;align-items:center;justify-content:center;width:100%;
  padding:0 {int(w*(0.075 if not landscape else 0.05))}px {int(h*0.05)}px;}}
.dev::after{{content:"";position:absolute;width:72%;height:42%;left:14%;bottom:6%;z-index:0;
  background:radial-gradient(closest-side, rgba(16,185,129,.40), transparent);filter:blur({int(S*0.06)}px);}}
.shot{{position:relative;z-index:1;border-radius:{rad}px;max-width:100%;max-height:100%;
  box-shadow:0 0 0 2px rgba(255,255,255,.10), 0 {int(S*0.02)}px {int(S*0.06)}px rgba(0,0,0,.55),
    0 {int(S*0.004)}px {int(S*0.02)}px rgba(0,0,0,.4);}}
.shot img{{display:block;max-width:100%;max-height:{int(h*0.80)}px;object-fit:contain;border-radius:{rad}px;}}
.shot::before{{content:"";position:absolute;inset:0;border-radius:{rad}px;pointer-events:none;
  background:linear-gradient(180deg, rgba(255,255,255,.12), transparent 20%);}}
.brand{{position:absolute;bottom:{int(h*0.028)}px;left:0;right:0;text-align:center;z-index:3;
  font-size:{int(kick_fs*0.82)}px;font-weight:800;letter-spacing:.3em;text-transform:uppercase;
  color:rgba(255,255,255,.42);display:{'block' if BRAND else 'none'};}}
</style></head><body>
<div class="cap"><span class="kicker">{html.escape(kicker)}</span><div class="head">{caption_html(item['caption'])}</div></div>
<div class="dev"><div class="shot"><img src="{uri}"></div></div>
<div class="brand">{html.escape(BRAND)}</div>
</body></html>"""
    hp = os.path.join(WORK, "html", os.path.basename(item["out"]) + ".html")
    open(hp, "w").write(doc)
    out = os.path.join(WORK, item["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # body is authored at full target px -> window MUST be full size with scale-factor 1
    # (half-window + scale-factor 2 clips the body and, in RTL, screenshots a blank left edge).
    # virtual-time-budget lets the big base64 font+image decode before the capture.
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--virtual-time-budget=6000",
                    f"--screenshot={out}", f"--window-size={w},{h}", f"file://{hp}"],
                   capture_output=True)
    ok = os.path.exists(out)
    print(("  OK  " if ok else "  FAIL") + out)
    return ok


n = sum(render(it) for it in C["items"])
print(f"framed {n}/{len(C['items'])}")
