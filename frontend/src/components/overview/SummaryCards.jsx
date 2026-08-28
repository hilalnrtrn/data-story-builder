function SummaryCards({ analysis, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const formatNumber = (value) =>
    typeof value === 'number' && Number.isFinite(value)
      ? new Intl.NumberFormat(locale).format(value)
      : copy.notAvailable
  const formatScore = (value) =>
    typeof value === 'number' && Number.isFinite(value)
      ? `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value)}%`
      : copy.notAvailable

  const priorityFindingCount = analysis.insights.filter(
    (insight) => insight?.priorityLevel === 'CRITICAL' || insight?.priorityLevel === 'HIGH',
  ).length
  const integrityAttentionCount = analysis.insightIntegrity.filter(
    (evaluation) => ['PASS_WITH_WARNINGS', 'REVIEW_REQUIRED', 'FAIL'].includes(evaluation?.status),
  ).length

  const cards = [
    { label: copy.rowsPrepared, value: formatNumber(analysis.rowCount), helper: copy.rowsPreparedHelper },
    { label: copy.columns, value: formatNumber(analysis.columnCount), helper: copy.columnsHelper },
    { label: copy.dataQuality, value: formatScore(analysis.dataQualityScore), helper: copy.dataQualityHelper },
    { label: copy.insights, value: formatNumber(analysis.insights.length), helper: copy.insightsHelper },
    { label: copy.priorityFindings, value: formatNumber(priorityFindingCount), helper: copy.priorityFindingsHelper },
    { label: copy.integrityAttention, value: formatNumber(integrityAttentionCount), helper: copy.integrityAttentionHelper },
  ]

  return (
    <section className="overview-section" aria-labelledby="overview-summary-title">
      <div className="overview-section-heading">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2 id="overview-summary-title">{copy.title}</h2>
        <p>{copy.description}</p>
      </div>
      <div className="summary-card-grid">
        {cards.map((card) => (
          <article className="summary-card" key={card.label}>
            <span className="summary-card-label">{card.label}</span>
            <strong className="summary-card-value">{card.value}</strong>
            <small>{card.helper}</small>
          </article>
        ))}
      </div>
    </section>
  )
}

export default SummaryCards
