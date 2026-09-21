#!/usr/bin/env python3
"""Robust iPhone recorder — decouples the SLOW AI parse from the recordings.
segA: dash->add->picker->select->analyzing(short). Then WAIT for review OUTSIDE any recording.
segB: result-screen->use-data->form->scroll->add->home->feature/analytics.
Assumes app ON HOME/DASHBOARD, newest photo = the target input image the import flow consumes.
REFERENCE recorder: the tap coordinates + the UDID default below are app/device-specific. RECALIBRATE the
taps per screen and pass UDID=... each run. SCALE = 3 (iPhone/most iPad) / 2 (some iPad) affects find_green.
Usage: UDID=... python3 recflow.py <tag>  -> s1_<tag>.mp4 (import) + s2_<tag>.mp4 (results)"""
import os, sys, time, subprocess, statistics
from PIL import Image
D=os.environ.get("UDID","<SET-UDID-ENV>"); TAG=sys.argv[1]   # override: UDID=<sim udid> python3 recflow.py …
WORK=os.path.dirname(os.path.abspath(__file__))
POLL=f"{WORK}/_p_{TAG}.png"; LOG=[]; T0=None
def run(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
def tap(x,y): run(f"idb ui tap {x} {y} --udid {D}")
def swipe(a,b,c,d,dur=0.5): run(f"idb ui swipe {a} {b} {c} {d} --duration {dur} --udid {D}")
def now(): return time.time()-T0
def logt(l,x=None,y=None): LOG.append((l,x,y,round(now(),2))); print(f"  t={now():5.2f} {l}"+(f" ({x},{y})" if x is not None else ""))
def shot(): run(f"xcrun simctl io {D} screenshot {POLL}"); return Image.open(POLL).convert("RGB")
def std(im,box): return statistics.pstdev(list(im.crop(box).convert("L").getdata()))
def find_green(im):
    W,H=im.size; px=im.load(); by,bc,bx=None,0,None
    for y in range(int(H*0.30),H-40,4):
        xs=[x for x in range(30,W-30,6) if (lambda r,g,b: r<95 and g>150 and 80<b<185 and g-r>80 and g-b>25)(*px[x,y])]
        if len(xs)>bc: bc,by,bx=len(xs),y,xs
    return None if by is None or bc<60 else ((min(bx)+max(bx))//2//3, by//3)
def hero_green(im):
    p=list(im.crop((60,400,1260,760)).getdata()); n=len(p)
    return (sum(q[1] for q in p)/n)>110 and (sum(q[1] for q in p)/n-sum(q[0] for q in p)/n)>25
def poll(cond,to,label,iv=1.0):
    t=time.time(); last=None
    while time.time()-t<to:
        im=shot(); ok,info=cond(im); last=info
        if ok: print(f"    [{label}] {info} {time.time()-t:.1f}s"); return im
        time.sleep(iv)
    print(f"    [{label}] TIMEOUT {last}"); return shot()
GRID=(30,1380,1290,2450)
def rec(path): return subprocess.Popen(f"xcrun simctl io {D} recordVideo --codec h264 --force {path}",shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def stop(p): time.sleep(0.4); p.send_signal(2); time.sleep(3)

def main():
    global T0
    # ---- SEG A: dash -> add -> picker -> select -> analyzing (short, no parse wait inside) ----
    p=rec(f"{WORK}/s1_{TAG}.mp4"); T0=time.time(); time.sleep(2.4); logt("dash")
    tap(219,894); logt("+",219,894); time.sleep(2.7)
    tap(322,379); logt("gallery",322,379); time.sleep(1.0)
    poll(lambda im:(std(im,GRID)>42,f"std={std(im,GRID):.0f}"),28,"picker")
    time.sleep(0.5); tap(77,203); logt("select",77,203)
    poll(lambda im:(std(im,GRID)<34,f"std={std(im,GRID):.0f}"),12,"picker-close",0.7)
    time.sleep(3.0); logt("analyzing")
    stop(p); print(f"  seg1 -> s1_{TAG}.mp4")
    # ---- WAIT for review OUTSIDE any recording (parse can take 40s+) ----
    print("  waiting for review (parse)...")
    poll(lambda im:(find_green(im) is not None,"green"),90,"review-ready",1.5)
    # ---- SEG B: review -> use-data -> form -> scroll -> add -> dashboard -> analytics -> charts ----
    p=rec(f"{WORK}/s2_{TAG}.mp4"); T0=time.time(); time.sleep(2.0); logt("review")
    btn=find_green(shot()); (tap(*btn),logt("use-data",*btn)) if btn else (tap(220,706),logt("use-data FB",220,706))
    time.sleep(3.0)
    for _ in range(5): swipe(220,770,220,240); time.sleep(0.6)   # 5 scrolls -> fully at bottom
    logt("form-scrolled"); time.sleep(0.6)
    tap(220,839); logt("add",220,839)   # button sits at (220,839) when fully scrolled — fixed tap is reliable
    poll(lambda im:(hero_green(im),"hero"),16,"dashboard"); logt("on-dash"); time.sleep(2.4)
    tap(350,884); logt("analytics",350,884); time.sleep(3.0); logt("on-analytics"); time.sleep(1.6)
    swipe(220,780,220,300,0.7); logt("scroll1"); time.sleep(2.6)
    swipe(220,780,220,360,0.7); logt("scroll2"); time.sleep(2.4)
    stop(p); print(f"  seg2 -> s2_{TAG}.mp4")
    print("=== LOG ==="); [print(l) for l in LOG]

main()
