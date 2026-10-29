#!/usr/bin/env python3
"""Browser regression guard for the ELH header and direct Request Care action.

Starts a private local static server, drives the installed Chromium through the
DevTools protocol, and verifies both the canonical homepage and a generated
city page at 320px, 390px and desktop. No third-party Python or Node packages
are needed. Checks navigation only; no care requests are submitted.
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
PAGES = ("/", "/index.html", "/hospice-torrance-ca.html")
WIDTHS = (320, 390, 1280)


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

CARE_NAV_EXPRESSION = r"""
(async () => {
  const nav = document.querySelector('#hdr nav');
  const contact = nav.querySelector('.nav-group--contact');
  const care = contact && contact.querySelector(':scope > .nav-parent');
  const visible = el => !!(el && el.getClientRects().length &&
    getComputedStyle(el).display !== 'none' &&
    getComputedStyle(el).visibility !== 'hidden');
  const dropdowns = [...nav.querySelectorAll('.nav-group')]
    .filter(group => group !== contact);
  const expectedSections = ['hospice-care', 'services', 'resources', 'service-areas', 'about'];
  const exercise = async group => {
    const toggle = group.querySelector('.nav-toggle');
    const submenu = group.querySelector('.nav-sub');
    const parent = group.querySelector('.nav-parent');
    if (!toggle || !submenu || !parent) return false;
    const href = parent.getAttribute('href');
    toggle.click();
    // Desktop visibility transitions need a rendering frame before inspection.
    const deadline = performance.now() + 1000;
    while (!visible(submenu) && performance.now() < deadline) {
      await new Promise(resolve => requestAnimationFrame(resolve));
    }
    const opened = toggle.getAttribute('aria-expanded') === 'true' &&
      toggle.getAttribute('aria-controls') === submenu.id &&
      group.classList.contains('expanded') && visible(submenu) &&
      [...submenu.querySelectorAll('a[href]')].some(visible) &&
      visible(toggle) && parent.tagName === 'A' && !!href &&
      !nav.querySelector('.nav-group.expanded:not([data-section="' +
        group.dataset.section + '"])');
    toggle.click();
    return opened && toggle.getAttribute('aria-expanded') === 'false' &&
      !group.classList.contains('expanded') && parent.getAttribute('href') === href;
  };
  let otherDropdownsUsable = true;
  for (const section of expectedSections) {
    const group = dropdowns.find(group => group.dataset.section === section);
    if (!group || !await exercise(group)) otherDropdownsUsable = false;
  }
  // Main's shared header now makes Request Care direct on non-homepages too.
  // Pin that current baseline rather than restoring the retired city dropdown.
  const contactStructure = !!contact && !!care &&
    !contact.querySelector('.nav-toggle, .nav-sub') &&
    !care.hasAttribute('aria-expanded') && !care.hasAttribute('aria-controls') &&
    !care.hasAttribute('aria-haspopup');
  return {
    otherDropdownsUsable,
    contactStructure,
    careDestination: !!care && care.tagName === 'A' &&
      care.textContent.trim() === 'Request Care' &&
      care.getAttribute('href') === '/?lead=family#leadcap',
    careVisible: visible(care)
  };
})()
"""


def evaluate(client, expression):
    return client.call(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
    )["result"].get("value")


def wait_for(client, expression, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if evaluate(client, expression):
            return True
        time.sleep(0.05)
    return False


def press_key(client, key, code, virtual_key):
    for kind in ("keyDown", "keyUp"):
        client.call("Input.dispatchKeyEvent", {
            "type": kind, "key": key, "code": code,
            "windowsVirtualKeyCode": virtual_key,
            **({"text": "\r"} if key == "Enter" and kind == "keyDown" else {}),
        })


def check_care_navigation(client, mobile):
    checks = {}
    # Deliberately start in a different audience on the homepage. This catches
    # a lost query parameter even though Family is the markup's initial default.
    if evaluate(client, "!!document.querySelector('.lead-cat[data-cat=\"voice\"]')"):
        evaluate(client, "document.querySelector('.lead-cat[data-cat=\"voice\"]').click()")
        checks["non-family audience selected before navigation"] = evaluate(client, (
            "document.querySelector('.lead-cat.active').dataset.cat === 'voice' && "
            "document.querySelector('.lead-form.show').dataset.form === 'voice'"
        ))

    # Open mobile navigation using the keyboard, not a synthetic link click.
    if mobile:
        evaluate(client, "document.querySelector('#hdr .menu-btn').focus()")
        press_key(client, "Enter", "Enter", 13)
    result = evaluate(client, CARE_NAV_EXPRESSION)
    checks.update(result)
    if mobile:
        checks["keyboard opens mobile menu"] = evaluate(client, (
            "document.querySelector('#hdr').classList.contains('nav-open') && "
            "document.querySelector('#hdr .menu-btn').getAttribute('aria-expanded') === 'true'"
        ))

    # Start at the first top-level link and traverse native tab order. The care
    # action must be reachable and Enter must follow its URL without opening a menu.
    evaluate(client, "document.querySelector('#hdr nav a').focus()")
    care_focused = False
    for _ in range(50):
        if evaluate(client, (
            "document.activeElement.matches('#hdr .nav-group--contact > .nav-parent')"
        )):
            care_focused = True
            break
        press_key(client, "Tab", "Tab", 9)
    checks["Request Care reachable by Tab"] = care_focused
    if care_focused:
        press_key(client, "Enter", "Enter", 13)
        checks["Enter arrives at Family care form"] = wait_for(client, r"""
          location.pathname === '/' && location.search === '?lead=family' &&
          location.hash === '#leadcap' &&
          document.readyState === 'complete' &&
          document.querySelectorAll('.lead-cat.active').length === 1 &&
          document.querySelector('.lead-cat.active').dataset.cat === 'family' &&
          document.querySelectorAll('.lead-form.show').length === 1 &&
          document.querySelector('.lead-form.show').dataset.form === 'family' &&
          getComputedStyle(document.querySelector('.lead-form.show')).display !== 'none'
        """)
    return checks


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
            client.call("Page.bringToFront")
            for page in PAGES:
                for width in WIDTHS:
                    client.call(
                        "Emulation.setDeviceMetricsOverride",
                        {
                            "width": width,
                            "height": 844,
                            "deviceScaleFactor": 1,
                            "mobile": width < 1000,
                        },
                    )
                    client.call(
                        "Page.navigate",
                        {"url": f"http://127.0.0.1:{site_port}{page}"},
                    )
                    # The homepage has substantial deferred content; wait for the
                    # shared header enhancer to create disclosure controls before
                    # exercising them.
                    ready = wait_for(client, (
                        "document.readyState === 'complete' && "
                        f"location.pathname === {json.dumps(page)} && "
                        "!!document.querySelector('#hdr .nav-toggle')"
                    ))
                    if not ready:
                        failures.append((page, width, ["header did not become ready"], {}))
                        continue
                    result = evaluate(client, CHECK_EXPRESSION) if width < 1000 else {}
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
                    } if width < 1000 else {}
                    checks.update(check_care_navigation(client, width < 1000))
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
        print("\n❌ Header browser regression(s):")
        for page, width, broken, result in failures:
            print(f"  {page} at {width}px: {', '.join(broken)}")
            print(f"    metrics: {json.dumps(result, sort_keys=True)}")
        raise SystemExit(1)

    print("SENTINEL: test-header-mobile.py browser checks OK")


if __name__ == "__main__":
    main()