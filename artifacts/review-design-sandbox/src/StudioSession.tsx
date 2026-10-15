import { ClerkProvider, SignIn, SignUp, Show, ClerkLoading } from "@clerk/react";
import { publishableKeyFromHost } from "@clerk/shared/keys";
import { Route, Switch, Router as WouterRouter, Redirect } from "wouter";
import type { ReactNode } from "react";

const clerkPubKey = publishableKeyFromHost(
  window.location.hostname,
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,
);
const clerkProxyUrl = import.meta.env.VITE_CLERK_PROXY_URL;
const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
const journalPath = `${basePath}/preview/elh-marketing-hub/Hub?view=Journal`;

export default function StudioSession({children}: {children: ReactNode}) {
  if (!clerkPubKey) return <p>Studio sign-in is unavailable: Clerk is not configured.</p>;
  return <ClerkProvider publishableKey={clerkPubKey} proxyUrl={clerkProxyUrl}
    appearance={{
      options: {logoImageUrl: `${window.location.origin}/assets/logo-eternal-trans.png`},
      variables: {colorPrimary: "#381B37", fontFamily: "Arial, sans-serif"},
    }}
    localization={{signIn: {start: {title: "Sign in to Eternal Studio", subtitle: "Denise and Aleksandra can approve Journal posts using their verified accounts."}}}}>
    <WouterRouter base={basePath}>
      <Switch>
        <Route path="/"><Show when="signed-in"><Redirect to="/preview/elh-marketing-hub/Hub?view=Journal"/></Show><section style={{padding:"4rem",background:"#f5f0eb",minHeight:"100vh",color:"#381B37"}}><img width="176" src="/assets/logo-eternal-trans.png" alt="Eternal Life Hospice"/><h1>Eternal Studio</h1><p>Review and approve complete Journal versions before publication.</p><a href={`${basePath}/sign-in`}>Sign in as the designated reviewer</a></section></Route>
        <Route path="/sign-in/*?"><div style={{display:"grid",placeItems:"center",minHeight:"100vh",background:"#f5f0eb"}}><ClerkLoading><p>Loading secure Studio sign-in…</p></ClerkLoading><SignIn routing="path" path={`${basePath}/sign-in`} forceRedirectUrl={journalPath} signUpUrl={`${basePath}/sign-up`}/></div></Route>
        <Route path="/sign-up/*?"><div style={{display:"grid",placeItems:"center",minHeight:"100vh",background:"#f5f0eb"}}><SignUp routing="path" path={`${basePath}/sign-up`} forceRedirectUrl={journalPath} signInUrl={`${basePath}/sign-in`}/></div></Route>
        <Route>{children}</Route>
      </Switch>
    </WouterRouter>
  </ClerkProvider>;
}
