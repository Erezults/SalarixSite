#!/usr/bin/env python3
"""
Generic App Store Connect asset uploader — screenshots AND app previews.
No app-specific values are baked in; everything comes from env vars or CLI.

Env (see the skill's Config block):
  ASC_KEY   = path to AuthKey_<KID>.p8
  ASC_KID   = key id
  ASC_ISS   = issuer uuid
  ASC_VERSION_ID = appStoreVersion id to attach assets to

Usage:
  # screenshots: one displayType, one locale, N files (order = CLI order)
  ASC_* env set...
  python3 asc_upload.py screenshots --locale he --type APP_IPHONE_67 a.png b.png ...
  # preview: one previewType, one locale, one video (replaces the set's current members)
  python3 asc_upload.py preview --locale he --type IPHONE_67 --replace preview.mp4 --poll

displayType:  APP_IPHONE_67 | APP_IPAD_PRO_129 | APP_DESKTOP  (+ other Apple enums)
previewType:  IPHONE_67 | IPAD_PRO_129 | DESKTOP
"""
import os, sys, json, time, hashlib, argparse
import urllib.request, urllib.error
import jwt

KEY = open(os.environ["ASC_KEY"]).read()
KID = os.environ["ASC_KID"]; ISS = os.environ["ASC_ISS"]
VERSION_ID = os.environ["ASC_VERSION_ID"]
BASE = "https://api.appstoreconnect.apple.com/v1"


def token():
    now = int(time.time())
    return jwt.encode({"iss": ISS, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"},
                      KEY, algorithm="ES256", headers={"kid": KID})


def req(url, method="GET", payload=None, raw=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else raw
    # CRUCIAL: presigned S3 PUTs (raw is not None) must NOT carry an Authorization header.
    h = {} if raw is not None else {"Authorization": f"Bearer {token()}"}
    if payload is not None:
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        resp = urllib.request.urlopen(r)
        body = resp.read()
        return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read().decode()[:500]}")


def locale_id(locale):
    locs = req(f"{BASE}/appStoreVersions/{VERSION_ID}/appStoreVersionLocalizations"
               "?fields[appStoreVersionLocalizations]=locale&limit=50")
    for l in locs["data"]:
        if l["attributes"]["locale"] == locale:
            return l["id"]
    raise SystemExit(f"locale {locale} not found on version {VERSION_ID}")


def upload_blob(reserve_url, reserve_type, rel_type, rel_id, path):
    """reserve -> presigned chunked PUT -> commit. Returns the new asset id."""
    blob = open(path, "rb").read()
    res = req(f"{BASE}/{reserve_url}", "POST", {
        "data": {"type": reserve_type,
                 "attributes": {"fileName": os.path.basename(path), "fileSize": len(blob)},
                 "relationships": {rel_type: {"data": {"type": rel_type + "s", "id": rel_id}}}}})
    aid = res["data"]["id"]
    ops = res["data"]["attributes"]["uploadOperations"]
    print(f"  {os.path.basename(path)}: {len(ops)} chunk(s), {len(blob)//1024} KB")
    for op in ops:
        hdrs = {h["name"]: h["value"] for h in op["requestHeaders"]}
        req(op["url"], op["method"], raw=blob[op["offset"]:op["offset"] + op["length"]], headers=hdrs)
    req(f"{BASE}/{reserve_url}/{aid}", "PATCH", {
        "data": {"type": reserve_type, "id": aid,
                 "attributes": {"uploaded": True, "sourceFileChecksum": hashlib.md5(blob).hexdigest()}}})
    return aid


def get_or_create_set(kind, loc_id, type_value):
    """kind = 'appScreenshotSets'(screenshotDisplayType) | 'appPreviewSets'(previewType)."""
    attr = "screenshotDisplayType" if kind == "appScreenshotSets" else "previewType"
    sets = req(f"{BASE}/appStoreVersionLocalizations/{loc_id}/{kind}?fields[{kind}]={attr}&limit=50")
    for s in sets["data"]:
        if s["attributes"][attr] == type_value:
            return s["id"]
    created = req(f"{BASE}/{kind}", "POST", {
        "data": {"type": kind, "attributes": {attr: type_value},
                 "relationships": {"appStoreVersionLocalization": {
                     "data": {"type": "appStoreVersionLocalizations", "id": loc_id}}}}})
    return created["data"]["id"]


def clear_set(kind, set_id):
    member = "appScreenshots" if kind == "appScreenshotSets" else "appPreviews"
    ex = req(f"{BASE}/{kind}/{set_id}/{member}?limit=20")
    for p in ex["data"]:
        req(f"{BASE}/{member}/{p['id']}", "DELETE")
    if ex["data"]:
        print(f"  cleared {len(ex['data'])} existing {member}")


def poll_preview(pid, tries=30):
    for i in range(tries):
        d = req(f"{BASE}/appPreviews/{pid}?fields[appPreviews]=assetDeliveryState,fileName")["data"]["attributes"]
        st = d["assetDeliveryState"]; state = st.get("state")
        print(f"  [{i}] {d['fileName']} -> {state}  errors={st.get('errors')}")
        if state in ("COMPLETE", "FAILED"):
            return state
        time.sleep(12)
    return "TIMEOUT"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["screenshots", "preview"])
    ap.add_argument("--locale", required=True)
    ap.add_argument("--type", required=True, help="displayType or previewType enum")
    ap.add_argument("--replace", action="store_true", help="delete current set members first")
    ap.add_argument("--poll", action="store_true", help="poll preview to COMPLETE")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    loc = locale_id(a.locale)
    if a.mode == "screenshots":
        set_id = get_or_create_set("appScreenshotSets", loc, a.type)
        if a.replace:
            clear_set("appScreenshotSets", set_id)
        print(f"appScreenshotSet {set_id} ({a.type}, {a.locale})")
        for f in a.files:
            upload_blob("appScreenshots", "appScreenshots", "appScreenshotSet", set_id, f)
        print("screenshots uploaded.")
    else:
        set_id = get_or_create_set("appPreviewSets", loc, a.type)
        if a.replace:
            clear_set("appPreviewSets", set_id)
        print(f"appPreviewSet {set_id} ({a.type}, {a.locale})")
        pid = upload_blob("appPreviews", "appPreviews", "appPreviewSet", set_id, a.files[0])
        print("preview uploaded — Apple is processing.")
        if a.poll:
            print(poll_preview(pid))


if __name__ == "__main__":
    main()
