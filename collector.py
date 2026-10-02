"""Saves TomTom traffic tiles for Dhaka. Run every 15 min (cron / Task Scheduler).
Usage:  TOMTOM_KEY=your_key python collector.py
Output: data/<YYYY-MM-DDTHHMM>/<z>/<x>/<y>.png  +  data/index.json (Dhaka time, UTC+6)
"""
import os, math, time, json, shutil, urllib.request, datetime as dt

KEY = os.environ["TOMTOM_KEY"]
BBOX = (23.68, 90.32, 23.90, 90.50)      # south, west, north, east (edit to widen/narrow)
ZOOMS = range(11, 14)                    # 11..13 (keeps storage small)
KEEP_DAYS = 31
OUT = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TZ = dt.timezone(dt.timedelta(hours=6))

def tile(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y

def tiles():
    s, w, n, e = BBOX
    for z in ZOOMS:
        x0, y1 = tile(s, w, z)
        x1, y0 = tile(n, e, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield z, x, y

def snaps():
    return sorted(d for d in os.listdir(OUT) if len(d) == 15 and d[4] == "-") if os.path.isdir(OUT) else []

def main():
    os.makedirs(OUT, exist_ok=True)
    now = dt.datetime.now(TZ)
    name = now.strftime("%Y-%m-%dT%H%M")
    ok = 0
    for z, x, y in tiles():
        url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative/{z}/{x}/{y}.png?key={KEY}"
        path = os.path.join(OUT, name, str(z), str(x), f"{y}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with urllib.request.urlopen(url, timeout=20) as r, open(path, "wb") as f:
                f.write(r.read())
            ok += 1
        except Exception as e:
            print("fail", z, x, y, e)
        time.sleep(0.25)                 # stay under the default 5 requests/second
    cutoff = (now - dt.timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%dT%H%M")
    for d in snaps():
        if d < cutoff:
            shutil.rmtree(os.path.join(OUT, d))
    tmp = os.path.join(OUT, "index.tmp")
    with open(tmp, "w") as f:
        json.dump(snaps(), f)
    os.replace(tmp, os.path.join(OUT, "index.json"))
    print(f"{name}: saved {ok} tiles")

main()
