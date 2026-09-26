# Live swap UI (one resident base, adapters by URL)
Start (server spawns the entitled daemon under sudo -n; model must be in /Library/Caches/com.apple.aned, adapters in the trusted dir):
  python3 server.py > server.log 2>&1 & echo $! > server.pid
Open http://127.0.0.1:8787   ·   stop: kill $(cat server.pid)   (never pkill -f server.py)
Demo capture to mp4 (real-time, every number measured during capture): python3 capture_demo.py [out.mp4]
?auto=demo runs the scripted sequence; ?auto=both runs the current state on its domain's adapter, then the other domain's positive preset on the other adapter.
