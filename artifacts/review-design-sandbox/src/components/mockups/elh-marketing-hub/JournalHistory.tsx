import {useEffect, useRef, useState} from "react";

export type ApprovalHistory = {
  recordEnvironment: "production" | "workspace";
  publishedVersion: {revision: string; date: string} | null;
  preStudioVersion: {revision: string; date: string} | null;
  events: {
    id: string;
    revision: string;
    action: string;
    reviewerId: string;
    reviewerLabel: string;
    reviewerNameSnapshot: string | null;
    occurredAt: string;
    environment: "production" | "workspace" | null;
    source: "audit" | "saved-decision";
  }[];
  nextCursor: string | null;
};

export type LoadHistoryPage = (slug: string, cursor: string | null, signal: AbortSignal) => Promise<ApprovalHistory>;

export default function JournalHistory({slug, revision, loadPage}: {slug: string; revision: string; loadPage: LoadHistoryPage}) {
  const [history, setHistory] = useState<ApprovalHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  const load = async (cursor: string | null) => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true); setError("");
    try {
      const page = await loadPage(slug, cursor, controller.signal);
      if (!controller.signal.aborted) setHistory(previous => ({
        ...page, events: cursor && previous ? [...previous.events, ...page.events] : page.events,
      }));
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Approval history unavailable");
    } finally {
      if (!controller.signal.aborted) {request.current = null; setLoading(false);}
    }
  };
  useEffect(() => {
    setHistory(null);
    void load(null);
    return () => {request.current?.abort(); request.current = null;};
  }, [slug, revision, loadPage]);
  return <section className="journal-history" aria-label="Journal approval history">
    <h3>Approval history</h3>
    {loading && <p role="status">Loading approval history…</p>}
    {error && <p role="alert">{error} <button type="button" disabled={loading} onClick={() => void load(history?.nextCursor ?? null)}>Retry history</button></p>}
    {history && <>
    <p><strong>{history.recordEnvironment === "production" ? "Live production" : "Workspace"} records only.</strong>
      {" "}Workspace decisions do not approve live publication. Saved names reflect the verified account at the time of the decision; current directory labels may change. Recorded account IDs identify the actors.</p>
    <p>Current review version <code>{revision}</code></p>
    {history.publishedVersion ? <p><strong>Published version retained</strong> · Publication date {history.publishedVersion.date}
      <code>{history.publishedVersion.revision}</code>
      {history.publishedVersion.revision !== revision && <span>This is separate from the revised draft under review.</span>}</p>
      : <p>No published version.</p>}
    {history.preStudioVersion && <p><strong>Pre-Studio history · frozen published original</strong> · Publication date {history.preStudioVersion.date}
      <code>{history.preStudioVersion.revision}</code>
      No reviewer approval record exists for this original. Its publication date is not an approval timestamp.</p>}
    {!history.events.length ? <p>No saved Studio decisions for this article.</p> :
      <ol>{history.events.map(event => <li key={event.id}>
        <strong>{event.action === "approve" ? "Approved" : "Held"}{event.source === "saved-decision" ? " · saved decision (no audit event)" : ""}</strong>
        <p>{event.reviewerNameSnapshot
          ? <>{event.reviewerNameSnapshot} · Name saved at decision</>
          : <>Name at decision not recorded</>}
          {event.reviewerLabel !== event.reviewerId && <> · Current directory label: {event.reviewerLabel}</>}
          {" · "}Recorded account <code>{event.reviewerId}</code></p>
        <p><time dateTime={event.occurredAt}>{new Date(event.occurredAt).toLocaleString("en-US", {timeZone: "America/Los_Angeles", timeZoneName: "short"})}</time>
          {" · "}{event.environment === "production" ? "Live production" : event.environment === "workspace" ? "Workspace" : "Event environment not recorded"}</p>
        <code>{event.revision}</code>
        <small>{event.revision === revision ? "Current review version" : event.revision === history.publishedVersion?.revision ? "Published version" : "Earlier version"}</small>
      </li>)}</ol>}
    {history.nextCursor && <button type="button" disabled={loading} onClick={() => void load(history.nextCursor)}>Load older events</button>}
    </>}
  </section>;
}
