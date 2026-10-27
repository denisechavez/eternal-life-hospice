// Read-only visual proof checks. No form endpoints or email transports are used.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {setTimeout as sleep} from "node:timers/promises";

const messages = JSON.parse(await readFile("artifacts/review-design-sandbox/public/email-design/approved-messages.json", "utf8"));
const base = "http://127.0.0.1:21921/__reviews-mockup/preview/elh-email-review/RefinedLetter";
const profile = await mkdtemp(join(tmpdir(), "elh-letter-proof-"));
const browser = spawn("chromium", ["--headless", "--no-sandbox", "--disable-dev-shm-usage",
  "--disable-background-networking", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"],
  {stdio:["ignore","ignore","pipe"]});
let ws, id = 0, stderr = "";
browser.stderr.on("data", chunk => {stderr = (stderr + chunk).slice(-2000);});
const pending = new Map();
try {
  let port;
  for(let attempt=0;attempt<600;attempt++) {
    try {port=Number((await readFile(join(profile,"DevToolsActivePort"),"utf8")).split("\n")[0]);break;}
    catch {await sleep(50);}
  }
  assert.ok(port, "Browser failed to start: " + stderr);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(tab=>tab.type==="page").webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener("open",resolve,{once:true});ws.addEventListener("error",reject,{once:true});});
  ws.addEventListener("message", event=>{
    const value=JSON.parse(event.data);
    if(pending.has(value.id)){const [resolve,reject]=pending.get(value.id);pending.delete(value.id);value.error?reject(value.error):resolve(value.result);}
  });
  const call = (method,params={})=>new Promise((resolve,reject)=>{
    const next=++id;pending.set(next,[resolve,reject]);ws.send(JSON.stringify({id:next,method,params}));
  });
  const evaluate = async expression=>{
    const result=await call("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
    if(result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  await call("Page.enable");
  for (const width of [1120,390,320]) {
    await call("Emulation.setDeviceMetricsOverride",{width,height:1400,deviceScaleFactor:1,mobile:width<500});
    const cases = width === 1120 ? messages : messages.filter(m=>["family","physician","aleksandra-meeting"].includes(m.key));
    for(const message of cases) {
      await call("Page.navigate",{url:base+"?email="+encodeURIComponent(message.key)});
      let actual;
      for(let attempt=0;attempt<140;attempt++) {
        actual=await evaluate(`(()=>{
          const frame=Array.from(document.querySelectorAll('iframe')).find(f=>f.contentDocument?.body?.textContent.includes('Confirmation number:'));
          if(!frame)return null;
          const doc=frame.contentDocument;
          const view=frame.contentWindow;
          return {
            text:doc.body.innerText.replace(/\\s+/g,' ').trim(),
            overflow:doc.documentElement.scrollWidth>doc.documentElement.clientWidth+1,
            outerOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
            numbers:Array.from(doc.querySelectorAll('a[href^="tel:"]')).map(a=>({text:a.textContent,decoration:view.getComputedStyle(a).textDecorationLine})),
            colors:Array.from(doc.querySelectorAll('p,a,strong,span,td')).filter(el=>Array.from(el.childNodes).some(n=>n.nodeType===3&&n.textContent.trim())).map(el=>({text:el.textContent.slice(0,50),color:view.getComputedStyle(el).color}))
          };
        })()`);
        if(actual && actual.text.includes(message.paragraphs[1].replace(/\s+/g," ").trim()))break;
        await sleep(75);
      }
      assert.ok(actual, `No letter rendered: ${width} ${message.key}`);
      let cursor=0;
      for(const paragraph of message.paragraphs) {
        const normalized=paragraph.replace(/\s+/g," ").trim();
        const index=actual.text.indexOf(normalized,cursor);
        assert.ok(index>=cursor, `Approved paragraph missing/reordered: ${width} ${message.key}: ${paragraph}`);
        cursor=index+normalized.length;
      }
      assert.equal(actual.overflow,false, `Letter overflows: ${width} ${message.key}`);
      assert.equal(actual.outerOverflow,false, `Review overflows: ${width} ${message.key}`);
      for(const number of actual.numbers)assert.equal(number.decoration,"none", `Underlined phone: ${width} ${message.key}`);
      for(const element of actual.colors) {
        const channels=(element.color.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
        assert.ok(channels.length===3 && Math.max(...channels)-Math.min(...channels)<=24 && Math.max(...channels)<=165,
          `Letter type must be grey, not purple or white: ${message.key} ${JSON.stringify(element)}`);
      }
      console.log(`PASS ${width}px ${message.key}: approved paragraphs, grey type, un-underlined phone links, no horizontal overflow`);
    }
  }
} finally {
  ws?.close();
  browser.kill("SIGTERM");
  await new Promise(resolve=>browser.once("exit",resolve));
  await rm(profile,{recursive:true,force:true});
}
