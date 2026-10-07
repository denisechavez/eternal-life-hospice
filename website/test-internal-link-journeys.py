#!/usr/bin/env python3
"""Desktop/mobile related-reading and real keyboard navigation checks."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from devserver import PrettyURLHandler

spec = importlib.util.spec_from_file_location("header_browser", Path(__file__).with_name("test-header-mobile.py"))
browser_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser_tools)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), PrettyURLHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    debug_port = sock.getsockname()[1]
    sock.close()
    routes = ["/hospice-care", "/resources", "/hospice-thousand-oaks-ca",
              "/blog/the-caregiver-who-needs-care", "/family-guide", "/refer"]
    with tempfile.TemporaryDirectory(prefix="elh-link-browser-") as profile:
        browser = subprocess.Popen([browser_tools.browser_binary(), "--headless=new", "--no-sandbox",
                                    "--disable-gpu", "--remote-allow-origins=*",
                                    f"--remote-debugging-port={debug_port}", f"--user-data-dir={profile}", "about:blank"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = None
        try:
            client = browser_tools.DevTools(browser_tools.wait_for_page_debugger(debug_port))
            client.call("Page.enable")
            # Avoid loading third-party trackers. Install GA4 test doubles only
            # after the real consent-aware handlers have bound.
            client.call("Page.addScriptToEvaluateOnNewDocument", {"source":
                        "localStorage.setItem('elh_cc','essential');"})
            for width in (390, 1280):
                client.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 600})
                for route in routes:
                    url = f"http://127.0.0.1:{server.server_address[1]}{route}"
                    client.call("Page.navigate", {"url": url})
                    for _ in range(100):
                        ready = client.call("Runtime.evaluate", {"expression": "document.readyState==='complete' && !!document.querySelector('.elh-related a')", "returnByValue": True})["result"].get("value")
                        if ready:
                            break
                        time.sleep(.1)
                    assert ready, (width, route, "section missing")
                    result = client.call("Runtime.evaluate", {"expression": """(() => {
                      const section=document.querySelector('.elh-related'), links=[...section.querySelectorAll('a')];
                      section.scrollIntoView(); links[0].focus();
                      return {width:section.getBoundingClientRect().width,
                        overflow:section.scrollWidth>section.clientWidth+1,
                        names:links.every(a=>a.textContent.trim().length>8),
                        columns:getComputedStyle(section.querySelector('ul')).gridTemplateColumns.split(' ').length,
                        href:links[1].getAttribute('href')};
                    })()""", "returnByValue": True})["result"]["value"]
                    assert not result["overflow"] and result["names"], (route, result)
                    assert result["columns"] == (1 if width == 390 else 2), (route, result)
                    client.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
                    client.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
                    focused = client.call("Runtime.evaluate", {"expression": """(() => {
                      const a=document.activeElement;
                      return {href:a.getAttribute('href'),outline:getComputedStyle(a).outlineWidth,
                        visible:a.matches(':focus-visible')};
                    })()""", "returnByValue": True})["result"]["value"]
                    assert focused["href"] == result["href"] and focused["visible"] and focused["outline"] == "3px", (route, focused)
                    mode = {"/hospice-care": "essential", "/resources": "record",
                            "/hospice-thousand-oaks-ca": "missing",
                            "/blog/the-caregiver-who-needs-care": "throw",
                            "/family-guide": "record", "/refer": "record"}[route]
                    before = client.call("Runtime.evaluate", {"expression": """(() => {
                      const mode=MODE, a=document.activeElement;
                      sessionStorage.removeItem('reading-event');
                      localStorage.setItem('elh_cc', mode==='essential'?'essential':'all');
                      window.gtag=mode==='missing'?undefined:(...args)=>{
                        if(mode==='throw') throw new Error('tracker unavailable');
                        sessionStorage.setItem('reading-event',JSON.stringify(args));
                      };
                      return {source:a.dataset.readingSource,
                        destination:a.dataset.readingDestination,topic:a.dataset.readingTopic};
                    })()""".replace("MODE", json.dumps(mode)), "returnByValue": True})["result"]["value"]
                    client.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
                    client.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
                    for _ in range(50):
                        path = client.call("Runtime.evaluate", {"expression": "location.pathname+location.search+location.hash", "returnByValue": True})["result"].get("value")
                        if path == result["href"]:
                            break
                        time.sleep(.1)
                    assert path == result["href"], (route, path, result["href"])
                    recorded = client.call("Runtime.evaluate", {"expression":
                        "JSON.parse(sessionStorage.getItem('reading-event'))", "returnByValue": True})["result"].get("value")
                    expected = ["event", "related_reading_click", {
                        "source_page": before["source"], "destination_page": before["destination"],
                        "topic": before["topic"]}] if mode == "record" else None
                    assert recorded == expected, (mode, route, recorded, expected)
                    print(f"PASS {width}px {route}: readable links, Tab/Enter navigation, {mode} analytics")
        finally:
            if client:
                client.close()
            browser.terminate()
            browser.wait(timeout=10)
            server.shutdown()
    print("SENTINEL: test-internal-link-journeys.py browser checks OK")


if __name__ == "__main__":
    main()
