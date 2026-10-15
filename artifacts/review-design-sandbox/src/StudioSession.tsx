import { ClerkProvider, SignIn, SignUp, Show, ClerkLoading } from "@clerk/react";
import { publishableKeyFromHost } from "@clerk/react/internal";
import { Route, Switch, Router as WouterRouter, Redirect } from "wouter";
import { useEffect, useState, type ReactNode } from "react";
import "./studio-session.css";

const clerkPubKey = publishableKeyFromHost(
  window.location.hostname,
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,
);
const clerkProxyUrl = import.meta.env.VITE_CLERK_PROXY_URL;
const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
const journalPath = `${basePath}/preview/elh-marketing-hub/Hub?view=Journal`;

function StudioFrame({children}: {children:ReactNode}) {
  return <main className="studio-auth-page"><section className="studio-auth-card">
    <img className="studio-auth-logo" width="176" src="/assets/logo-eternal-trans.png" alt="Eternal Life Hospice"/>
    {children}
  </section></main>;
}

function SignInLoading() {
  const [delayed,setDelayed]=useState(false);
  useEffect(()=>{const timer=window.setTimeout(()=>setDelayed(true),15000);return()=>window.clearTimeout(timer)},[]);
  return <div role="status" className="studio-auth-loading">
    <p>{delayed?"Secure sign-in is taking longer than expected.":"Loading secure Studio sign-in…"}</p>
    {delayed&&<><p>Your articles remain protected. Reload to try the connection again.</p>
      <button className="studio-auth-button" onClick={()=>window.location.reload()}>Reload secure sign-in</button></>}
  </div>;
}

export default function StudioSession({children}: {children: ReactNode}) {
  if (!clerkPubKey) return <StudioFrame><h1>Studio sign-in unavailable</h1><p>The secure sign-in service is not configured. No approvals can be saved.</p></StudioFrame>;
  return <ClerkProvider publishableKey={clerkPubKey} proxyUrl={clerkProxyUrl}
    appearance={{
      options: {logoImageUrl: `${window.location.origin}/assets/logo-eternal-trans.png`},
      variables: {colorPrimary: "#381B37", fontFamily: "Arial, sans-serif"},
      elements: {rootBox: {width: "100%"}, cardBox: {width: "100%", maxWidth: "100%"}},
    }}
    localization={{signIn: {start: {title: "Sign in to Eternal Studio", subtitle: "Denise and Aleksandra can approve Journal posts using their verified accounts."}}}}>
    <WouterRouter base={basePath}>
      <Switch>
        <Route path="/"><Show when="signed-in"><Redirect to="/preview/elh-marketing-hub/Hub?view=Journal"/></Show><StudioFrame>
          <p className="studio-auth-eyebrow">Private editorial workspace</p><h1>Eternal Studio</h1>
          <p>Review Journal articles and approve each complete version before publication.</p>
          <a className="studio-auth-button" href={`${basePath}/sign-in`}>Sign in to Eternal Studio</a>
          <p className="studio-auth-note">Denise and Aleksandra can approve articles using their verified accounts. Your displayed name will come from the account you sign in with.</p>
          <a className="studio-auth-back" href="/">Return to the Eternal Life Hospice website</a>
        </StudioFrame></Route>
        <Route path="/sign-in/*?"><StudioFrame><h1>Sign in to Eternal Studio</h1>
          <p>Use your authorized Eternal Life Hospice account to review and approve Journal articles.</p>
          <ClerkLoading><SignInLoading/></ClerkLoading><SignIn routing="path" path={`${basePath}/sign-in`} forceRedirectUrl={journalPath} signUpUrl={`${basePath}/sign-up`}/>
          <a className="studio-auth-back" href={`${basePath}/`}>Back to Studio welcome</a>
        </StudioFrame></Route>
        <Route path="/sign-up/*?"><StudioFrame><h1>Create your Studio sign-in</h1>
          <p>Creating an account does not grant approval access. Only authorized, verified reviewers can access articles.</p>
          <ClerkLoading><SignInLoading/></ClerkLoading><SignUp routing="path" path={`${basePath}/sign-up`} forceRedirectUrl={journalPath} signInUrl={`${basePath}/sign-in`}/>
          <a className="studio-auth-back" href={`${basePath}/sign-in`}>Already have an account? Sign in</a>
        </StudioFrame></Route>
        <Route>{children}</Route>
      </Switch>
    </WouterRouter>
  </ClerkProvider>;
}
