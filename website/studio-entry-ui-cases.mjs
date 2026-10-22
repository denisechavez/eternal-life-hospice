// Real StudioSession + App, isolated Clerk/session responses and synthetic
// dynamically imported content. No credentials or production requests.
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFile, writeFile} from "node:fs/promises";
import {join} from "node:path";

export async function checkStudioEntry({build,artifact,directory,call,evaluate,until}) {
  const privateSource=join(directory,"private-review.tsx");
  await writeFile(privateSource,`
    import React from "react";
    window.entryFixture.events.push("private-import");
    export default function Review(){return <div id="journal-fixture">Protected Journal fixture</div>;}
  `);
  await build({
    stdin:{contents:`
      import React from "react";
      import {createRoot} from "react-dom/client";
      import StudioSession from ${JSON.stringify(join(artifact,"src/StudioSession.tsx"))};
      import App from ${JSON.stringify(join(artifact,"src/App.tsx"))};
      const root=createRoot(document.getElementById("root"));
      window.entryFixture={signedIn:new URLSearchParams(location.search).has("signedIn"),
        loading:false,failRestart:false,events:[],
        verification:new URLSearchParams(location.search).get("verification")||"ok"};
      window.fetch=async(url,options)=>{
        if(url!=="/api/studio/session")throw new Error("Unexpected fixture request: "+url);
        const fixture=window.entryFixture;
        fixture.events.push("verify-start");
        fixture.requestOptions={credentials:options.credentials,cache:options.cache};
        if(fixture.verification==="deferred")await new Promise(resolve=>fixture.release=resolve);
        if(fixture.verification==="network")throw new Error("Fixture connection unavailable");
        const status=Number(fixture.verification)||200;
        return {ok:status===200,status,json:async()=>{
          fixture.events.push("verify-response");
          return {verified:fixture.verification!=="malformed"};
        }};
      };
      window.entryFixture.render=()=>root.render(<StudioSession><App/></StudioSession>);
      window.entryFixture.render();
    `,loader:"tsx",resolveDir:artifact},
    outdir:directory,entryNames:"studio-entry",bundle:true,format:"esm",splitting:true,jsx:"automatic",
    chunkNames:"entry-chunks/[name]-[hash]",metafile:true,
    alias:{react:join(artifact,"node_modules/react"),"react-dom":join(artifact,"node_modules/react-dom")},
    nodePaths:[join(artifact,"node_modules")],
    define:{"import.meta.env.BASE_URL":'"/studio/"',
      "import.meta.env.VITE_CLERK_PUBLISHABLE_KEY":'"fixture"',
      "import.meta.env.VITE_CLERK_PROXY_URL":'""',
      "import.meta.env.VITE_DEFAULT_COMPONENT":'""',"process.env.NODE_ENV":'"production"'},
    plugins:[{name:"isolated-entry-auth",setup(plugin){
      plugin.onLoad({filter:/\/\.generated\/mockup-components\.ts$/},()=>({
        contents:`export const modules={"./components/mockups/elh-marketing-hub/Hub.tsx":()=>import(${JSON.stringify(privateSource)})};`,
        loader:"ts",resolveDir:artifact
      }));
      plugin.onResolve({filter:/^@clerk\/react(?:\/internal)?$/},args=>({path:args.path,namespace:"entry-auth"}));
      plugin.onLoad({filter:/.*/,namespace:"entry-auth"},args=>({
        contents:args.path.endsWith("/internal")?"export const publishableKeyFromHost=()=> 'fixture';":`
          import React from "react";
          export function ClerkProvider(props){window.entryFixture.provider=props;return props.children;}
          export const useAuth=()=>({isLoaded:!window.entryFixture.loading,isSignedIn:window.entryFixture.signedIn});
          export const ClerkLoading=({children})=>window.entryFixture.loading?children:null;
          export const Show=({when,children})=>(when==="signed-in"===window.entryFixture.signedIn)?children:null;
          export function SignIn(){return React.createElement("div",null,
            React.createElement("input",{name:"identifier",type:"email"}),
            React.createElement("button",{id:"complete-fixture-signin",onClick:()=>{
              window.entryFixture.signedIn=true;window.entryFixture.render();
            }},"Complete fixture sign-in"));}
          export const SignUp=SignIn;
          export const useClerk=()=>({signOut:async options=>{
            if(window.entryFixture.failRestart)throw new Error("Fixture sign-out unavailable");
            window.entryFixture.signedIn=false;
            window.entryFixture.provider.routerReplace(options.redirectUrl);
            window.entryFixture.render();
          }});
        `,loader:"js",resolveDir:artifact
      }));
    }}]
  });
  const privateRequests=[];
  const server=createServer(async(req,res)=>{
    try {
      const file=req.url?.split("?")[0];
      if(file==="/studio-entry.js"||file==="/studio-entry.css"||/^\/entry-chunks\/[\w-]+\.js$/.test(file)){
        if(file.includes("/private-review-"))privateRequests.push(file);
        res.setHeader("Content-Type",file.endsWith(".css")?"text/css":"application/javascript");
        res.end(await readFile(join(directory,file.slice(1))));return;
      }
      res.setHeader("Content-Type","text/html");
      res.end('<!doctype html><html><head><link rel="stylesheet" href="/studio-entry.css"></head><body><div id="root"></div><script type="module" src="/studio-entry.js"></script></body></html>');
    } catch {res.statusCode=500;res.end("Fixture unavailable");}
  });
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  const origin=`http://127.0.0.1:${server.address().port}`;
  try {
    await call("Page.navigate",{url:origin+"/studio/"});
    await until(`document.querySelector("a.studio-auth-button")`);
    assert.equal(await evaluate(`getComputedStyle(document.querySelector(".studio-auth-button")).backgroundColor`),"rgb(56, 27, 55)");
    assert.equal(await evaluate(`getComputedStyle(document.querySelector(".studio-auth-button")).color`),"rgb(255, 250, 245)");
    assert.equal(privateRequests.length,0);
    await evaluate(`document.querySelector("a.studio-auth-button").click()`);
    await until(`location.pathname==="/studio/sign-in"&&document.querySelector('input[name="identifier"]')`);
    await evaluate(`entryFixture.provider.routerPush("/studio/sign-in/sso-callback")`);
    await until(`location.pathname==="/studio/sign-in/sso-callback"`);
    assert.ok(await evaluate(`document.body.textContent.includes("Completing secure sign-in")`));
    await evaluate(`document.querySelector("#complete-fixture-signin").click()`);
    await until(`location.pathname==="/studio/preview/elh-marketing-hub/Hub"&&document.querySelector("#journal-fixture")`);
    assert.equal(await evaluate("location.search"),"?view=Journal");
    assert.deepEqual(await evaluate("entryFixture.events"),["verify-start","verify-response","private-import"]);
    console.log("PASS OAuth callback and completed sign-in reach Journal without a doubled Studio path");

    for(const route of ["/studio/","/studio/sign-in","/studio/sign-in/sso-callback","/studio/sign-up"]){
      await call("Page.navigate",{url:origin+route+"?signedIn=1"});
      await until(`document.querySelector("#journal-fixture")&&location.pathname==="/studio/preview/elh-marketing-hub/Hub"`);
    }
    console.log("PASS existing signed-in sessions leave welcome, login and callback screens instead of spinning");

    await call("Page.navigate",{url:origin+"/studio/sign-in/sso-callback"});
    await until(`document.querySelector(".studio-auth-restart")`);
    assert.equal(await evaluate(`Boolean(document.querySelector("#journal-fixture"))`),false);
    await evaluate(`entryFixture.failRestart=true;document.querySelector(".studio-auth-restart").click()`);
    await until(`document.querySelector('[role="alert"]')?.textContent.includes("could not be restarted")`);
    await evaluate(`entryFixture.failRestart=false;document.querySelector(".studio-auth-restart").click()`);
    await until(`location.pathname==="/studio/sign-in"&&document.querySelector('input[name="identifier"]')`);
    assert.equal(await evaluate(`Boolean(document.querySelector("#journal-fixture"))`),false);
    console.log("PASS interrupted callbacks offer restart, show restart errors and never grant anonymous access");

    const deepLink="/studio/preview/elh-marketing-hub/Hub?view=Journal";
    for(const reviewer of ["reviewer-a","reviewer-b"]){
      privateRequests.length=0;
      await call("Page.navigate",{url:origin+deepLink+"&signedIn="+reviewer+"&verification=deferred"});
      await until(`typeof window.entryFixture?.release==="function"&&document.body.textContent.includes("Verifying secure Studio access")`);
      assert.equal(privateRequests.length,0,"No private import may start before backend verification");
      assert.equal(await evaluate(`Boolean(document.querySelector("#journal-fixture"))`),false);
      assert.deepEqual(await evaluate("entryFixture.requestOptions"),{credentials:"same-origin",cache:"no-store"});
      await evaluate("entryFixture.release()");
      await until(`document.querySelector("#journal-fixture")`);
      assert.deepEqual(await evaluate("entryFixture.events"),["verify-start","verify-response","private-import"]);
      assert.equal(privateRequests.length,1);
      assert.equal(await evaluate("location.pathname+location.search"),deepLink+"&signedIn="+reviewer+"&verification=deferred");
    }
    console.log("PASS authenticated deep links verify the backend before requesting or executing private dynamic JavaScript");

    for(const [verification,message] of [["403","not authorized"],["401","Sign in again"],
      ["503","temporarily unavailable"],["malformed","unexpected response"],["network","Fixture connection unavailable"]]){
      privateRequests.length=0;
      await call("Page.navigate",{url:origin+deepLink+"&signedIn=unapproved&verification="+verification});
      await until(`document.querySelector('[role="alert"]')?.textContent.includes(${JSON.stringify(message)})`);
      assert.equal(privateRequests.length,0);
      assert.equal(await evaluate(`Boolean(document.querySelector("#journal-fixture"))`),false);
      assert.equal(await evaluate(`getComputedStyle(document.querySelector(".studio-auth-button")).backgroundColor`),"rgb(56, 27, 55)");
      if(verification==="403"){
        await evaluate(`entryFixture.failRestart=true;document.querySelector(".studio-auth-restart").click()`);
        await until(`document.querySelector('[role="alert"]')?.textContent.includes("Sign-out failed")`);
        await evaluate(`entryFixture.failRestart=false;document.querySelector(".studio-auth-restart").click()`);
        await until(`location.pathname==="/studio/sign-in"&&document.querySelector('input[name="identifier"]')`);
        assert.equal(privateRequests.length,0);
        await evaluate(`entryFixture.verification="ok";document.querySelector("#complete-fixture-signin").click()`);
      }else{
        await evaluate(`entryFixture.verification="ok";document.querySelector(".studio-auth-button").click()`);
      }
      await until(`document.querySelector("#journal-fixture")`);
      assert.equal(privateRequests.length,1);
    }
    console.log("PASS unauthorized accounts can change accounts; failed verification retries without exposing private content");
    privateRequests.length=0;
    await call("Page.navigate",{url:origin+deepLink});
    await until(`location.pathname==="/studio/sign-in"&&document.querySelector('input[name="identifier"]')`);
    assert.equal(privateRequests.length,0);
    assert.deepEqual(await evaluate("entryFixture.events"),[]);
    console.log("PASS anonymous deep links never verify or load private content; public presentation styles remain available");
  } finally {
    await new Promise(resolve=>server.close(resolve));
  }
}
