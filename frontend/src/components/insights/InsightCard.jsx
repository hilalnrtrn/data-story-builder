const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)

const TYPE_ICONS = {
  CHANGE: <path d="m4 15 5-5 3 3 7-7m-5 0h5v5" />,
  TREND: <path d="M3 15c3-8 6 4 9-4s5-4 9-4" />,
  ANOMALY: <path d="M3 12h4l2-6 4 12 2-6h6" />,
  CONTRIBUTION: <path d="M6 5v14m0-7h7m0 0 5-5m-5 5 5 5" />,
  CONTRAST: <path d="M4 8h15m-4-4 4 4-4 4M20 16H5m4-4-4 4 4 4" />,
}

const DIRECTION_SYMBOLS = { UP: '↑', DOWN: '↓', STABLE: '→', HIGH: '↑', LOW: '↓' }

function TypeIcon({ type }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {TYPE_ICONS[type] || <circle cx="12" cy="12" r="5" />}
    </svg>
  )
}

function InsightCard({ insight, language, copy, featured = false, selected, onSelect }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const formatScore = (value) => isFiniteNumber(value)
    ? new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : copy.notAvailable
  const formatNumber = (value) => isFiniteNumber(value)
    ? new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value)
    : null
  const formatScaledPercent = (value) => isFiniteNumber(value)
    ? `${value > 0 ? '+' : ''}${formatNumber(value)}%`
    : null
  const formatRatioPercent = (value) => isFiniteNumber(value)
    ? `${new Intl.NumberFormat(locale, {
      style: 'percent',
      maximumFractionDigits: 1,
    }).formatToParts(value).filter(({ type }) => type !== 'percentSign').map(({ value: part }) => part).join('').trim()}%`
    : null
  const formatPeriod = (period) => {
    if (!period || typeof period !== 'object' || Array.isArray(period)) return null
    if (period.previous && period.current) return `${period.previous} → ${period.current}`
    if (period.start && period.end) return `${period.start} → ${period.end}`
    return period.current || period.start || null
  }
  const typeLabel = copy.types[insight.type] || insight.type || copy.notAvailable
  const priorityLabel = copy.priorities[insight.priorityLevel] || insight.priorityLevel || copy.notAvailable
  const direction = copy.directions[insight.direction] || insight.direction || copy.notAvailable
  const context = [insight.segment || insight.dimension, formatPeriod(insight.period)].filter(Boolean).join(' · ')
  const typeClass = String(insight.type || 'unknown').toLowerCase()
  const primarySignal = (() => {
    if (insight.type === 'CHANGE') {
      const value = formatScaledPercent(insight.values?.percentageChange)
      return value ? { symbol: DIRECTION_SYMBOLS[insight.direction] || '→', value } : null
    }
    if (insight.type === 'TREND') return { symbol: DIRECTION_SYMBOLS[insight.direction] || '→', value: direction }
    if (insight.type === 'ANOMALY') {
      const value = formatNumber(insight.values?.observed)
      return value ? { symbol: '!', value, note: copy.primarySignals.observedAnomaly } : { symbol: '!', value: typeLabel }
    }
    if (insight.type === 'CONTRIBUTION') {
      const value = formatRatioPercent(insight.values?.contributionShare)
      return value ? { value: `${value} ${copy.primarySignals.contribution}` } : null
    }
    if (insight.type === 'CONTRAST') {
      const subject = insight.values?.subject
      const comparison = insight.values?.comparison
      const difference = isFiniteNumber(insight.values?.differencePercentagePoints)
        ? `${insight.values.differencePercentagePoints > 0 ? '+' : ''}${formatNumber(insight.values.differencePercentagePoints)} ${copy.percentagePoints}`
        : copy.comparisonResults[insight.values?.comparisonResult]
      if (subject && comparison) return { value: `${subject} ↔ ${comparison}`, note: difference }
      return difference ? { value: difference } : null
    }
    return null
  })()

  return (
    <article className={`insight-explorer-card insight-type-${typeClass}${featured ? ' is-featured' : ''}${selected ? ' is-selected' : ''}`}>
      <div className="insight-card-heading">
        <span className="insight-type-label"><TypeIcon type={insight.type} />{typeLabel}</span>
        <span className={`insight-priority insight-priority-${String(insight.priorityLevel || 'standard').toLowerCase()}`}>
          <span aria-hidden="true" />{priorityLabel}
        </span>
      </div>
      <div className="insight-card-subject"><h3>{insight.metric || copy.notAvailable}</h3></div>
      {primarySignal && (
        <div className="insight-card-primary-signal">
          <div>{primarySignal.symbol && <span aria-hidden="true">{primarySignal.symbol}</span>}<strong>{primarySignal.value}</strong></div>
          {primarySignal.note && <small>{primarySignal.note}</small>}
        </div>
      )}
      {context && <p className="insight-card-context">{context}</p>}
      <dl className="insight-card-scores">
        {featured && <div><dt>{copy.businessPriority}</dt><dd>{formatScore(insight.priorityScore)}</dd></div>}
        <div><dt>{copy.confidence}</dt><dd>{formatScore(insight.confidence)}</dd></div>
      </dl>
      <div className="insight-card-footer">
        <button type="button" className="insight-why-button" aria-pressed={selected} onClick={() => onSelect(insight.id)}>
          {copy.whyAction} <span aria-hidden="true">→</span>
        </button>
      </div>
    </article>
  )
}

export default InsightCard
