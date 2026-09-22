"""Real-time frame capture of the LIVE swap UI (?auto=demo) via headless Chrome CDP, then ffmpeg (concat with true
frame durations). Every number in the video is measured during the capture; nothing is staged."""
import json, os, subprocess, sys, time, base64, urllib.request, websocket
HERE=os.path.dirname(os.path.abspath(__file__)); FR=f"{HERE}/_frames"; PROF="/tmp/chromeprof_kev"; PORT=9227
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; URL="http://127.0.0.1:8787/?auto=demo"
OUT=sys.argv[1] if len(sys.argv)>1 else f"{HERE}/kev_swap_demo.mp4"; W,H=1280,960; MAXS=60
subprocess.run(["rm","-rf",FR]); os.makedirs(FR)
proc=subprocess.Popen([CH,"--headless=new",f"--remote-debugging-port={PORT}",f"--user-data-dir={PROF}",f"--window-size={W},{H}","--hide-scrollbars","--force-device-scale-factor=1","--remote-allow-origins=*","about:blank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: page=next(t for t in json.load(urllib.request.urlopen(f"http://localhost:{PORT}/json/list",timeout=1)) if t["type"]=="page"); break
        except Exception: time.sleep(0.5)
    ws=websocket.create_connection(page["webSocketDebuggerUrl"],timeout=30); mid=[0]
    def cmd(m,p=None):
        mid[0]+=1; ws.send(json.dumps({"id":mid[0],"method":m,"params":p or {}}))
        while True:
            r=json.loads(ws.recv())
            if r.get("id")==mid[0]: return r.get("result",{})
    cmd("Page.enable"); cmd("Emulation.setDeviceMetricsOverride",{"width":W,"height":H,"deviceScaleFactor":1,"mobile":False}); cmd("Page.navigate",{"url":URL}); time.sleep(1.0)
    t0=time.time(); ts=[]; i=0
    while time.time()-t0<MAXS:
        shot=cmd("Page.captureScreenshot",{"format":"png"})
        if "data" not in shot: time.sleep(0.2); continue
        open(f"{FR}/f_{i:04d}.png","wb").write(base64.b64decode(shot["data"])); ts.append(time.time()-t0); i+=1
        done=cmd("Runtime.evaluate",{"expression":"!!window.__demo_done"}).get("result",{}).get("value")
        if done: break
        time.sleep(0.08)
    ws.close(); print(f"captured {i} frames over {ts[-1]:.1f}s",flush=True)
finally: proc.terminate()
with open(f"{FR}/list.txt","w") as f:
    for k in range(i): f.write(f"file 'f_{k:04d}.png'\nduration {(ts[k+1]-ts[k]) if k+1<i else 0.5:.4f}\n")
    f.write(f"file 'f_{i-1:04d}.png'\n")
r=subprocess.run(["/opt/homebrew/bin/ffmpeg","-y","-f","concat","-safe","0","-i",f"{FR}/list.txt","-fps_mode","vfr","-vf",f"scale={W}:{H}","-c:v","libx264","-pix_fmt","yuv420p","-crf","18","-movflags","+faststart",OUT],capture_output=True,text=True)
print(r.stderr.splitlines()[-1] if r.returncode else f"OK -> {OUT}"); subprocess.run(["ls","-la",OUT])
