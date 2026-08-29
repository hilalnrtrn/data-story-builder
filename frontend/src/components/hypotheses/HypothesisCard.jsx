const count = (value) => Array.isArray(value) ? value.length : null

function HypothesisCard({ hypothesis, language, copy, selected, onSelect }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const confidence = typeof hypothesis?.confidence === 'number' && Number.isFinite(hypothesis.confidence)
    ? new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 2 }).format(hypothesis.confidence)
    : copy.unavailable
  const status = copy.statuses[hypothesis?.status] || hypothesis?.status || copy.unavailable
  const causality = copy.causalityStatuses[hypothesis?.causalityStatus]
    || hypothesis?.causalityStatus
    || copy.unavailable

  return (
    <article className={`hypothesis-card${selected ? ' is-selected' : ''}`}>
      <div className="hypothesis-card-heading">
        <span className="hypothesis-kind"><span aria-hidden="true">◇</span>{copy.possibleExplanation}</span>
        <span className={`hypothesis-status status-${String(hypothesis?.status || 'unknown').toLowerCase()}`}>{status}</span>
      </div>
      <h3>{hypothesis?.statement || copy.unavailable}</h3>
      <dl className="hypothesis-card-metadata">
        <div><dt>{copy.confidenceScore}</dt><dd>{confidence}</dd></div>
        <div><dt>{copy.causality}</dt><dd>{causality}</dd></div>
      </dl>
      <p className="hypothesis-card-sources">{copy.sourceCount.replace('{count}', count(hypothesis?.sourceInsightIds) ?? copy.unavailable)}</p>
      <button type="button" className="hypothesis-open-button" aria-pressed={selected} onClick={() => onSelect(hypothesis.id)}>
        {copy.viewDetails}<span aria-hidden="true">›</span>
      </button>
    </article>
  )
}

export default HypothesisCard
