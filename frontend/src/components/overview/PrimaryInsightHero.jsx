const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)

const TYPE_ICONS = {
  CHANGE: <><path d="M5 17 10 12l3 3 6-8" /><path d="M14 7h5v5" /></>,
  TREND: <><path d="M4 17c3-1 4-7 7-7s4 5 9 2" /><path d="M16 8h4v4" /></>,
  ANOMALY: <><path d="M4 13h4l2-6 4 11 2-5h4" /><circle cx="20" cy="6" r="1" /></>,
  CONTRIBUTION: <><circle cx="6" cy="12" r="2" /><circle cx="18" cy="7" r="2" /><circle cx="18" cy="17" r="2" /><path d="m8 11 8-3M8 13l8 3" /></>,
  CONTRAST: <><path d="M8 5 4 9l4 4" /><path d="M4 9h16" /><path d="m16 19 4-4-4-4" /></>,
}

const rankInsights = (insights) => {
  const persisted = Array.isArray(insights) ? insights : []
  const ranked = persisted.filter((insight) => Number.isInteger(insight?.rank) && insight.rank > 0)
  return ranked.length > 0
    ? [...ranked].sort((left, right) => left.rank - right.rank)
    : persisted
}

const getPrimaryInsight = (insights) => rankInsights(insights)[0] || null

function PrimaryInsightHero({ insights, storyGeneration, language, copy, storyCopy }) {
  const insight = getPrimaryInsight(insights)
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const numberFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 })
  const ratioFormatter = new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 })
  const formatPeriod = (period) => {
    if (!period || typeof period !== 'object') return null
    if (period.previous && period.current) return `${period.previous} → ${period.current}`
    if (period.start && period.end) return `${period.start} → ${period.end}`
    return period.current || period.start || null
  }
  const formatSignal = () => {
    if (!insight) return null
    const values = insight.values || {}
    if (insight.type === 'CHANGE') {
      const value = isFiniteNumber(values.relativeChange) ? values.relativeChange : values.percentageChange
      if (!isFiniteNumber(value)) return copy.types[insight.type]
      const direction = value > 0 ? '↑' : value < 0 ? '↓' : '→'
      return `${value > 0 ? '+' : ''}${numberFormatter.format(value)}% ${direction}`
    }
    if (insight.type === 'TREND') {
      const direction = copy.directions[insight.direction] || insight.direction
      return direction ? `${insight.direction === 'UP' ? '↗' : insight.direction === 'DOWN' ? '↘' : '→'} ${direction}` : copy.types.TREND
    }
    if (insight.type === 'ANOMALY') {
      return isFiniteNumber(values.observed) ? numberFormatter.format(values.observed) : copy.types.ANOMALY
    }
    if (insight.type === 'CONTRIBUTION' && isFiniteNumber(values.contributionShare)) {
      return ratioFormatter.format(values.contributionShare)
    }
    if (insight.type === 'CONTRAST' && isFiniteNumber(values.differencePercentagePoints)) {
      const value = values.differencePercentagePoints
      return `${value > 0 ? '+' : ''}${numberFormatter.format(value)} ${copy.percentagePoints}`
    }
    return copy.types[insight.type] || insight.type || copy.notAvailable
  }
  const signalLabel = {
    CHANGE: copy.primaryValues.change,
    TREND: copy.direction,
    ANOMALY: copy.primaryValues.anomaly,
    CONTRIBUTION: copy.primaryValues.contribution,
    CONTRAST: copy.primaryValues.contrast,
  }[insight?.type]

  if (!insight) {
    return (
      <section className="primary-insight-hero is-empty" aria-labelledby="primary-insight-title">
        <div>
          <p className="overview-kicker">{copy.primarySignal}</p>
          <h2 id="primary-insight-title">{copy.emptyTitle}</h2>
          <p>{copy.emptyDescription}</p>
        </div>
      </section>
    )
  }

  const typeLabel = copy.types[insight.type] || insight.type || copy.notAvailable
  const priorityLabel = copy.priorities[insight.priorityLevel] || insight.priorityLevel
  const context = [formatPeriod(insight.period), insight.dimension, insight.segment].filter(Boolean)
  const storyStatus = storyGeneration?.status
  const storyStatusLabel = storyCopy.storyStatuses?.[storyStatus]
    || storyStatus
    || storyCopy.notAvailable

  return (
    <section className={`primary-insight-hero insight-${String(insight.type || 'unknown').toLowerCase()}`} aria-labelledby="primary-insight-title">
      <div className="primary-insight-content">
        <div className="primary-insight-labels">
          <span className="primary-insight-type">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              {TYPE_ICONS[insight.type]}
            </svg>
            {typeLabel}
          </span>
          {priorityLabel && <span className={`primary-insight-priority priority-${String(insight.priorityLevel || 'standard').toLowerCase()}`}>{priorityLabel}</span>}
        </div>
        <p className="overview-kicker">{copy.primarySignal}</p>
        <h2 id="primary-insight-title">{insight.metric || copy.notAvailable}</h2>
        {signalLabel && <span className="primary-insight-signal-label">{signalLabel}</span>}
        <strong className={`primary-insight-signal direction-${String(insight.direction || 'stable').toLowerCase()}`}>{formatSignal()}</strong>
        {context.length > 0 && <p className="primary-insight-context">{context.join(' · ')}</p>}
      </div>
      <aside className="primary-insight-aside">
        <div className="primary-insight-visual" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
            {TYPE_ICONS[insight.type]}
          </svg>
        </div>
        {Number.isInteger(insight.rank) && insight.rank > 0 && (
          <div className="primary-insight-rank" aria-label={`${copy.rank} ${insight.rank}`}>
            <strong>#{insight.rank}</strong>
          </div>
        )}
        <div className={`hero-story-status story-status-${String(storyStatus || 'unavailable').toLowerCase()}`} role="status">
          <span aria-hidden="true">{storyStatus === 'Succeeded' ? '✓' : storyStatus === 'Failed' ? '!' : '○'}</span>
          {storyStatus === 'Succeeded' ? (
            <strong>{storyCopy.storyReady}</strong>
          ) : (
            <><span>{storyCopy.storyStatus}</span><strong>{storyStatusLabel}</strong></>
          )}
        </div>
      </aside>
    </section>
  )
}

export default PrimaryInsightHero
