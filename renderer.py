"""Vice City Intel branded intro renderer. No Buffer calls or automated posting."""
import http.server
import json
import os
import subprocess
import tempfile
from pathlib import Path

PORT = int(os.getenv("PORT", "8080"))
SCRIPT = "Welcome to Vice City Intel. Your destination for Grand Theft Auto six updates. We separate confirmed announcements from rumors, so you know what is real. Follow for the latest coverage."
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def render():
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voice.wav"
        mp4 = Path(tmp) / "preview.mp4"
        subprocess.run(["espeak-ng", "-v", "en-us+m3", "-s", "145", "-w", str(wav), SCRIPT], check=True, timeout=30)
        # Distinct visual test, not a publishable branded Short.
        vf = ("drawtext=fontfile=" + FONT +
              ":text='VICE CITY INTEL':fontsize=62:fontcolor=white:x=(w-text_w)/2:y=750,"
              "drawtext=fontfile=" + FONT +
              ":text='GTA VI NEWS AND UPDATES':fontsize=32:fontcolor=cyan:x=(w-text_w)/2:y=900")
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i","color=c=0x10152c:s=720x1280:r=24",
                        "-i",str(wav),"-vf",vf,"-c:v","libx264","-preset","ultrafast",
                        "-pix_fmt","yuv420p","-c:a","aac","-shortest","-t","12",str(mp4)],
                       check=True,timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        return mp4.read_bytes()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path == '/health':
            self.send_response(200); self.send_header('Content-Type','application/json')
        elif self.path == '/video/intro.mp4' and os.getenv('ALLOW_PUBLIC_INTRO') == '1':
            self.send_response(200); self.send_header('Content-Type','video/mp4')
        else:
            self.send_response(404)
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            data = json.dumps({"status":"ok","service":"vice-city-intel-renderer","publishing":False}).encode()
            self.send_response(200); self.send_header("Content-Type","application/json")
        elif (self.path == "/video/intro.mp4" and os.getenv("ALLOW_PUBLIC_INTRO") == "1") or (self.path == "/test-render" and os.getenv("ALLOW_TEST_RENDER") == "1"):
            try:
                data = render()
                self.send_response(200); self.send_header("Content-Type","video/mp4")
            except Exception:
                data = b'{"error":"render_failed"}'
                self.send_response(500); self.send_header("Content-Type","application/json")
        else:
            data = b'{"error":"not_found"}'
            self.send_response(404); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self,*args): pass

if __name__ == "__main__":
    if os.getenv("VCI_BUILD_SMOKE_TEST") == "1":
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "render.mp4"
            output.write_bytes(render())
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                 "-of", "json", str(output)],
                check=True, capture_output=True, text=True, timeout=20
            )
            streams = json.loads(result.stdout)["streams"]
            assert any(s.get("codec_type") == "video" and s.get("width") == 720 and s.get("height") == 1280 for s in streams)
            assert any(s.get("codec_type") == "audio" for s in streams)
            print("VCI_RENDER_SMOKE_TEST_PASS: 720x1280 H264 MP4 with audio")
    else:
        http.server.ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
