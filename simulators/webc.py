import colorsys
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer

_BOUNDARY = "smarthomecam"


def _make_png(width, height, color):
    """Builds a valid solid-color PNG by hand (stdlib zlib/struct only) -
    good enough as a placeholder frame; no image library dependency.
    """
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))

    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    row = b'\x00' + bytes(color) * width  # filter type 0 (none) per scanline
    idat = chunk(b'IDAT', zlib.compress(row * height, 6))
    iend = chunk(b'IEND', b'')
    return signature + ihdr + idat + iend


def _current_frame():
    hue = (time.time() % 10) / 10.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.9)
    return _make_png(320, 240, (int(r * 255), int(g * 255), int(b * 255)))


class _MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep console output focused on sensor readings

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={_BOUNDARY}")
        self.end_headers()
        try:
            while not self.server.stop_event.is_set():
                frame = _current_frame()
                self.wfile.write(f"--{_BOUNDARY}\r\n".encode())
                self.wfile.write(b"Content-Type: image/png\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            pass


class _ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_webc_simulator(port, stop_event):
    server = _ThreadingHTTPServer(("0.0.0.0", port), _MJPEGHandler)
    server.stop_event = stop_event

    def watch_stop():
        stop_event.wait()
        server.shutdown()

    watcher = threading.Thread(target=watch_stop, daemon=True)
    watcher.start()
    server.serve_forever(poll_interval=0.5)
    server.server_close()
