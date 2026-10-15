export type ApprovalHistory = {
  recordEnvironment: "production" | "workspace";
  publishedVersion: {revision: string; date: string} | null;
  preStudioVersion: {revision: string; date: string} | null;
  events: {
    revision: string;
    action: string;
    reviewerId: string;
    reviewerLabel: string;
    occurredAt: string;
    environment: "production" | "workspace" | null;
    source: "audit" | "saved-decision";
  }[];
};

export default function JournalHistory({history, revision}: {history: ApprovalHistory; revision: string}) {
  return <section className="journal-history" aria-label="Journal approval history">
    <h3>Approval history</h3>
    <p><strong>{history.recordEnvironment === "production" ? "Live production" : "Workspace"} records only.</strong>
      {" "}Workspace decisions do not approve live publication. Account names below are current directory labels; recorded account IDs identify the actors.</p>
    <p>Current review version <code>{revision}</code></p>
    {history.publishedVersion ? <p><strong>Published version retained</strong> · Publication date {history.publishedVersion.date}
      <code>{history.publishedVersion.revision}</code>
      {history.publishedVersion.revision !== revision && <span>This is separate from the revised draft under review.</span>}</p>
      : <p>No published version.</p>}
    {history.preStudioVersion && <p><strong>Pre-Studio history · frozen published original</strong> · Publication date {history.preStudioVersion.date}
      <code>{history.preStudioVersion.revision}</code>
      No reviewer approval record exists for this original. Its publication date is not an approval timestamp.</p>}
    {!history.events.length ? <p>No saved Studio decisions for this article.</p> :
      <ol>{history.events.map((event, index) => <li key={`${event.occurredAt}-${index}`}>
        <strong>{event.action === "approve" ? "Approved" : "Held"}{event.source === "saved-decision" ? " · saved decision (no audit event)" : ""}</strong>
        <p>{event.reviewerLabel} · Recorded account <code>{event.reviewerId}</code></p>
        <p><time dateTime={event.occurredAt}>{new Date(event.occurredAt).toLocaleString("en-US", {timeZone: "America/Los_Angeles", timeZoneName: "short"})}</time>
          {" · "}{event.environment === "production" ? "Live production" : event.environment === "workspace" ? "Workspace" : "Event environment not recorded"}</p>
        <code>{event.revision}</code>
        <small>{event.revision === revision ? "Current review version" : event.revision === history.publishedVersion?.revision ? "Published version" : "Earlier version"}</small>
      </li>)}</ol>}
  </section>;
}
