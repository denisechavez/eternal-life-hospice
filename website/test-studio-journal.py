#!/usr/bin/env python3
"""Verify the complete Journal collection and final-article review in Studio."""
import importlib.util
import socket
import subprocess
import tempfile
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("studio_browser", Path(__file__).with_name("test-header-mobile.py"))
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


def main():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    with tempfile.TemporaryDirectory(prefix="elh-studio-browser-") as profile:
        browser = subprocess.Popen([tools.browser_binary(), "--headless=new", "--no-sandbox",
                                    "--disable-gpu", "--remote-allow-origins=*",
                                    f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = None
        try:
            client = tools.DevTools(tools.wait_for_page_debugger(port))
            client.call("Page.enable")
            client.call("Emulation.setDeviceMetricsOverride", {
                "width":1728,"height":980,"deviceScaleFactor":1,"mobile":False})
            client.call("Page.navigate", {"url": "http://127.0.0.1:21921/__reviews-mockup/preview/elh-marketing-hub/Hub?view=Journal"})
            def evaluate(expression):
                return client.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})["result"].get("value")
            for _ in range(250):
                if evaluate("document.querySelectorAll('.studio-row').length===107"):
                    break
                time.sleep(.1)
            assert evaluate("document.querySelectorAll('.studio-row').length") == 107, evaluate("document.body.innerText")
            assert evaluate("[...document.querySelectorAll('.studio-row small')].some(e=>e.textContent.includes('2026-12-31'))")
            evaluate("""(()=>{const s=document.querySelector('[aria-label="Filter Journal month"]');
                s.value='2026-12';s.dispatchEvent(new Event('change',{bubbles:true}));})()""")
            time.sleep(.4)
            assert evaluate("document.querySelectorAll('.studio-row').length") == 31
            evaluate("window.scrollTo(0,document.documentElement.scrollHeight)")
            time.sleep(.2)
            assert evaluate("window.scrollY") > 500
            evaluate("[...document.querySelectorAll('.studio-row')].at(-1).click()")
            time.sleep(.5)
            assert evaluate("!!document.querySelector('.article-review iframe')")
            assert evaluate("""(()=>{const r=document.querySelector('.detail-drawer').getBoundingClientRect();
                return Math.abs(r.top)<1 && Math.abs(r.height-window.innerHeight)<2})()"""), "Reader is outside the visible viewport"
            assert evaluate("""(()=>{const d=document.querySelector('.article-review iframe').contentDocument;
                return d?.querySelector('h1')?.textContent.includes('Begin the New Year') &&
                  d.querySelector('article').innerText.split(/\\s+/).length>300 &&
                  getComputedStyle(d.querySelector('article')).display!=='none' &&
                  Number(getComputedStyle(d.querySelector('article')).opacity)>0})()"""), "Full article is not readable"
            for _ in range(80):
                if evaluate("""[...document.querySelector('.article-review iframe').contentDocument.styleSheets]
                    .some(s=>s.href?.includes('/assets/elh.css'))"""):
                    break
                time.sleep(.1)
            assert evaluate("""[...document.querySelector('.article-review iframe').contentDocument.styleSheets]
                .some(s=>s.href?.includes('/assets/elh.css'))"""), "Original article styling failed to load"
            assert evaluate("""(()=>{const raw=document.querySelector('.article-review iframe').srcdoc;
                return raw.includes('Begin the New Year') && raw.includes('elh-inline-link') &&
                  raw.includes('journal/q4/begin-the-new-year-with-one-clear-care-conversation.jpg') &&
                  !/<script\\b/i.test(raw)})()""")
            assert evaluate("document.querySelector('.detail-body').innerText.includes('Needs review')")
            # Ensure the new list did not silently promote future posts to approved.
            evaluate("document.querySelector('[aria-label=\"Close review\"]').click()")
            evaluate("""(()=>{const s=document.querySelector('[aria-label="Filter Journal month"]');
                s.value='';s.dispatchEvent(new Event('change',{bubbles:true}));})()""")
            time.sleep(.3)
            assert evaluate("document.querySelectorAll('.studio-row').length") == 107
            # Returning to Journal after scrolling another view must show the list,
            # not retain the old page's off-screen scroll position.
            evaluate("""[...document.querySelectorAll('.nav-items button')]
                .find(b=>b.textContent.trim()==='Content Calendar').click()""")
            time.sleep(.2)
            evaluate("""[...document.querySelectorAll('.nav-items button')]
                .find(b=>b.textContent.trim()==='Eternal Journal').click()""")
            time.sleep(.3)
            assert evaluate("window.scrollY") == 0
            assert evaluate("document.querySelectorAll('.studio-row').length") == 107
            # Cover every legacy, original-campaign and continuation article.
            for index in range(107):
                evaluate(f"document.querySelectorAll('.studio-row')[{index}].click()")
                for _ in range(50):
                    readable=evaluate("""(()=>{const f=document.querySelector('.article-review iframe');
                        const d=f?.contentDocument;const main=d?.querySelector('main');
                        const heading=d?.querySelector('h1');
                        return !!main && !!heading && main.innerText.split(/\\s+/).length>100 &&
                          Number(getComputedStyle(main).opacity)>0})()""")
                    if readable:
                        break
                    time.sleep(.05)
                assert readable, f"Blank article review at row {index}"
                evaluate("document.querySelector('[aria-label=\"Close review\"]').click()")
            print("SENTINEL: test-studio-journal.py 107 posts, full visible reader, original styling and navigation OK")
        finally:
            if client:
                client.close()
            browser.terminate()
            browser.wait(timeout=10)


if __name__ == "__main__":
    main()
