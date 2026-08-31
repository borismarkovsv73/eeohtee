import subprocess
import time


def run_webc_process(settings, stop_event):
    """Runs the real mjpg_streamer binary as a subprocess, same invocation
    as the course tutorial: input_uvc.so grabs frames from the camera,
    output_http.so serves them as an MJPEG stream on the given port.
    Expects mjpg_streamer to already be installed/built on the Pi.
    """
    device = settings.get('device', '/dev/video0')
    port = settings.get('port', 8080)
    resolution = settings.get('resolution', '640x480')
    framerate = settings.get('framerate', 15)
    www_dir = settings.get('www_dir', '/usr/local/share/mjpg-streamer/www')

    input_opts = f"input_uvc.so -d {device} -r {resolution} -f {framerate}"
    output_opts = f"output_http.so -p {port} -w {www_dir}"

    process = subprocess.Popen(["mjpg_streamer", "-i", input_opts, "-o", output_opts])
    try:
        while not stop_event.is_set():
            if process.poll() is not None:
                break
            time.sleep(0.5)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
