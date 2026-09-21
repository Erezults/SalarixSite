#!/usr/bin/env python3
"""READ-ONLY: list App Store screenshot sets + download URLs for a Salarix app version."""
import os, json, time, urllib.request, jwt, sys

KEY = open(os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_5K587S6Q67.p8")).read()
KID, ISS = "5K587S6Q67", "a38867d2-7e7e-46c3-9ff8-c606a096a5a7"
APP = sys.argv[1] if len(sys.argv) > 1 else "6783344327"
BASE = "https://api.appstoreconnect.apple.com/v1"

def tok():
    now = int(time.time())
    return jwt.encode({"iss": ISS, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"}, KEY,
                      algorithm="ES256", headers={"kid": KID})

def get(url):
    r = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok()}"})
    return json.loads(urllib.request.urlopen(r).read())

vers = get(f"{BASE}/apps/{APP}/appStoreVersions?limit=5&fields[appStoreVersions]=versionString,platform,appStoreState")
for v in vers["data"]:
    a = v["attributes"]
    print(f'VERSION {v["id"]} {a["platform"]} {a["versionString"]} {a["appStoreState"]}')
    locs = get(f'{BASE}/appStoreVersions/{v["id"]}/appStoreVersionLocalizations?limit=10')
    for l in locs["data"]:
        lid, loc = l["id"], l["attributes"]["locale"]
        sets = get(f"{BASE}/appStoreVersionLocalizations/{lid}/appScreenshotSets?limit=20")
        for s in sets["data"]:
            dt = s["attributes"]["screenshotDisplayType"]
            shots = get(f'{BASE}/appScreenshotSets/{s["id"]}/appScreenshots?limit=20')
            print(f"  {loc} {dt}: {len(shots['data'])} shots")
            for sh in shots["data"]:
                at = sh["attributes"]
                tmpl = (at.get("imageAsset") or {}).get("templateUrl", "")
                w = (at.get("imageAsset") or {}).get("width")
                h = (at.get("imageAsset") or {}).get("height")
                print(f"    {at['fileName']} {w}x{h} {at['assetDeliveryState']['state']} {tmpl}")
