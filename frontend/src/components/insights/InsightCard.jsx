const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)

const TYPE_SYMBOLS = {
  CHANGE: '↗',
  TREND: '∿',
  ANOMALY: '!',
  CONTRIBUTION: '⑂',
  CONTRAST: '⇄',
}

const DIRECTION_SYMBOLS = {
  UP: '↑',
  DOWN: '↓',
  STABLE: '→',
  HIGH: '↑',
  LOW: '↓',
}

function InsightCard({ insight, language, copy, featured = false, selected, onSelect }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const formatScore = (value) => isFiniteNumber(value)
    ? new Intl.NumberFormat(locale, {
      style: 'percent',
      maximumFractionDigits: 1,
    }).format(value)
    : copy.notAvailable
  const formatScaledPercent = (value) => isFiniteNumber(value)
    ? `${value > 0 ? '+' : ''}${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value)}%`
    : null
  const formatRatioPercent = (value) => isFiniteNumber(value)
    ? new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : null
  const formatPeriod = (period) => {
    if (!period || typeof period !== 'object' || Array.isArray(period)) {
      return copy.notAvailable
    }
    if (period.previous && period.current) return `${period.previous} → ${period.current}`
    if (period.start && period.end) return `${period.start} → ${period.end}`
    return period.current || period.start || copy.notAvailable
  }
  const typeLabel = copy.types[insight.type] || insight.type || copy.notAvailable
  const priorityLabel = copy.priorities[insight.priorityLevel]
    || insight.priorityLevel
    || copy.notAvailable
  const priorityTone = insight.priorityLevel === 'CRITICAL'
    ? 'unhealthy'
    : insight.priorityLevel === 'HIGH'
      ? 'warning'
      : 'neutral-status'
  const direction = copy.directions[insight.direction]
    || insight.direction
    || copy.notAvailable
  const context = [insight.segment || insight.dimension, formatPeriod(insight.period)]
    .filter(Boolean)
    .join(' · ')
  const scores = [
    { key: 'importance', symbol: '★', label: copy.importance, value: insight.importance },
    { key: 'confidence', symbol: '✓', label: copy.confidence, value: insight.confidence },
    { key: 'business', symbol: '◆', label: copy.businessRelevance, value: insight.businessRelevance },
  ]
  const typeClass = String(insight.type || 'unknown').toLowerCase()
  const primarySignal = (() => {
    if (insight.type === 'CHANGE') {
      const value = formatScaledPercent(insight.values?.percentageChange)
      return value ? { symbol: DIRECTION_SYMBOLS[insight.direction] || '→', value } : null
    }
    if (insight.type === 'TREND') {
      return { symbol: insight.direction === 'DOWN' ? '↘' : insight.direction === 'UP' ? '↗' : '→', value: direction }
    }
    if (insight.type === 'ANOMALY') return { symbol: '!', value: typeLabel }
    if (insight.type === 'CONTRIBUTION') {
      const value = formatRatioPercent(insight.values?.contributionShare)
      return value ? { symbol: '◆', value: `${value} ${copy.primarySignals.contribution}` } : null
    }
    if (insight.type === 'CONTRAST') {
      if (isFiniteNumber(insight.values?.differencePercentagePoints)) {
        const value = insight.values.differencePercentagePoints
        return {
          symbol: '⇄',
          value: `${value > 0 ? '+' : ''}${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value)} ${copy.percentagePoints}`,
        }
      }
      const result = copy.comparisonResults[insight.values?.comparisonResult]
      return result ? { symbol: '⇄', value: result } : null
    }
    return null
  })()

  return (
    <article className={`insight-explorer-card insight-type-${typeClass}${featured ? ' is-featured' : ''}${selected ? ' is-selected' : ''}`}>
      <div className="insight-card-heading">
        <span className="insight-type-label">
          <span aria-hidden="true">{TYPE_SYMBOLS[insight.type] || '•'}</span>
          {typeLabel}
        </span>
        <span className={`status ${priorityTone}`}>{priorityLabel}</span>
      </div>

      <div className="insight-card-subject">
        <h3>{insight.metric || copy.notAvailable}</h3>
        <p>{context}</p>
      </div>

      {primarySignal && (
        <div className="insight-card-primary-signal">
          <span aria-hidden="true">{primarySignal.symbol}</span>
          <strong>{primarySignal.value}</strong>
        </div>
      )}

      {featured && (
        <div className="featured-priority-score">
          <span>{copy.businessPriority}</span>
          <strong>{formatScore(insight.priorityScore)}</strong>
        </div>
      )}

      <div className="insight-card-scores">
        {scores.map((score) => (
          <div key={score.key}>
            <div className="insight-score-heading">
              <span><span aria-hidden="true">{score.symbol}</span> {score.label}</span>
              <strong>{formatScore(score.value)}</strong>
            </div>
          </div>
        ))}
      </div>

      <div className="insight-card-footer">
        <button
          type="button"
          className="insight-why-button"
          aria-pressed={selected}
          onClick={() => onSelect(insight.id)}
        >
          {copy.whyAction} <span aria-hidden="true">›</span>
        </button>
      </div>
    </article>
  )
}

export default InsightCard
