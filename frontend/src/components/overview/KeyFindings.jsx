const DISPLAY_LIMIT = 5

const primaryValueFor = (
  finding,
  copy,
  formatNumber,
  formatContributionShare,
) => {
  const values = finding?.values
  if (!values || typeof values !== 'object') return null

  if (finding.type === 'CHANGE') {
    const value = Number.isFinite(values.relativeChange)
      ? values.relativeChange
      : values.percentageChange
    return Number.isFinite(value)
      ? { label: copy.primaryValues.change, value: `${formatNumber(value)}%` }
      : null
  }
  if (finding.type === 'CONTRIBUTION' && Number.isFinite(values.contributionShare)) {
    return {
      label: copy.primaryValues.contribution,
      value: formatContributionShare(values.contributionShare),
    }
  }
  if (finding.type === 'CONTRAST' && Number.isFinite(values.differencePercentagePoints)) {
    return { label: copy.primaryValues.contrast, value: `${formatNumber(values.differencePercentagePoints)} pp` }
  }
  if (finding.type === 'ANOMALY' && Number.isFinite(values.observed)) {
    return { label: copy.primaryValues.anomaly, value: formatNumber(values.observed) }
  }
  if (finding.type === 'TREND' && Number.isFinite(values.endValue)) {
    return { label: copy.primaryValues.trend, value: formatNumber(values.endValue) }
  }
  return null
}

function KeyFindings({ insights, language, copy, compact = false }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const persistedInsights = Array.isArray(insights) ? insights : []
  const rankedInsights = persistedInsights.filter(
    (insight) => insight?.rank !== null && insight?.rank !== undefined,
  )
  const findings = (rankedInsights.length > 0 ? rankedInsights : persistedInsights)
    .slice(0, DISPLAY_LIMIT)
  const formatNumber = (value) => new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  }).format(value)
  const formatContributionShare = (value) => new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(value)
  const formatScore = (value) => (
    Number.isFinite(value)
      ? new Intl.NumberFormat(locale, {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(value)
      : null
  )
  const formatPeriod = (period) => {
    if (!period || typeof period !== 'object') return null
    if (period.previous && period.current) return `${period.previous} → ${period.current}`
    if (period.start && period.end) return `${period.start} → ${period.end}`
    return period.current || period.start || null
  }

  if (findings.length === 0) {
    return (
      <section className={`overview-section key-findings-section${compact ? ' key-findings-compact' : ''}`} aria-labelledby="key-findings-title">
        <div className="overview-section-heading">
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="key-findings-title">{copy.title}</h2>
        </div>
        <div className="overview-inline-empty">
          <h3>{copy.emptyTitle}</h3>
          <p>{copy.emptyDescription}</p>
        </div>
      </section>
    )
  }

  return (
    <section className={`overview-section key-findings-section${compact ? ' key-findings-compact' : ''}`} aria-labelledby="key-findings-title">
      <div className="overview-section-heading">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2 id="key-findings-title">{copy.title}</h2>
        <p>{copy.description}</p>
      </div>

      <ol className="key-findings-list">
        {findings.map((finding, index) => {
          const priorityLabel = copy.priorities[finding.priorityLevel]
            || finding.priorityLevel
            || copy.notAvailable
          const priorityClass = finding.priorityLevel === 'CRITICAL'
            ? 'unhealthy'
            : finding.priorityLevel === 'HIGH'
              ? 'warning'
              : 'neutral-status'
          const primaryValue = primaryValueFor(
            finding,
            copy,
            formatNumber,
            formatContributionShare,
          )
          const period = formatPeriod(finding.period)
          const context = [finding.dimension, finding.segment].filter(Boolean)
          const direction = copy.directions[finding.direction] || finding.direction
          const directionValueClass = finding.direction === 'UP'
            ? 'finding-value-up'
            : finding.direction === 'DOWN'
              ? 'finding-value-down'
              : 'finding-value-neutral'
          const scoreItems = [
            [copy.confidence, formatScore(finding.confidence)],
            [copy.importance, formatScore(finding.importance)],
            [copy.businessRelevance, formatScore(finding.businessRelevance)],
          ].filter(([, value]) => value !== null)
          const displayOrdinal = finding.rank ?? index + 1

          if (compact) {
            return (
              <li className="key-finding-card" key={finding.id}>
                <div
                  className="finding-rank"
                  aria-label={`${finding.rank ? copy.rank : copy.ordinal} ${displayOrdinal}`}
                >
                  #{displayOrdinal}
                </div>
                <div className="finding-compact-identity">
                  <h3>{finding.metric || copy.notAvailable}</h3>
                  {(period || context.length > 0 || direction) && (
                    <p className="finding-context">
                      {[period, ...context, direction].filter(Boolean).join(' · ')}
                    </p>
                  )}
                </div>
                <div className="finding-compact-result">
                  <span className={`status ${priorityClass}`}>{priorityLabel}</span>
                  {primaryValue && (
                    <strong
                      className={directionValueClass}
                      title={`${primaryValue.label}: ${primaryValue.value}`}
                    >
                      {primaryValue.value}
                    </strong>
                  )}
                </div>
              </li>
            )
          }

          return (
            <li className="key-finding-card" key={finding.id}>
              <div
                className="finding-rank"
                aria-label={`${finding.rank ? copy.rank : copy.ordinal} ${displayOrdinal}`}
              >
                #{displayOrdinal}
              </div>
              <div className="finding-content">
                <div className="finding-title-row">
                  <div>
                    <span className="finding-type">
                      {copy.types[finding.type] || finding.type || copy.notAvailable}
                    </span>
                    <h3>{finding.metric || copy.notAvailable}</h3>
                  </div>
                  <span className={`status ${priorityClass}`}>{priorityLabel}</span>
                </div>

                {(period || context.length > 0 || direction) && (
                  <p className="finding-context">
                    {[period, ...context, direction].filter(Boolean).join(' · ')}
                  </p>
                )}

                {primaryValue && (
                  <div className="finding-primary-value">
                    <span>{primaryValue.label}</span>
                    <strong className={directionValueClass}>{primaryValue.value}</strong>
                  </div>
                )}

                {scoreItems.length > 0 && (
                  <dl className="finding-score-grid">
                    {scoreItems.map(([label, value]) => (
                      <div key={label}>
                        <dt>{label}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export default KeyFindings
