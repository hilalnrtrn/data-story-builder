function SummaryCards({ analysis, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const formatNumber = (value) =>
    typeof value === 'number' && Number.isFinite(value)
      ? new Intl.NumberFormat(locale).format(value)
      : copy.notAvailable
  const integrityAttentionCount = analysis.insightIntegrity.filter(
    (evaluation) => ['PASS_WITH_WARNINGS', 'REVIEW_REQUIRED', 'FAIL'].includes(evaluation?.status),
  ).length
  const storyStatus = analysis.storyGeneration?.status
  const storyStatusLabel = copy.storyStatuses?.[storyStatus]
    || storyStatus
    || copy.notAvailable

  const cards = [
    { tone: 'purple', icon: 'insights', label: copy.insights, value: formatNumber(analysis.insights.length), helper: copy.insightsHelper },
    { tone: 'blue', icon: 'relationships', label: copy.relationships, value: formatNumber(analysis.relationships.length), helper: copy.relationshipsHelper },
    { tone: 'green', icon: 'integrity', label: copy.integrityAlerts, value: formatNumber(integrityAttentionCount), helper: copy.integrityAlertsHelper },
    { tone: 'orange', icon: 'hypotheses', label: copy.hypotheses, value: formatNumber(analysis.hypotheses.length), helper: copy.hypothesesHelper },
    { tone: 'pink', icon: 'story', label: copy.storyStatus, value: storyStatusLabel, helper: copy.storyStatusHelper },
  ]

  const icons = {
    insights: <><path d="M5 5v14h14" /><path d="m8 15 3-4 3 2 4-6" /></>,
    relationships: <><circle cx="12" cy="5" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="18" r="2" /><path d="m11 6.75-5 9.5" /><path d="m13 6.75 5 9.5" /><path d="M7 18h10" /></>,
    integrity: <><path d="M12 3.5 19 6.75v5c0 4.1-2.75 7.05-7 8.75-4.25-1.7-7-4.65-7-8.75v-5Z" /><path d="m8.75 12 2.1 2.1 4.4-4.6" /></>,
    hypotheses: <><path d="M9 3.5h6" /><path d="M10 3.5v5.25l-5 8.75a2 2 0 0 0 1.75 3h10.5a2 2 0 0 0 1.75-3l-5-8.75V3.5" /><path d="M7.5 16h9" /></>,
    story: <><path d="M4 5.5c2.5-1.25 5.25-1.25 8 .5v14c-2.75-1.75-5.5-1.75-8-.5Z" /><path d="M20 5.5c-2.5-1.25-5.25-1.25-8 .5v14c2.75-1.75 5.5-1.75 8-.5Z" /></>,
  }

  return (
    <section className="summary-cards-section" aria-labelledby="overview-summary-title">
      <h2 className="visually-hidden" id="overview-summary-title">{copy.title}</h2>
      <div className="summary-card-grid">
        {cards.map((card) => (
          <article className={`summary-card summary-card-${card.tone}`} key={card.label}>
            <div className="summary-card-heading">
              <span className="summary-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  {icons[card.icon]}
                </svg>
              </span>
              <span className="summary-card-label">{card.label}</span>
            </div>
            <strong className="summary-card-value">{card.value}</strong>
            <small>{card.helper}</small>
          </article>
        ))}
      </div>
    </section>
  )
}

export default SummaryCards
