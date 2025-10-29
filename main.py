from machine import Pin
import network
import time
import json
import uos
import gc

import PicoePaper75 as epd7in5

import framebuf
import gc
try:
    import urequests as requests
except Exception:
    import requests    # fallback if using a port that provides requests

CONFIG_PATH = "/secrets.json"

# --- HTTP-date parser: "Mon, 27 Oct 2025 14:22:01 GMT" ---
_MONTH = {b"Jan":1,b"Feb":2,b"Mar":3,b"Apr":4,b"May":5,b"Jun":6,
          b"Jul":7,b"Aug":8,b"Sep":9,b"Oct":10,b"Nov":11,b"Dec":12}





# Download an image over HTTP and save to local storage
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
    parsedDate = None
    try: 
        resp = requests.get(url)
        print(resp.headers)
        fileDate = resp.headers.get("Last-Modified") # this is the last modifed of the file on the server
        print(fileDate)
        
        parsedDate = parse_http_date(fileDate)
        print("paresed HTTP date:", parsedDate, "Last modified from header:", fileDate)
        if parsedDate and last_modified >= parsedDate:
            print("File not modified since last download")
            resp.close()
            return
        socket = resp.raw
        with open(dest_path, "wb") as fd:
            while (n := socket.readinto(buffer)) > 0:
                fd.write(buffer[:n])
    finally:
        resp.close()   
    return parsedDate


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

def load_pbm_p4(path, invert=False):
    '''
    Load a PBM P4 (binary) image from the filesystem into a FrameBuffer.
    Returns (FrameBuffer, bytearray buffer, width, height)
    '''
    # Parse minimal PBM (P4) header
    with open(path, "rb") as f:
        magic = f.readline().strip()
        if magic != b'P4':
            raise ValueError("Not PBM P4")

        # Skip comments and read width/height
        def next_token():
            while True:
                b = f.read(1)
                if not b:
                    raise ValueError("Unexpected EOF in header")
                if b in b' \t\r\n':
                    continue
                if b == b'#':              # comment
                    while True:
                        c = f.read(1)
                        if not c or c == b'\n':
                            break
                    continue
                # start of a token
                tok = [b]
                while True:
                    c = f.read(1)
                    if not c or c in b' \t\r\n':
                        break
                    tok.append(c)
                return b''.join(tok)

        w = int(next_token())
        h = int(next_token())

        # Each row is ceil(w/8) bytes
        row_bytes = (w + 7) // 8
        data = f.read(row_bytes * h)
        if len(data) != row_bytes * h:
            raise ValueError("PBM data truncated")

    # PBM P4: bit=1 is black, MSB is leftmost pixel.
    # framebuf.MONO_HMSB matches the bit order.
    buf = bytearray(data)

    if invert:
        for i in range(len(buf)):
            buf[i] ^= 0xFF

    fb = framebuf.FrameBuffer(buf, w, h, framebuf.MONO_HMSB)
    return fb, buf, w, h

# main code


def main():
    LED = Pin("LED", Pin.OUT)
    shutdownPin = Pin(19, Pin.OUT)
    LED.value(1)  # Turn the LED on

    try:
        print("Starting up")
        cfg = read_config()
        ssid = cfg["ssid"]
        pwd = cfg["password"]
        url = cfg["file_url"]
        last_modified = cfg.get("last_modified", 0)
        target = cfg.get("target_path", "/image.pbm")
        print("Config Read")

        print("Connecting to WiFi:", ssid)
        wlan = connect_wifi(ssid, pwd)
        print("Connected, IP:", wlan.ifconfig()[0])
    
        print("Downloading File:", url)
        newDate = downloadfile(url, target, last_modified)
        wlan.deinit()
        print("File download complete")
        print("WiFi disconnected")
        if newDate:
            print("File on server was newer than local copy and was downloaded. Lets update")
            print("Updating last_modified to", newDate)
            

            fb, buf, w, h = load_pbm_p4("/calendar.pbm", invert=False)
            print("Loaded PBM from file system:", w, "x", h)
            gc.collect()

            epd = epd7in5.EPD_7in5()
            epd.init() 
            gc.collect()
            print("Displaying image")
            epd.display(buf)
            epd.delay_ms(500)

            print("sleep")
            epd.sleep()
            cfg["last_modified"] = newDate
            write_cfg(cfg)
        else:
            print("File on server not newer than local copy, not updating display")

        print("Done. Shutting down.")
    finally:
        shutdownPin.value(1)  # Signal shutdown
        print("Should only see this if something went wrong before shutdown or testing")

if __name__ == "__main__":
    main()