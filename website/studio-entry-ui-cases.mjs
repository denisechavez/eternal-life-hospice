// Client-routing fixture only. No credentials, real sessions or approval APIs.
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFile} from "node:fs/promises";
import {join} from "node:path";

export async function checkStudioEntry({build,artifact,directory,call,evaluate,until}) {
  await build({
    stdin:{contents:`
      import React from "react";
      import {createRoot} from "react-dom/client";
      import StudioSession from ${JSON.stringify(join(artifact,"src/StudioSession.tsx"))};
      const root=createRoot(document.getElementById("root"));
      window.entryFixture={signedIn:new URLSearchParams(location.search).has("signedIn"),
        loading:false,failRestart:false};
      window.entryFixture.render=()=>root.render(<StudioSession><div id="journal-fixture">Protected Journal fixture</div></StudioSession>);
      window.entryFixture.render();
    `,loader:"tsx",resolveDir:artifact},
    outfile:join(directory,"studio-entry.js"),bundle:true,format:"esm",jsx:"automatic",
    alias:{react:join(artifact,"node_modules/react"),"react-dom":join(artifact,"node_modules/react-dom")},
    nodePaths:[join(artifact,"node_modules")],
    define:{"import.meta.env.BASE_URL":'"/studio/"',
      "import.meta.env.VITE_CLERK_PUBLISHABLE_KEY":'"fixture"',
      "import.meta.env.VITE_CLERK_PROXY_URL":'""',"process.env.NODE_ENV":'"production"'},
    plugins:[{name:"isolated-entry-auth",setup(plugin){
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
  const server=createServer(async(req,res)=>{
    try {
      const file=req.url?.split("?")[0];
      if(file==="/studio-entry.js"||file==="/studio-entry.css"){
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
    await evaluate(`document.querySelector("a.studio-auth-button").click()`);
    await until(`location.pathname==="/studio/sign-in"&&document.querySelector('input[name="identifier"]')`);
    await evaluate(`entryFixture.provider.routerPush("/studio/sign-in/sso-callback")`);
    await until(`location.pathname==="/studio/sign-in/sso-callback"`);
    assert.ok(await evaluate(`document.body.textContent.includes("Completing secure sign-in")`));
    await evaluate(`document.querySelector("#complete-fixture-signin").click()`);
    await until(`location.pathname==="/studio/preview/elh-marketing-hub/Hub"&&document.querySelector("#journal-fixture")`);
    assert.equal(await evaluate("location.search"),"?view=Journal");
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
  } finally {
    await new Promise(resolve=>server.close(resolve));
  }
}
