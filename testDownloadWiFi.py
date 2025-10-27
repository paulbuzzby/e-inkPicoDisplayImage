#  python -m http.server 9000 to host files for testing
import network
import time
import json
import uos
import gc
try:
    import urequests as requests
except Exception:
    import requests    # fallback if using a port that provides requests

CONFIG_PATH = "/secrets.json"

# --- HTTP-date parser: "Mon, 27 Oct 2025 14:22:01 GMT" ---
_MONTH = {b"Jan":1,b"Feb":2,b"Mar":3,b"Apr":4,b"May":5,b"Jun":6,
          b"Jul":7,b"Aug":8,b"Sep":9,b"Oct":10,b"Nov":11,b"Dec":12}

def read_config(path=CONFIG_PATH):
    with open(path, "r") as f:
        return json.load(f)

def write_cfg(cfg, path=CONFIG_PATH):
    # atomic-ish write
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f)
    import uos
    try: uos.remove(path)
    except OSError: pass
    uos.rename(tmp, path)        

def connect_wifi(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)
    t0 = time.time()
    while not wlan.isconnected():
        if time.time() - t0 > timeout:
            raise RuntimeError("WiFi connection timed out")
        time.sleep(0.5)
    return wlan

def ensure_dir_for(path):
    # ensure directory exists for a target path like /images/display.pbm
    dirpath = "/".join(path.split("/")[:-1])
    if dirpath == "":
        return
    parts = dirpath.split("/")
    p = ""
    for part in parts:
        if part == "":
            p = "/"
            continue
        p = p.rstrip("/") + "/" + part
        try:
            uos.stat(p)
        except OSError:
            try:
                uos.mkdir(p)
            except OSError:
                pass

def downloadfile(url, dest_path, last_modified=0):
    BUFSIZE = 1024

    buffer = memoryview(bytearray(BUFSIZE))
    resp = requests.get(url)
    print(resp.headers)
    fileDate = resp.headers.get("Last-Modified")
    print(fileDate)
    print("File date:", parse_http_date(fileDate))
    parsedDate = parse_http_date(fileDate)
    if parsedDate and last_modified >= parsedDate:
        print("File not modified since last download")
        resp.close()
        return
    socket = resp.raw
    with open(dest_path, "wb") as fd:
        while (n := socket.readinto(buffer)) > 0:
            fd.write(buffer[:n])
    resp.close()   # Dont forget to close your connection
    return parsedDate


def file_mtime(path):
    try:
        return uos.stat(path)[8]   # mtime index in MicroPython stat tuple
    except OSError:
        return None



def parse_http_date(h):
    if not h:
        return None
    b = h.encode() if isinstance(h, str) else h
    # Strip weekday and comma
    try:
        # b"Mon, 27 Oct 2025 14:22:01 GMT"
        _, rest = b.split(b",", 1)
        parts = rest.strip().split()
        # [b'27', b'Oct', b'2025', b'14:22:01', b'GMT']
        day  = int(parts[0])
        mon  = _MONTH[parts[1]]
        year = int(parts[2])
        hh, mm, ss = [int(x) for x in parts[3].split(b":")]
    except Exception:
        return None
    # Build a time tuple; wday/yday ignored by mktime
    return time.mktime((year, mon, day, hh, mm, ss, 0, 0))

def main():
    cfg = read_config()
    ssid = cfg["ssid"]
    pwd = cfg["password"]
    url = cfg["file_url"]
    last_modified = cfg.get("last_modified", 0)
    target = cfg.get("target_path", "/image.pbm")


    print(file_mtime(target))

    print("Connecting to WiFi:", ssid)
    wlan = connect_wifi(ssid, pwd)
    print("Connected, IP:", wlan.ifconfig()[0])
   
    print("Downloading:", url)
    newDate = downloadfile(url, target, last_modified)
    
    if newDate:
        print("Updating last_modified to", newDate)
        cfg["last_modified"] = newDate
        write_cfg(cfg)

if __name__ == "__main__":
    main()
