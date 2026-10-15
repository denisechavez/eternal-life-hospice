// Test the actual browser module with synthetic fetch/Turnstile transports.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source=await readFile(new URL("./elh-preview/assets/intake-security.js",import.meta.url),"utf8");
const {submit}=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
let requests=[];
let siteKey="";
let failChallenge=false;
let removed=0;
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
await assert.rejects(()=>submit({method:"POST",body:"form-name=elh-family"}),/verification failed/);
assert.equal(requests.length,1);
assert.equal(removed,4);
console.log("PASS Turnstile must finish before submission; failed widgets clean up and never POST");
