export function EvidenceList({ evidence }) {
  return <section className="panel"><h2>Evidence</h2><div className="evidence-list">
    {evidence.map((item) => <article className="evidence" key={item.id}>
      <span className={`severity ${item.severity}`}>{item.severity}</span>
      <div><h3>{item.title}</h3><p>{item.description}</p><small>{item.source}</small></div>
    </article>)}
  </div></section>;
}
