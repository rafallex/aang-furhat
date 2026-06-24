"""One HTTP server that hands audio files to the robot over the LAN.

`request.speak.audio` makes the *robot* fetch a URL and play it, so any custom
audio we want it to play (the Avatar-State wind, the rendered deep voice) has to
be served from THIS PC on the LAN -- not localhost. Both producers share this one
server and one directory, so there is a single port to open in the firewall.

Best-effort: if the port can't bind, the caller disables custom audio and the
rest of the show carries on.
"""

import os
import socket
import functools
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


def detect_lan_ip():
    """Best guess at this machine's LAN IP (the address the robot can reach).

    No packets are actually sent -- connecting a UDP socket just makes the OS pick
    the outbound route, and we read back which local address it chose."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass  # keep the console clean


class LanAudioServer:
    """Serves a single directory of WAVs to the robot over HTTP."""

    def __init__(self, directory, host="", port=8077):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self.host = host or detect_lan_ip()
        self.port = port
        self.httpd = None

    def start(self):
        handler = functools.partial(_QuietHandler, directory=self.directory)
        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self.base_url()

    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def url_for(self, filename, bust=None):
        """URL the robot can fetch. Pass `bust` to append a cache-buster so the
        robot never replays a stale file left from a previous run."""
        url = f"{self.base_url()}/{filename}"
        return f"{url}?t={bust}" if bust is not None else url

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
