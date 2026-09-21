#!/usr/bin/env python3
"""Reliable COMMIT + results recorder. Assumes app is ON THE FORM (any scroll).
Scrolls to bottom, taps the detected primary CTA button, VERIFIES the home/hero appeared, then records
s3_<tag>.mp4 = home/dashboard -> feature/analytics. REFERENCE recorder — recalibrate the green-detect
thresholds + fallback tap for your app; pass UDID=... each run.
Usage: UDID=... python3 recresults.py <tag>"""
import os, sys, time, subprocess
from PIL import Image
D=os.environ.get("UDID","<SET-UDID-ENV>"); TAG=sys.argv[1]   # override: UDID=<sim udid> python3 recresults.py …
W=os.path.dirname(os.path.abspath(__file__)); POLL=f"{W}/_r_{TAG}.png"
def run(c): subprocess.run(c,shell=True,capture_output=True)
def tap(x,y): run(f"idb ui tap {x} {y} --udid {D}")
def sw(a,b,c,d,dur=0.45): run(f"idb ui swipe {a} {b} {c} {d} --duration {dur} --udid {D}")
def shot(): run(f"xcrun simctl io {D} screenshot {POLL}"); return Image.open(POLL).convert("RGB")
def find_green(im):
    Wd,H=im.size; px=im.load(); by,bc,bx=None,0,None
    for y in range(int(H*0.30),H-30,3):
        xs=[x for x in range(30,Wd-30,5) if (lambda r,g,b: r<95 and g>150 and 80<b<185 and g-r>80 and g-b>25)(*px[x,y])]
        if len(xs)>bc: bc,by,bx=len(xs),y,xs
    return None if by is None or bc<80 else ((min(bx)+max(bx))//2//3, by//3)
def hero(im):
    p=list(im.crop((60,400,1260,760)).getdata()); n=len(p)
    return sum(q[1] for q in p)/n>90 and sum(q[1] for q in p)/n-sum(q[0] for q in p)/n>22

# 1) scroll to bottom, commit
for _ in range(6): sw(220,700,220,250); time.sleep(0.45)
time.sleep(0.7)
b=find_green(shot()); b=b or (220,839)
print("add button ->", b); tap(*b)
t=time.time(); ok=False
while time.time()-t<16:
    if hero(shot()): ok=True; print(f"DASHBOARD at {time.time()-t:.1f}s"); break
    time.sleep(1)
if not ok:
    print("COMMIT FAILED — still not on dashboard"); sys.exit(1)
time.sleep(1.5)
# 2) record results
p=subprocess.Popen(f"xcrun simctl io {D} recordVideo --codec h264 --force {W}/s3_{TAG}.mp4",shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(2.6); print("dash")
tap(350,884); print("analytics"); time.sleep(3.4)
sw(220,780,220,300,0.6); time.sleep(2.8); print("scroll1")
sw(220,780,220,360,0.6); time.sleep(2.6); print("scroll2")
time.sleep(0.4); p.send_signal(2); time.sleep(3)
print("s3 dur:", subprocess.run(f"ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 {W}/s3_{TAG}.mp4",shell=True,capture_output=True,text=True).stdout.strip())
