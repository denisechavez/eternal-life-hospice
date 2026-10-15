// Isolated browser fixture: real Studio component, mocked Clerk/fetch, no server
// authentication changes and no real approvals, emails, or production requests.
// Run: node --experimental-websocket website/test-journal-approval-ui.mjs
import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdtemp, readFile, readdir, writeFile, rm} from "node:fs/promises";
import {spawn} from "node:child_process";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";
import {pathToFileURL} from "node:url";

const artifact = resolve("artifacts/review-design-sandbox");
const require = createRequire(join(artifact, "package.json"));
const {build} = require("esbuild");
const directory = await mkdtemp(join(tmpdir(), "elh-approval-ui-"));
const component = join(artifact, "src/components/mockups/elh-marketing-hub");
let browser, ws;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  await build({
    stdin: {contents: `
      import React from "react";
      import {createRoot} from "react-dom/client";
      import Hub from ${JSON.stringify(join(component, "Hub.tsx"))};
      import {journalArticles} from ${JSON.stringify(join(component, "contentData.ts"))};
      const fixture = window.approvalFixture = {posts:[],revision:1,failNext:0};
      let release;
      const firstLoad = new Promise(resolve=>release=resolve);
      fixture.release=()=>release();
      const records=()=>journalArticles.map(a=>({slug:a.slug,title:"Reviewed: "+a.title,
        date:a.date,revision:"r"+fixture.revision,html:"<main><h1>Reviewed version "+fixture.revision+"</h1><p>Complete fixture article.</p></main>",
        status:fixture.published===a.slug?"Published":"Needs review",held:false,hasPublishedVersion:false}));
      window.confirm=()=>{throw new Error("Native browser confirmation must not be used");};
      window.fetch=async(url,options={})=>{
        if(url!=="/api/studio/journal")throw new Error("Unexpected fixture request: "+url);
        if(options.method==="POST"){
          const request=JSON.parse(options.body);fixture.posts.push(request);
          if(fixture.failNext){const status=fixture.failNext;fixture.failNext=0;
            fixture.revision++;return {ok:false,json:async()=>({message:"Article changed. Retry and review the current version."})};}
          fixture.published=request.action==="approve"?request.slug:null;
          if(fixture.failAfterCommit){fixture.failAfterCommit=false;throw new Error("Connection lost after save");}
        }else{await firstLoad;}
        return {ok:true,json:async()=>({items:records()})};
      };
      createRoot(document.getElementById("root")).render(<Hub/>);
    `, resolveDir: artifact, loader: "tsx"},
    bundle: true, outfile: join(directory, "app.js"), format: "iife",
    loader: {".html":"text"},
    jsx: "automatic", logLevel: "error",
    alias: {react: join(artifact,"node_modules/react"), "react-dom":join(artifact,"node_modules/react-dom")},
    define: {"import.meta.env.BASE_URL":"window.fixtureBase", "import.meta.env.DEV":"false"},
    external: ["/__reviews-mockup/*", "/studio/*", "/fonts/*", "/*.png"],
    plugins: [{
      name: "isolated-auth-fixture",
      setup(plugin) {
        // Implement the existing Vite eager raw-HTML macro in this offline
        // bundle; do not approximate its required template documents.
        plugin.onLoad({filter: /\/contentData\.ts$/}, async ({path}) => {
          const folder=resolve("website/elh-preview/blog");
          const documents=Object.fromEntries(await Promise.all(
            (await readdir(folder)).filter(name=>name.endsWith(".html")).map(async name=>[
              "../../../../../../website/elh-preview/blog/"+name, await readFile(join(folder,name),"utf8"),
            ])));
          return {contents:(await readFile(path,"utf8")).replace(
            /import\.meta\.glob<string>\([\s\S]*?\);/, ()=>JSON.stringify(documents)+";"),
            loader:"ts",resolveDir:component};
        });
        plugin.onResolve({filter: /^@clerk\/react$/}, () => ({path:"auth",namespace:"fixture"}));
        plugin.onLoad({filter: /.*/,namespace:"fixture"}, () => ({
          contents: "export const useAuth=()=>({isSignedIn:true,isLoaded:true});export const useClerk=()=>({signOut(){}});",
        }));
      },
    }],
  });
  await writeFile(join(directory,"index.html"), `<html><head><link rel="stylesheet" href="app.css"></head><body>
    <div id="root"></div><script>window.fixtureBase=location.search.includes("workspace=1")?"/__reviews-mockup/":"/studio/";</script>
    <script src="app.js"></script></body></html>`);
  browser=spawn("chromium",["--headless","--no-sandbox","--disable-dev-shm-usage",
    "--remote-debugging-port=0",`--user-data-dir=${join(directory,"profile")}`,"about:blank"],{stdio:"ignore"});
  let port;
  for(let i=0;i<100;i++){try{port=Number((await readFile(join(directory,"profile/DevToolsActivePort"),"utf8")).split("\n")[0]);break;}catch{await sleep(100);}}
  assert.ok(port);
  const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws=new WebSocket(tabs.find(tab=>tab.type==="page").webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener("open",resolve,{once:true});ws.addEventListener("error",reject,{once:true});});
  let id=0;const pending=new Map();const browserErrors=[];
  ws.addEventListener("message",event=>{
    const response=JSON.parse(event.data);const handler=pending.get(response.id);
    if(response.method==="Runtime.exceptionThrown")browserErrors.push(response.params.exceptionDetails);
    if(handler){pending.delete(response.id);response.error?handler.reject(response.error):handler.resolve(response.result);}
  });
  const call=(method,params={})=>new Promise((resolve,reject)=>{
    pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));
  });
  const evaluate=async(expression)=>{
    const result=await call("Runtime.evaluate",{expression,returnByValue:true});
    assert.ok(!result.exceptionDetails,JSON.stringify(result.exceptionDetails));return result.result.value;
  };
  async function until(expression){
    for(let i=0;i<100;i++){if(await evaluate(`Boolean(${expression})`))return;await sleep(100);}
    throw new Error(`Timed out: ${expression}\n${await evaluate("document.body.innerText.slice(-3000)")}\n${JSON.stringify(browserErrors)}`);
  }
  const click=async(label)=>evaluate(`(()=>{const button=[...document.querySelectorAll('[role="dialog"] button')].find(b=>b.textContent.trim()===${JSON.stringify(label)});if(!button||button.disabled)throw new Error("Button unavailable: "+${JSON.stringify(label)});button.click()})()`);
  const file=pathToFileURL(join(directory,"index.html")).href;
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Emulation.setDeviceMetricsOverride",{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await call("Page.navigate",{url:file+"?view=Journal"});
  await until("document.querySelectorAll('.studio-row').length>100");
  await evaluate("document.querySelector('.studio-row').click()");
  await until("document.querySelector('[role=\"dialog\"]')");
  assert.ok(await evaluate(`[...document.querySelectorAll('[role="dialog"] button')].find(b=>b.textContent.includes("Approve complete article")).disabled`));
  await evaluate("approvalFixture.release()");
  await until(`[...document.querySelectorAll('[role="dialog"] button')].some(b=>b.textContent==="Approve complete article"&&!b.disabled)`);
  assert.match(await evaluate(`document.querySelector('[role="dialog"] h1').textContent`),/^Reviewed:/);
  assert.ok(await evaluate(`(()=>{const r=document.querySelector('.review-actions').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()`));
  console.log("PASS article opened before loading receives the current version; actions stay visible");
  await click("Approve complete article");
  assert.equal(await evaluate("approvalFixture.posts.length"),0);
  await click("Cancel");
  assert.equal(await evaluate("approvalFixture.posts.length"),0);
  console.log("PASS inline confirmation and cancellation never use native popups");
  await evaluate("approvalFixture.failNext=409");
  await click("Approve complete article");await click("Confirm approval");
  await until(`document.querySelector('[role="dialog"] [role="alert"]')?.textContent.includes("Article changed")`);
  assert.equal(await evaluate("approvalFixture.posts.length"),1);
  await click("Retry / refresh approvals");
  await until(`[...document.querySelectorAll('[role="dialog"] button')].some(b=>b.textContent==="Approve complete article"&&!b.disabled)`);
  await click("Approve complete article");await click("Confirm approval");
  await until("!document.querySelector('[role=\"dialog\"]')");
  assert.equal(await evaluate("approvalFixture.posts.length"),2);
  assert.deepEqual(await evaluate("approvalFixture.posts.map(p=>p.revision)"),["r1","r2"]);
  console.log("PASS stale-version errors remain in the reader; retry reviews and saves only the current version");
  await evaluate("document.querySelector('.studio-row').click()");
  await until(`document.querySelector('[role="dialog"]')?.textContent.includes("Published version retained")`);
  assert.ok(await evaluate(`[...document.querySelectorAll('[role="dialog"] button')].find(b=>b.textContent.includes("Published version retained")).disabled`));
  console.log("PASS confirmed published status remains after reopening");
  await evaluate(`document.querySelector('[aria-label="Close review"]').click();document.querySelectorAll('.studio-row')[1].click();approvalFixture.failAfterCommit=true`);
  await until(`[...document.querySelectorAll('[role="dialog"] button')].some(b=>b.textContent==="Approve complete article"&&!b.disabled)`);
  await click("Approve complete article");await click("Confirm approval");
  await until(`document.querySelector('[role="dialog"] [role="alert"]')?.textContent.includes("Connection lost")`);
  await click("Retry / refresh approvals");
  await until(`[...document.querySelectorAll('[role="dialog"] button')].some(b=>b.textContent.includes("Published version retained")&&b.disabled)`);
  assert.equal(await evaluate("approvalFixture.posts.length"),3);
  console.log("PASS retry after a lost save response recognizes the saved approval without posting twice");
  await call("Page.navigate",{url:file+"?view=Journal&workspace=1"});
  await until("document.querySelectorAll('.studio-row').length>100");
  await evaluate("approvalFixture.release();document.querySelector('.studio-row').click()");
  await until(`document.querySelector('[role="dialog"]')?.textContent.includes("Workspace review versions loaded")`);
  assert.ok(await evaluate(`[...document.querySelectorAll('[role="dialog"] button')].find(b=>b.textContent.includes("Approve complete article")).disabled`));
  assert.equal(await evaluate(`document.querySelector('[role="dialog"] a').href`),"https://eternallifehospice.com/studio/");
  console.log("PASS workspace cannot misrepresent preview decisions as live approvals");
  await call("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.ok(await evaluate(`(()=>{const r=document.querySelector('.review-actions').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.width<=innerWidth})()`));
  console.log("PASS mobile approval controls fit the viewport");
} finally {
  if(ws)ws.close();
  if(browser&&browser.exitCode===null){browser.kill();await new Promise(resolve=>browser.once("exit",resolve));}
  await rm(directory,{recursive:true,force:true});
}
