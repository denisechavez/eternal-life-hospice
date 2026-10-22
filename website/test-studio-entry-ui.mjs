// Offline authenticated entry regression. Uses real components with isolated
// reviewer fixtures, never actual Clerk sessions or draft-bearing bundles.
// Run: node --experimental-websocket website/test-studio-entry-ui.mjs
import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdtemp,readFile,rm} from "node:fs/promises";
import {spawn} from "node:child_process";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {checkStudioEntry} from "./studio-entry-ui-cases.mjs";

const artifact=resolve("artifacts/review-design-sandbox");
const require=createRequire(join(artifact,"package.json"));
const {build}=require("esbuild");
const {publishableKeyFromHost}=require("@clerk/react/internal");
// Use the installed browser SDK's actual identity derivation, not its fixture.
for(const host of ["eternallifehospice.com","eternal-life-hospice.replit.app"]){
  const key=publishableKeyFromHost(host,"pk_live_"+Buffer.from("unused.example$").toString("base64"));
  assert.equal(Buffer.from(key.slice("pk_live_".length),"base64").toString(),`clerk.${host}$`);
}
console.log("PASS installed Clerk browser SDK derives the matching production issuer for both allowed domains");
const directory=await mkdtemp(join(tmpdir(),"elh-studio-entry-"));
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let browser,ws;
try {
  assert.equal(typeof WebSocket,"function","Run with --experimental-websocket on Node 20");
  browser=spawn("chromium",["--headless","--no-sandbox","--disable-dev-shm-usage",
    "--remote-debugging-port=0",`--user-data-dir=${join(directory,"profile")}`,"about:blank"],{stdio:"ignore"});
  let launchError;
  browser.on("error",error=>{launchError=error});
  let port;
  for(let i=0;i<100;i++){
    if(launchError)throw launchError;
    try{port=Number((await readFile(join(directory,"profile/DevToolsActivePort"),"utf8")).split("\n")[0]);break;}
    catch{await sleep(100);}
  }
  assert.ok(port,"Chromium did not open its debugging port");
  const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws=new WebSocket(tabs.find(tab=>tab.type==="page").webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{
    ws.addEventListener("open",resolve,{once:true});ws.addEventListener("error",reject,{once:true});
  });
  let id=0;
  const pending=new Map(),errors=[];
  ws.addEventListener("message",event=>{
    const result=JSON.parse(event.data),handler=pending.get(result.id);
    if(result.method==="Runtime.exceptionThrown")errors.push(result.params.exceptionDetails);
    if(result.method==="Fetch.requestPaused"){
      const {requestId,request}=result.params;
      const local=new URL(request.url).hostname==="127.0.0.1";
      if(!local)errors.push({message:"Fixture attempted a non-loopback request"});
      void call(local?"Fetch.continueRequest":"Fetch.failRequest",
        local?{requestId}:{requestId,errorReason:"BlockedByClient"})
        .catch(error=>errors.push({message:error.message}));
    }
    if(handler){pending.delete(result.id);clearTimeout(handler.timer);
      result.error?handler.reject(new Error(JSON.stringify(result.error))):handler.resolve(result.result);}
  });
  const call=(method,params={})=>new Promise((resolve,reject)=>{
    const requestId=++id;
    const timer=setTimeout(()=>{pending.delete(requestId);reject(new Error(`Browser command timed out: ${method}`));},15000);
    pending.set(requestId,{resolve,reject,timer});ws.send(JSON.stringify({id:requestId,method,params}));
  });
  const evaluate=async expression=>{
    const result=await call("Runtime.evaluate",{expression,returnByValue:true});
    assert.ok(!result.exceptionDetails,JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until=async expression=>{
    for(let i=0;i<100;i++){if(await evaluate(`Boolean(${expression})`))return;await sleep(50);}
    throw new Error(`Timed out: ${expression}\n${await evaluate("document.body.innerText")}\n${JSON.stringify(errors)}`);
  };
  await call("Page.enable");await call("Runtime.enable");
  // Deny non-loopback traffic even if a fixture accidentally imports a live SDK.
  await call("Fetch.enable",{patterns:[{urlPattern:"*"}]});
  await checkStudioEntry({build,artifact,directory,call,evaluate,until});
  assert.deepEqual(errors,[],"Studio entry raised a browser exception");
  console.log("SENTINEL: test-studio-entry-ui.mjs authenticated checks OK");
} finally {
  if(ws)ws.close();
  if(browser&&browser.exitCode===null&&browser.pid){
    const exited=new Promise(resolve=>browser.once("exit",resolve));browser.kill();await exited;
  }
  await rm(directory,{recursive:true,force:true,maxRetries:5,retryDelay:100});
}
