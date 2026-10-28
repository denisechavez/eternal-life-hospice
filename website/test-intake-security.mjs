// Test the actual browser module with synthetic fetch/Turnstile transports.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {webcrypto} from "node:crypto";
globalThis.crypto ??= webcrypto;
const {default: websitePhone} = await import("./website-phone.cjs");
const source=websitePhone.publicPhoneText(await readFile(new URL("./elh-preview/assets/intake-security.js",import.meta.url),"utf8"));
const {submit}=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
let requests=[];
let siteKey="";
let failChallenge=false;
let removed=0;
const browserProofs = new Set();
globalThis.window={
  setTimeout:(fn,ms)=>setTimeout(fn,ms>=15000?1000:0), clearTimeout,
  turnstile:{
    render(container,options){
      assert.equal(options.action,"intake");
      queueMicrotask(()=>failChallenge?options["error-callback"]():options.callback("synthetic-provider-token"));
      return "synthetic-widget";
    },
    remove(){removed++;}
  }
};
globalThis.document={body:{appendChild(){}},createElement(){
  return {style:{},setAttribute(){},remove(){removed++;}};
}};
globalThis.fetch=async(url,options={})=>{
  requests.push({url,options});
  return new Response(JSON.stringify(url.startsWith("/api/form-security")
    ?{token:"synthetic-signed-token",siteKey,waitMs:0}
    :{ok:true,accepted:true,receipt_id:"SYNTHETIC"}),{status:200});
};
for(const formName of ["elh-family","elh-physician","elh-casemanager","elh-coordinator","elh-chat-callback","elh-voice","elh-care-brief-signup"]){
  requests=[];
  const response=await submit({method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},
    body:new URLSearchParams({"form-name":formName,phone:"2025550190"}).toString()});
  assert.equal(response.status,200);
  assert.equal(requests.length,2);
  assert.equal(requests[0].url,"/api/form-security?form="+formName);
  assert.equal(new URLSearchParams(requests[1].options.body).get("_elh_security"),"synthetic-signed-token");
  const proof = requests[0].options.headers["X-ELH-Intake-Proof"];
  assert.match(proof, /^[a-f0-9]{64}$/);
  assert.ok(!browserProofs.has(proof), "Each attempt must use a fresh proof");
  browserProofs.add(proof);
  assert.equal(new URLSearchParams(requests[1].options.body).get("_elh_browser_proof"),proof);
  assert.equal(new URLSearchParams(requests[1].options.body).get("phone"),"2025550190");
}
const multipart=new FormData();
multipart.set("form-name","elh-physician");
multipart.set("attachment",new Blob(["synthetic content"]),"synthetic.txt");
await submit({method:"POST",body:multipart});
assert.ok(requests.at(-1).options.body instanceof FormData);
assert.equal(requests.at(-1).options.body.get("attachment").name,"synthetic.txt");
console.log("PASS every active form and multipart body receives a signed token without dropping fields");
siteKey="synthetic-site-key";
requests=[];
await submit({method:"POST",body:"form-name=elh-family"});
assert.equal(new URLSearchParams(requests.at(-1).options.body).get("cf-turnstile-response"),"synthetic-provider-token");
assert.equal(removed,2);
failChallenge=true;
requests=[];
await assert.rejects(()=>submit({method:"POST",body:"form-name=elh-family"}),
  error=>error.intakeOutcome==="verification" && /not been sent/.test(error.message));
assert.equal(requests.length,1);
assert.equal(removed,4);
console.log("PASS Turnstile must finish before submission; failed widgets clean up and never POST");

// A server error or unreadable response is not proof of non-delivery.
for (const test of [
  {name:"security network failure", phase:"security", network:true, outcome:"verification"},
  {name:"security invalid JSON", phase:"security", raw:true, outcome:"verification"},
  {name:"security missing token", phase:"security", data:{waitMs:0}, outcome:"verification"},
  {name:"explicit rejection", status:403, data:{ok:false}, outcome:"rejected"},
  {name:"rate rejection", status:429, data:{ok:false}, outcome:"rejected"},
  {name:"server verification outage", status:503, data:{ok:false,error:"security_unavailable"}, outcome:"rejected"},
  {name:"delivery outage", status:502, data:{ok:false,error:"delivery_unavailable"}, outcome:"unknown"},
  {name:"processing error", status:500, data:{ok:false,error:"processing_error"}, outcome:"unknown"},
  {name:"POST network failure", network:true, outcome:"unknown"},
  {name:"POST unreadable response", raw:true, outcome:"unknown"},
  {name:"missing acceptance", data:{ok:true}, outcome:"unknown"},
  {name:"conflicting response", status:503, data:{ok:false,accepted:true}, outcome:"unknown"},
  {name:"accepted without receipt email", data:{ok:true,accepted:true,acknowledgement_sent:false}}
]) {
  requests=[];
  globalThis.fetch=async(url,options={})=>{
    requests.push({url,options});
    const security=url.startsWith("/api/form-security");
    if(security && test.phase!=="security")
      return new Response(JSON.stringify({token:"synthetic-token",siteKey:"",waitMs:0}));
    if(test.network)throw new TypeError("synthetic connection interrupted");
    return new Response(test.raw?"not json":JSON.stringify({...test.data,message:"untrusted copy"}),
      {status:test.status||200});
  };
  if(test.outcome){
    await assert.rejects(()=>submit({method:"POST",body:"form-name=elh-family"}),
      error=>error.intakeOutcome===test.outcome && !error.message.includes("untrusted"),
      test.name);
  } else {
    const response=await submit({method:"POST",body:"form-name=elh-family"});
    assert.equal((await response.json()).acknowledgement_sent,false);
  }
  assert.equal(requests.length,test.phase==="security"?1:2,test.name+": no automatic retry");
}
console.log("PASS verification, explicit rejection, ambiguous delivery and unchanged missing-receipt acceptance");
const realCrypto = globalThis.crypto;
Object.defineProperty(globalThis, "crypto", {configurable:true, value:undefined});
requests=[];
await assert.rejects(()=>submit({method:"POST",body:"form-name=elh-family"}),
  error=>error.intakeOutcome==="verification" && /not been sent/.test(error.message));
assert.equal(requests.length, 0, "Missing secure randomness must fail before GET or POST");
Object.defineProperty(globalThis, "crypto", {configurable:true, value:realCrypto});
console.log("PASS missing secure randomness fails closed without sending a request");

// Ads measurement is tied to confirmed intake responses, never attempts or UI.
let adsConsent = "all";
let adsCalls = [];
globalThis.localStorage = {getItem: () => adsConsent};
globalThis.document.readyState = "complete";
window.gtag = (...args) => adsCalls.push(args);
let intakeStatus = 200;
let intakeResult;
globalThis.fetch = async url => new Response(JSON.stringify(url.startsWith("/api/form-security")
  ? {token:"synthetic-token", siteKey:"", waitMs:0} : intakeResult),
  {status:url.startsWith("/api/form-security") ? 200 : intakeStatus});
const accepted = async (receipt, extra = {}) => {
  intakeStatus = 200;
  intakeResult = {ok:true, accepted:true, receipt_id:receipt, ...extra};
  return submit({method:"POST", body:"form-name=elh-family&email=private%40example.invalid&message=PRIVATE"});
};
await accepted("ADS-SYNTHETIC-1", {acknowledgement_sent:false});
await accepted("ADS-SYNTHETIC-1");
assert.equal(adsCalls.length, 1, "Repeated receipt must not create another Ads conversion");
assert.deepEqual(adsCalls[0], ["event", "conversion", {
  send_to:"AW-18384023405/JC8lCKGQ9qsdEO3el75E", value:1, currency:"USD"
}]);
assert.ok(!/PRIVATE|private|ADS-SYNTHETIC|email|receipt|message/.test(JSON.stringify(adsCalls)));
for (const [status, data] of [
  [403, {ok:false, accepted:false}], [502, {ok:false}],
  [200, {ok:true}], [200, {ok:true, accepted:false}],
  [503, {ok:true, accepted:true}]
]) {
  intakeStatus = status;
  intakeResult = data;
  await assert.rejects(() => submit({method:"POST", body:"form-name=elh-family"}));
  assert.equal(adsCalls.length, 1);
}
adsConsent = "essential";
await accepted("ADS-OPT-OUT");
assert.equal(adsCalls.length, 1, "No conversion without optional-tracking consent");
adsConsent = "all";
assert.equal(adsCalls.length, 1, "Later consent must not replay past submissions");
window.gtag = () => {throw new Error("synthetic tracker outage");};
assert.equal((await accepted("ADS-THROW")).status, 200);
window.gtag = () => Promise.reject(new Error("synthetic asynchronous tracker outage"));
assert.equal((await accepted("ADS-REJECT")).status, 200);
await new Promise(resolve => setTimeout(resolve, 0));
console.log("PASS Google Ads fires once per confirmed receipt, with consent and no entered data; failures never affect intake");

let onLoad;
window.gtag = undefined;
window.addEventListener = (name, callback, options) => {
  assert.equal(name, "load");
  assert.equal(options.once, true);
  onLoad = callback;
};
document.readyState = "loading";
await accepted("ADS-BEFORE-LOAD");
assert.equal(typeof onLoad, "function");
window.gtag = (...args) => adsCalls.push(args);
onLoad();
await new Promise(resolve => setTimeout(resolve, 5));
assert.equal(adsCalls.length, 2, "Confirmed submission waits for the existing Google loader");
window.gtag = undefined;
await accepted("ADS-REVOKED-BEFORE-LOAD");
adsConsent = "essential";
window.gtag = (...args) => adsCalls.push(args);
onLoad();
await new Promise(resolve => setTimeout(resolve, 5));
assert.equal(adsCalls.length, 2, "Consent is rechecked before delayed reporting");
console.log("PASS delayed Google boot and consent revocation do not duplicate or leak conversions");
adsConsent = "all";
document.readyState = "complete";
await accepted(undefined);
assert.equal(adsCalls.length, 3, "Acceptance without a receipt number is still a conversion");
localStorage.getItem = () => {throw new Error("synthetic storage restriction");};
assert.equal((await accepted("ADS-NO-STORAGE")).status, 200);
assert.equal(adsCalls.length, 3, "Unavailable consent storage must suppress conversion");
console.log("PASS missing receipt numbers and restricted consent storage preserve correct intake outcomes");
