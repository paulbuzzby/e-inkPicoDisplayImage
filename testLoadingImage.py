
import PicoePaper75 as epd7in5

import framebuf
import gc

def load_pbm_p4(path, invert=False):
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



fb, buf, w, h = load_pbm_p4("/calendar.pbm", invert=False)
print("Loaded PBM:", w, "x", h)
gc.collect()
print("Free memory:", gc.mem_free())

epd = epd7in5.EPD_7in5()
print("Free memory:", gc.mem_free())
epd.init() 
print("Free memory:", gc.mem_free())
gc.collect()

epd.display(buf)
epd.delay_ms(2000)


#epd.Clear()
#epd.delay_ms(2000)
print("sleep")
epd.sleep()
print("Done")