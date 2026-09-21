#!/usr/bin/env python3
"""
Generic transparent-overlay generator for App-Preview videos:
HIGH-CONTRAST marketing caption chips (any language, RTL-aware) + animated tap-ripple indicators
+ a thin bottom progress bar. Outputs an RGBA PNG sequence you composite onto the base video.

Design: a DARK glass chip (near-black vertical gradient, ~94% opaque) with a bright mint accent
underline, white bold text, a strong drop shadow AND a mint outer glow. Dark-on-content guarantees
legibility over BOTH light and dark app screens (the old bright-teal-on-white pill washed out).
Captions slide up + fade in.

Config JSON (path as argv[1]):
{
  "size": [1320, 2868], "fps": 30, "duration": 25.2,
  "font": "/abs/Brand-ExtraBold.ttf", "font_size": 66, "rtl": true,
  "pill": {"c0":[14,165,160], "c1":[34,211,238], "text":[255,255,255]},  # c0->c1 = accent gradient
  "cap_cy": 300,                 # caption chip centre-y (px)
  "progress": true,              # thin mint progress bar at the very bottom
  "out": "/abs/ov",
  "captions": [[start,end,"text"], ...],   # wrap a keyword in *stars* to tint it mint (LTR only)
  "taps": [[t, x_px, y_px], ...]
}
Usage: python3 overlay_gen.py config.json
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    from bidi.algorithm import get_display
except Exception:
    try:
        from bidi import get_display
    except Exception:
        def get_display(s): return s

C = json.load(open(sys.argv[1]))
W, H = C["size"]; FPS = C["fps"]; DUR = C["duration"]
NF = int(DUR * FPS) + 1
OUT = C["out"]; os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
FS = C.get("font_size", 84)          # BIG by default — small captions read as generic/unclear
font = ImageFont.truetype(C["font"], FS)
RTL = C.get("rtl", False)
P = C.get("pill", {"c0": [14, 165, 160], "c1": [34, 211, 238], "text": [255, 255, 255]})
CAP_CY = C.get("cap_cy", 300)
SHOW_PROG = C.get("progress", True)
C0, C1 = tuple(P["c0"]), tuple(P["c1"])
def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_chip(text):
    """Dark high-contrast chip with mint accent underline + shadow + mint glow. Returns (img, pad)."""
    disp = get_display(text.replace("*", "")) if RTL else text.replace("*", "")
    tmp = Image.new("RGBA", (10, 10)); d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), disp, font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    padx, padtop, padbot = 74, 42, 54          # extra bottom room for the accent bar
    pw, ph = tw + 2 * padx, th + padtop + padbot
    # dark vertical-gradient body
    chip = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); cp = chip.load()
    top, bot = (22, 43, 58), (9, 20, 29)        # #162B3A -> #09141D
    for y in range(ph):
        col = lerp(top, bot, y / max(1, ph - 1)) + (240,)
        for x in range(pw):
            cp[x, y] = col
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=255)
    chip.putalpha(mask)
    dd = ImageDraw.Draw(chip)
    dd.rounded_rectangle([1, 1, pw - 2, ph - 2], radius=ph // 2, outline=(255, 255, 255, 34), width=2)
    # keyword tint (LTR only): *word* -> mint
    if not RTL and "*" in text:
        segs = text.split("*"); x = padx - bb[0]; base = padtop - bb[1]
        for i, s in enumerate(segs):
            if not s:
                continue
            col = lerp(C0, C1, 0.6) + (255,) if i % 2 else tuple(P["text"]) + (255,)
            dd.text((x, base), s, font=font, fill=col)
            x += dd.textlength(s, font=font)
    else:
        dd.text((padx - bb[0], padtop - bb[1]), disp, font=font, fill=tuple(P["text"]) + (255,))
    # mint accent underline bar (rounded), centred near bottom
    bar_w, bh = int(pw * 0.30), 9
    bx0, by = (pw - bar_w) // 2, ph - padbot + 20
    bar = Image.new("RGBA", (bar_w, bh), (0, 0, 0, 0)); bl = bar.load()
    for x in range(bar_w):
        c = lerp(C0, C1, x / max(1, bar_w - 1))
        for y in range(bh):
            bl[x, y] = c + (255,)
    bm = Image.new("L", (bar_w, bh), 0)
    ImageDraw.Draw(bm).rounded_rectangle([0, 0, bar_w - 1, bh - 1], radius=bh // 2, fill=255)
    bar.putalpha(bm); chip.alpha_composite(bar, (bx0, by))
    # compose: mint glow + dark shadow + chip
    pad = 110
    canvas = Image.new("RGBA", (pw + 2 * pad, ph + 2 * pad), (0, 0, 0, 0))
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([pad, pad + 6, pad + pw, pad + ph + 6], radius=ph // 2,
                                           fill=(C1[0], C1[1], C1[2], 78))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(42)))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 18, pad + pw, pad + ph + 18], radius=ph // 2,
                                         fill=(2, 9, 14, 205))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(28)))
    canvas.alpha_composite(chip, (pad, pad))
    return canvas, pad


chips = [(s, e, *make_chip(t)) for (s, e, t) in C["captions"]]
TAPS = C["taps"]


def ripple_layer(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for (tt, x, y) in TAPS:
        p = (t - tt) / 0.70
        if p < 0 or p > 1:
            continue
        rr = int(36 + 105 * (1 - (1 - p) ** 2))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 255, 255, int(235 * (1 - p))),
                  width=max(2, int(12 * (1 - p))))
        d.ellipse([x - rr - 6, y - rr - 6, x + rr + 6, y + rr + 6],
                  outline=(C0[0], C0[1], C0[2], int(205 * (1 - p))), width=max(1, int(6 * (1 - p))))
        cr = int(48 * (1 - 0.35 * p))
        d.ellipse([x - cr, y - cr, x + cr, y + cr], fill=(C1[0], C1[1], C1[2], int(150 * (1 - 0.85 * p))))
        d.ellipse([x - cr, y - cr, x + cr, y + cr], outline=(255, 255, 255, int(225 * (1 - p))), width=6)
        wr = int(19 * (1 - 0.3 * p))
        d.ellipse([x - wr, y - wr, x + wr, y + wr], fill=(255, 255, 255, int(235 * (1 - p))))
    return layer


def progress_bar(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    pb_h, m, y0 = 9, 44, H - 15
    d.rounded_rectangle([m, y0, W - m, y0 + pb_h], radius=pb_h // 2, fill=(255, 255, 255, 45))
    fw = int((W - 2 * m) * min(1.0, t / DUR))
    if fw > pb_h:
        bar = Image.new("RGBA", (fw, pb_h), (0, 0, 0, 0)); bl = bar.load()
        for x in range(fw):
            c = lerp(C0, C1, min(1.0, x / max(1, (W - 2 * m) - 1) * 1.25))
            for y in range(pb_h):
                bl[x, y] = c + (255,)
        bm = Image.new("L", (fw, pb_h), 0)
        ImageDraw.Draw(bm).rounded_rectangle([0, 0, fw - 1, pb_h - 1], radius=pb_h // 2, fill=255)
        bar.putalpha(bm); layer.alpha_composite(bar, (m, y0))
    return layer


print(f"generating {NF} overlay frames -> {OUT}")
for f in range(NF):
    t = f / FPS
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for (s, e, chip, pad) in chips:
        if s <= t < e:
            fade = max(0.0, min(1.0, (t - s) / 0.34, (e - t) / 0.30))
            if fade > 0:
                cw, ch = chip.size
                rise = int(34 * (1 - min(1.0, (t - s) / 0.34)) ** 2)   # slide-up entrance
                px = (W - cw) // 2; py = CAP_CY - ch // 2 + rise
                if fade < 1.0:
                    a = chip.split()[3].point(lambda v: int(v * fade))
                    pc = chip.copy(); pc.putalpha(a); fr.alpha_composite(pc, (px, py))
                else:
                    fr.alpha_composite(chip, (px, py))
            break
    fr = Image.alpha_composite(fr, ripple_layer(t))
    if SHOW_PROG:
        fr = Image.alpha_composite(fr, progress_bar(t))
    fr.save(f"{OUT}/f{f:04d}.png")
    if f % 120 == 0:
        print(f"  {f}/{NF}")
print("done", NF, "frames")
