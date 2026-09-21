#!/usr/bin/env python3
# Regenerate ALL App Store marketing screenshots from the archived raw captures in
# screenshots/_raw/. Brand frame + 2-line caption (main + blue accent), theme
# auto-matched per capture (dark shot -> dark frame; light shot -> light frame),
# Hebrew rendered RTL via headless Chrome. Run: python3 appstore/frame.py
#
# Self-contained: sources in _raw/{iphone,ipad}/<slug>.png, outputs overwrite
# screenshots/<device>/<lang>/<slug>.png.
import base64, html, subprocess, os

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'screenshots', '_raw')
OUTROOT = os.path.join(ROOT, 'screenshots')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
MAGICK = 'magick'

# slug -> (en main, en accent, he main, he accent)
CAPS = {
    '1-dashboard': ('Your whole home network', 'at a glance', 'כל הרשת הביתית', 'במבט אחד'),
    '2-scan':      ('Watch every device', 'appear live', 'כל מכשיר מופיע', 'בזמן אמת'),
    '3-ipmap':     ('Every IP address', 'used or free', 'כל כתובת IP', 'תפוסה או פנויה'),
    '4-insights':  ('Smart insights tell you', 'what to fix', 'תובנות חכמות', 'אומרות מה לתקן'),
    '5-tool':      ('Guided tools that', 'do the work', 'כלים מודרכים', 'שעושים את העבודה'),
    '6-device':    ('Ping, wake &', 'manage any device', 'Ping, השכמה', 'וניהול לכל מכשיר'),
}
SLUGS = list(CAPS.keys())

# device -> layout. src = which _raw folder; shot sized by width (portrait) or height (landscape).
DEVICES = {
    'iphone-6.9': dict(src='iphone', W=1320, H=2868, capfont=66, captop=158, capw=1200,
                       shottop=470, shotdim='width:1056px', glowtop=-260, glowsize='1500px;height:900px'),
    'ipad-13':    dict(src='ipad', W=2752, H=2064, capfont=82, captop=104, capw=2300,
                       shottop=400, shotdim='height:1500px', glowtop=-360, glowsize='2300px;height:1200px'),
    'mac':        dict(src='ipad', W=2880, H=1800, capfont=80, captop=92, capw=2400,
                       shottop=360, shotdim='height:1340px', glowtop=-380, glowsize='2400px;height:1200px'),
}

DARK = dict(bg='linear-gradient(155deg,#1c1c42 0%,#111028 45%,#08080f 100%)',
            glow='rgba(91,156,255,.30)', l1='#ffffff', l2='#5b9cff',
            shadow='0 48px 130px rgba(0,0,0,.6)', border='rgba(255,255,255,.09)')
LIGHT = dict(bg='linear-gradient(155deg,#eef2fb 0%,#e4eaf6 50%,#dbe3f3 100%)',
             glow='rgba(59,130,246,.16)', l1='#101a3d', l2='#2f6fed',
             shadow='0 44px 120px rgba(40,60,120,.30)', border='rgba(20,30,70,.10)')

def is_light(path):
    try:
        out = subprocess.run([MAGICK, path, '-resize', '1x1!', '-format', '%[fx:mean]', 'info:'],
                             capture_output=True, text=True).stdout.strip()
        return float(out) > 0.5
    except Exception:
        return False

TPL = '''<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden}}
  body{{background:{bg};font-family:-apple-system,"SF Pro Display","Helvetica Neue",Arial,sans-serif;position:relative}}
  .glow{{position:absolute;top:{glowtop}px;left:50%;transform:translateX(-50%);
        width:{glowsize};border-radius:50%;
        background:radial-gradient(closest-side,{glow},rgba(0,0,0,0));}}
  .cap{{position:absolute;top:{captop}px;left:{capleft}px;width:{capw}px;text-align:center;
       font-weight:800;line-height:1.14;letter-spacing:-1.4px;font-size:{capfont}px}}
  .cap .l1{{display:block;color:{l1};white-space:nowrap}}
  .cap .l2{{display:block;color:{l2};white-space:nowrap}}
  [dir=rtl] .cap{{font-family:-apple-system,"SF Hebrew","Arial Hebrew",Arial,sans-serif}}
  .shotwrap{{position:absolute;top:{shottop}px;left:50%;transform:translateX(-50%);}}
  .shot{{{shotdim};display:block;border-radius:46px;box-shadow:{shadow};border:1px solid {border}}}
</style></head>
<body dir="{dir}">
  <div class="glow"></div>
  <div class="cap"><span class="l1">{cl1}</span><span class="l2">{cl2}</span></div>
  <div class="shotwrap"><img class="shot" src="data:image/png;base64,{b64}"/></div>
</body></html>'''

def render(device, cfg, slug, lang, l1, l2):
    src = os.path.join(RAW, cfg['src'], f'{slug}.png')
    theme = LIGHT if is_light(src) else DARK
    with open(src, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    htmlstr = TPL.format(dir=('rtl' if lang == 'he' else 'ltr'),
                         cl1=html.escape(l1), cl2=html.escape(l2), b64=b64,
                         capleft=(cfg['W'] - cfg['capw']) // 2, **cfg, **theme)
    outdir = os.path.join(OUTROOT, device, lang)
    os.makedirs(outdir, exist_ok=True)
    htmlpath = os.path.join(outdir, f'_{slug}.html')
    outpng = os.path.join(outdir, f'{slug}.png')
    with open(htmlpath, 'w') as f:
        f.write(htmlstr)
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--force-device-scale-factor=1', f'--window-size={cfg["W"]},{cfg["H"]}',
                    f'--screenshot={outpng}', f'file://{htmlpath}'], check=True, capture_output=True)
    os.remove(htmlpath)
    return ('light' if theme is LIGHT else 'dark')

if __name__ == '__main__':
    for device, cfg in DEVICES.items():
        for slug in SLUGS:
            en1, en2, he1, he2 = CAPS[slug]
            t = render(device, cfg, slug, 'en', en1, en2)
            render(device, cfg, slug, 'he', he1, he2)
            print(f'{device}/{slug} [{t}]')
    print('done — all sets regenerated from _raw/')
