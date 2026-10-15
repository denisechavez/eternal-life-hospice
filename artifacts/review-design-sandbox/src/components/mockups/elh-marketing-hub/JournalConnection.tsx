export type JournalConnectionState = {
  live: boolean;
  ready: boolean;
  loading: boolean;
  saving: boolean;
  signedIn: boolean | undefined;
  authLoaded: boolean;
  error: string;
  signInHref: string;
  retry: () => void;
  signOut: () => void;
};

export default function JournalConnection({state}: {state: JournalConnectionState}) {
  return <section className="journal-connection" aria-label="Journal approval connection">
    {!state.live && <p><strong>Workspace preview — not live publishing.</strong> Review drafts here,
      but approve website articles in the live Eternal Studio.</p>}
    <p role="status">{state.saving ? "Saving your decision… Please wait for confirmation."
      : state.loading ? "Loading current article versions and saved approvals…"
      : state.ready ? (state.live ? "Connected to live Journal approvals." : "Workspace review versions loaded.")
      : "Approval is locked until the current article version can be verified."}</p>
    {state.error && <p role="alert"><strong>Approval unavailable:</strong> {state.error}
      {" "}No new approval has been confirmed. Retry to check the saved status.</p>}
    <div className="journal-connection-actions">
      {!state.live && <a className="primary-btn" href="https://eternallifehospice.com/studio/" target="_blank" rel="noopener noreferrer">Open live Studio to approve</a>}
      {state.authLoaded && !state.signedIn && <a className="secondary-btn" href={state.signInHref}>Sign in as the designated reviewer</a>}
      {state.signedIn && <><button className="secondary-btn" disabled={state.loading || state.saving} onClick={state.retry}>Retry / refresh approvals</button>
        <button className="secondary-btn" disabled={state.saving} onClick={state.signOut}>Sign out / change account</button></>}
    </div>
  </section>;
}
