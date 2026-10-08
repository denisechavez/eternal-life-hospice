import master from "../../../../../../website/content/seo-keyword-master.json";

/** Coverage evidence and private draft placements, never search-ranking claims. */
export default function KeywordCoverageTracker() {
  return <details className="panel" style={{padding:20}}>
    <summary style={{cursor:"pointer",fontWeight:700}}>
      SEO master coverage tracker · {master.termCount} keyword IDs
    </summary>
    <p>IDs 1–96 retain their original audit. IDs 97–101 are the new Thryv terms.
      Thousand Oaks is a primary market. Natural-intent draft coverage is not
      confirmed publication or exact-phrase completion.</p>
    <p><strong>Nursing priority:</strong> explain assessments, caregiver teaching,
      individualized visits and how 24/7 on-call support differs from continuous
      bedside nursing.</p>
    <p>{master.rankingStatus} The publication keyword lens above is a separate
      editorial word-count tool, not this coverage tracker.</p>
    <div style={{overflowX:"auto"}}>
      <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
        <thead><tr>{["ID","Keyword","Source","Intent / geography","Cycle evidence","Private draft dates"].map(label =>
          <th key={label} style={{padding:10,textAlign:"left"}}>{label}</th>)}</tr></thead>
        <tbody>{master.keywords.map(keyword => <tr key={keyword.id}>
          <td style={{padding:10,borderTop:"1px solid #ddd"}}>{keyword.id}</td>
          <td style={{padding:10,borderTop:"1px solid #ddd"}}>{keyword.phrase}</td>
          <td style={{padding:10,borderTop:"1px solid #ddd"}}>{keyword.source}</td>
          <td style={{padding:10,borderTop:"1px solid #ddd"}}>{keyword.intent}<br/>{keyword.geography}</td>
          <td style={{padding:10,borderTop:"1px solid #ddd"}}>{keyword.cycles.map(cycle =>
            <div key={cycle.cycle}>{cycle.cycle}: {cycle.confirmation}</div>)}</td>
          <td style={{padding:10,borderTop:"1px solid #ddd"}}>
            {keyword.draftDates.length ? keyword.draftDates.join(" · ") : "No new revision in this update"}
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <p>Draft dates reuse existing article dates; they are not new release slots.
      The original 96-term coverage gaps remain open. All revisions require
      Studio review before publication; no ranks have been imported.</p>
  </details>;
}
