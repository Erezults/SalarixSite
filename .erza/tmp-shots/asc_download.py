#!/usr/bin/env python3
"""READ-ONLY: download all APP_IPHONE_67 screenshots (en-US + he) of the iOS 1.3.0 version."""
import os, json, time, urllib.request, jwt

KEY = open(os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_5K587S6Q67.p8")).read()
KID, ISS = "5K587S6Q67", "a38867d2-7e7e-46c3-9ff8-c606a096a5a7"
BASE = "https://api.appstoreconnect.apple.com/v1"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asc")

def tok():
    now = int(time.time())
    return jwt.encode({"iss": ISS, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"}, KEY,
                      algorithm="ES256", headers={"kid": KID})

def get(url):
    r = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok()}"})
    return json.loads(urllib.request.urlopen(r).read())

VERSION = "3950bacd-3950-4822-bae7-43dacb932065"  # IOS 1.3.0
locs = get(f"{BASE}/appStoreVersions/{VERSION}/appStoreVersionLocalizations?limit=10")
for l in locs["data"]:
    loc = l["attributes"]["locale"]
    lang = "en" if loc.startswith("en") else "he"
    sets = get(f'{BASE}/appStoreVersionLocalizations/{l["id"]}/appScreenshotSets?limit=20')
    for s in sets["data"]:
        if s["attributes"]["screenshotDisplayType"] != "APP_IPHONE_67":
            continue
        shots = get(f'{BASE}/appScreenshotSets/{s["id"]}/appScreenshots?limit=20')
        d = os.path.join(OUT, lang)
        os.makedirs(d, exist_ok=True)
        for sh in shots["data"]:
            at = sh["attributes"]
            asset = at["imageAsset"]
            url = asset["templateUrl"].replace("{w}", str(asset["width"])).replace("{h}", str(asset["height"])).replace("{f}", "png")
            dest = os.path.join(d, at["fileName"])
            urllib.request.urlretrieve(url, dest)
            print(f"{lang}/{at['fileName']} downloaded")
print("done")
