#!/usr/bin/env python3
"""Browser regression guard for the ELH header at phone widths.

Starts a private local static server, drives the installed Chromium through the
DevTools protocol, and verifies both the canonical homepage and a generated
city page at 320px and 390px. No third-party Python or Node packages are needed.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent / "elh-preview"
PAGES = ("/index.html", "/hospice-torrance-ca.html")
WIDTHS = (320, 390)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


class WebSocket:
    def __init__(self, url):
        parsed = urlparse(url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        request = (
            f"GET {target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self._read_until(b"\r\n\r\n")
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        )
        if b" 101 " not in response or expected not in response:
            status = response.split(b"\r\n", 1)[0].decode("ascii", "replace")
            raise RuntimeError(f"Chromium DevTools websocket handshake failed: {status}")

    def _read_until(self, marker):
        data = b""
        while marker not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise EOFError("DevTools websocket closed")
            data += chunk
        return data

    def _read_exact(self, length):
        data = b""
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise EOFError("DevTools websocket closed")
            data += chunk
        return data

    def send(self, payload):
        raw = json.dumps(payload).encode("utf-8")
        mask = os.urandom(4)
        length = len(raw)
        if length < 126:
            header = struct.pack("!BB", 0x81, 0x80 | length)
        elif length < 65536:
            header = struct.pack("!BBH", 0x81, 0xFE, length)
        else:
            header = struct.pack("!BBQ", 0x81, 0xFF, length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(raw))
        self.sock.sendall(header + mask + masked)

    def receive(self):
        first, second = struct.unpack("!BB", self._read_exact(2))
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        if second & 0x80:
            mask = self._read_exact(4)
        else:
            mask = None
        data = self._read_exact(length)
        if mask:
            data = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
        if opcode == 0x9:
            self.sock.sendall(bytes([0x8A, len(data)]) + data)
            return self.receive()
        if opcode == 0x8:
            raise EOFError("DevTools websocket closed")
        return json.loads(data.decode("utf-8"))

    def close(self):
        self.sock.close()


class DevTools:
    def __init__(self, websocket_url):
        self.ws = WebSocket(websocket_url)
        self.next_id = 1

    def call(self, method, params=None):
        call_id = self.next_id
        self.next_id += 1
        self.ws.send({"id": call_id, "method": method, "params": params or {}})
        while True:
            message = self.ws.receive()
            if message.get("id") != call_id:
                continue
            if "error" in message:
                raise RuntimeError(f"{method}: {message['error']}")
            return message.get("result", {})

    def close(self):
        self.ws.close()


CHECK_EXPRESSION = r"""
(() => {
  const hdr = document.getElementById('hdr');
  const button = hdr && hdr.querySelector('.menu-btn');
  const nav = hdr && hdr.querySelector('nav');
  if (!hdr || !button || !nav) return { error: 'missing header, menu button, or nav' };
  const rect = button.getBoundingClientRect();
  const style = getComputedStyle(button);
  const before = button.getAttribute('aria-expanded');
  const controls = button.getAttribute('aria-controls');
  const controlledNav = controls && document.getElementById(controls) === nav;
  const hit = document.elementFromPoint(
    Math.max(0, Math.min(innerWidth - 1, rect.left + rect.width / 2)),
    Math.max(0, Math.min(innerHeight - 1, rect.top + rect.height / 2))
  );
  button.click();
  const opened = hdr.classList.contains('nav-open') &&
    button.getAttribute('aria-expanded') === 'true' &&
    getComputedStyle(nav).display !== 'none';
  const parent = nav.querySelector('.nav-parent');
  const toggle = nav.querySelector('.nav-toggle');
  const subId = toggle && toggle.getAttribute('aria-controls');
  const sub = subId && document.getElementById(subId);
  const toggleStyle = toggle && getComputedStyle(toggle);
  const submenuToggleStyled = !!(toggleStyle &&
    toggleStyle.backgroundColor === 'rgba(0, 0, 0, 0)' &&
    toggleStyle.borderTopWidth === '0px' &&
    toggleStyle.borderRightWidth === '0px' &&
    toggleStyle.borderLeftWidth === '0px');
  if (toggle) toggle.click();
  const submenuOpened = !!(parent && toggle && sub &&
    toggle.getAttribute('aria-expanded') === 'true' &&
    toggle.parentElement.classList.contains('expanded') &&
    getComputedStyle(sub).display !== 'none');
  const parentNavigable = parent && parent.tagName === 'A' &&
    parent.getAttribute('href') === '/hospice-care';
  button.click();
  const closed = !hdr.classList.contains('nav-open') &&
    button.getAttribute('aria-expanded') === 'false';
  return {
    viewport: innerWidth,
    htmlWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth,
    headerScrollWidth: hdr.scrollWidth,
    headerLeft: hdr.getBoundingClientRect().left,
    headerRight: hdr.getBoundingClientRect().right,
    buttonLeft: rect.left,
    buttonRight: rect.right,
    buttonWidth: rect.width,
    buttonHeight: rect.height,
    visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 &&
      rect.height > 0 && rect.left >= 0 && rect.right <= innerWidth,
    hitTarget: !!(hit && (hit === button || button.contains(hit))),
    initialCollapsed: before === 'false',
    controlledNav,
    opened,
    submenuToggleStyled,
    submenuOpened,
    parentNavigable,
    closed
  };
})()
"""


def browser_binary():
    configured = os.environ.get("CHROME_BIN") or os.environ.get("CHROMIUM_BIN")
    candidates = [configured, "chromium", "chromium-browser", "google-chrome"]
    for candidate in candidates:
        if candidate and (os.path.isfile(candidate) or shutil.which(candidate)):
            return candidate
    raise RuntimeError("Chromium not found (set CHROME_BIN or CHROMIUM_BIN)")


def wait_for_page_debugger(port):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            targets = json.load(urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1))
            page = next(target for target in targets if target.get("type") == "page")
            return page["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Chromium DevTools page target did not become ready")


def main():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs),
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    site_port = server.server_address[1]

    debug_socket = socket.socket()
    debug_socket.bind(("127.0.0.1", 0))
    debug_port = debug_socket.getsockname()[1]
    debug_socket.close()

    with tempfile.TemporaryDirectory(prefix="elh-header-chrome-") as profile:
        browser = subprocess.Popen(
            [
                browser_binary(),
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-background-networking",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        client = None
        failures = []
        try:
            client = DevTools(wait_for_page_debugger(debug_port))
            client.call("Page.enable")
            for page in PAGES:
                for width in WIDTHS:
                    client.call(
                        "Emulation.setDeviceMetricsOverride",
                        {
                            "width": width,
                            "height": 844,
                            "deviceScaleFactor": 1,
                            "mobile": True,
                        },
                    )
                    client.call(
                        "Page.navigate",
                        {"url": f"http://127.0.0.1:{site_port}{page}"},
                    )
                    # The homepage has substantial deferred content; wait for the
                    # shared header enhancer to create disclosure controls before
                    # exercising them.
                    for _ in range(20):
                        ready = client.call(
                            "Runtime.evaluate",
                            {
                                "expression": (
                                    "document.readyState !== 'loading' && "
                                    "!!document.querySelector('#hdr .nav-toggle')"
                                ),
                                "returnByValue": True,
                            },
                        )["result"].get("value")
                        if ready:
                            break
                        time.sleep(0.05)
                    result = client.call(
                        "Runtime.evaluate",
                        {"expression": CHECK_EXPRESSION, "returnByValue": True},
                    )["result"]["value"]
                    checks = {
                        "no horizontal clipping": (
                            result.get("headerScrollWidth") <= width
                            and result.get("headerLeft", -1) >= 0
                            and result.get("headerRight", width + 1) <= width
                        ),
                        "hamburger visible": result.get("visible"),
                        "hamburger is the hit target": result.get("hitTarget"),
                        "menu starts collapsed": result.get("initialCollapsed"),
                        "menu controls nav": result.get("controlledNav"),
                        "menu opens": result.get("opened"),
                        "submenu toggle has no native button box": result.get(
                            "submenuToggleStyled"
                        ),
                        "submenu opens accessibly": result.get("submenuOpened"),
                        "Hospice Care landing page remains linked": result.get("parentNavigable"),
                        "menu closes": result.get("closed"),
                    }
                    broken = [label for label, passed in checks.items() if not passed]
                    if result.get("error"):
                        broken.append(result["error"])
                    if broken:
                        failures.append((page, width, broken, result))
                    else:
                        print(f"  ✓ {page} at {width}px")
        finally:
            if client:
                client.close()
            browser.terminate()
            try:
                browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser.kill()
            server.shutdown()

    if failures:
        print("\n❌ Mobile header browser regression(s):")
        for page, width, broken, result in failures:
            print(f"  {page} at {width}px: {', '.join(broken)}")
            print(f"    metrics: {json.dumps(result, sort_keys=True)}")
        raise SystemExit(1)

    print("SENTINEL: test-header-mobile.py browser checks OK")


if __name__ == "__main__":
    main()