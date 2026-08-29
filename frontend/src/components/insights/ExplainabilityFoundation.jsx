const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)

const TYPE_ICONS = {
  CHANGE: <path d="m4 15 5-5 3 3 7-7m-5 0h5v5" />,
  TREND: <path d="M3 15c3-8 6 4 9-4s5-4 9-4" />,
  ANOMALY: <path d="M3 12h4l2-6 4 12 2-6h6" />,
  CONTRIBUTION: <path d="M6 5v14m0-7h7m0 0 5-5m-5 5 5 5" />,
  CONTRAST: <path d="M4 8h15m-4-4 4 4-4 4M20 16H5m4-4-4 4 4 4" />,
}

function TypeIcon({ type }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true">{TYPE_ICONS[type] || <circle cx="12" cy="12" r="5" />}</svg>
}

function InsightHero({ insight, typeLabel, priorityLabel, context, formatNumber, formatRatioPercent, formatScaledPercent, copy }) {
  const signal = (() => {
    if (insight.type === 'CHANGE' && isFiniteNumber(insight.values?.percentageChange)) {
      const value = insight.values.percentageChange
      return { symbol: value > 0 ? '↑' : value < 0 ? '↓' : '→', value: `${value > 0 ? '+' : ''}${formatScaledPercent(value)}` }
    }
    if (insight.type === 'TREND') {
      return { symbol: insight.direction === 'UP' ? '↗' : insight.direction === 'DOWN' ? '↘' : '→', value: copy.directions[insight.direction] || insight.direction }
    }
    if (insight.type === 'ANOMALY' && isFiniteNumber(insight.values?.observed)) {
      return { symbol: '!', value: formatNumber(insight.values.observed), note: copy.observedSignal }
    }
    if (insight.type === 'CONTRIBUTION' && isFiniteNumber(insight.values?.contributionShare)) {
      return { value: `${formatRatioPercent(insight.values.contributionShare)} ${copy.primarySignals.contribution}` }
    }
    if (insight.type === 'CONTRAST') {
      const subject = insight.values?.subject
      const comparison = insight.values?.comparison
      const difference = isFiniteNumber(insight.values?.differencePercentagePoints)
        ? `${insight.values.differencePercentagePoints > 0 ? '+' : ''}${formatNumber(insight.values.differencePercentagePoints)} ${copy.percentagePoints}`
        : null
      if (subject && comparison) return { value: `${subject} ↔ ${comparison}`, note: difference }
      return difference ? { value: difference } : null
    }
    return null
  })()

  return (
    <section className={`fd-e-hero fd-e-type-${String(insight.type || 'unknown').toLowerCase()}`} aria-label={copy.summaryTitle}>
      <div className="fd-e-hero-identifiers">
        <span className="fd-e-type-marker"><TypeIcon type={insight.type} />{typeLabel}</span>
        <span className={`fd-e-priority fd-e-priority-${String(insight.priorityLevel || 'standard').toLowerCase()}`}><i aria-hidden="true" />{priorityLabel}</span>
      </div>
      <h3>{insight.metric || copy.unavailable}</h3>
      {signal ? (
        <div className={`fd-e-primary-signal${insight.type === 'CONTRAST' ? ' is-long' : ''}`}>
          <div>{signal.symbol && <span aria-hidden="true">{signal.symbol}</span>}<strong>{signal.value}</strong></div>
          {signal.note && <small>{signal.note}</small>}
        </div>
      ) : <p className="fd-e-unavailable">{copy.notAvailableForInsight}</p>}
      {context && <p className="fd-e-hero-context">{context}</p>}
      <div className="fd-e-explainability-motif" aria-label={copy.explainabilityPath}>
        <span><i aria-hidden="true" />{copy.signal}</span>
        <b aria-hidden="true" />
        <span><i aria-hidden="true" />{copy.evidence}</span>
        <b aria-hidden="true" />
        <span><i aria-hidden="true" />{copy.verification}</span>
      </div>
    </section>
  )
}

function ValueItem({ label, value, emphasis = false }) {
  return <div className={emphasis ? 'is-emphasis' : ''}><dt>{label}</dt><dd>{value}</dd></div>
}

function WhatHappened({ insight, formatValue, copy }) {
  const value = (field) => formatValue(field, insight.values?.[field])
  const available = (field) => insight.values?.[field] !== null && insight.values?.[field] !== undefined
  let content = null

  if (insight.type === 'CHANGE') {
    content = <><div className="fd-e-value-flow"><ValueItem label={copy.valueFields.previous} value={value('previous')} emphasis /><span aria-hidden="true">→</span><ValueItem label={copy.valueFields.current} value={value('current')} emphasis /></div><dl className="fd-e-supporting-values">{available('absoluteChange') && <ValueItem label={copy.valueFields.absoluteChange} value={value('absoluteChange')} />}{available('percentageChange') && <ValueItem label={copy.valueFields.percentageChange} value={value('percentageChange')} />}</dl></>
  } else if (insight.type === 'TREND') {
    content = <><div className="fd-e-value-flow"><ValueItem label={copy.valueFields.startValue} value={value('startValue')} emphasis /><span aria-hidden="true">→</span><ValueItem label={copy.valueFields.endValue} value={value('endValue')} emphasis /></div><dl className="fd-e-supporting-values"><ValueItem label={copy.direction} value={copy.directions[insight.direction] || insight.direction || copy.unavailable} />{available('periodCount') && <ValueItem label={copy.valueFields.periodCount} value={value('periodCount')} />}</dl></>
  } else if (insight.type === 'ANOMALY') {
    const hasRange = available('lowerBound') && available('upperBound')
    content = <><dl className="fd-e-supporting-values"><ValueItem label={copy.valueFields.observed} value={value('observed')} emphasis />{available('iqr') && <ValueItem label={copy.valueFields.iqr} value={value('iqr')} />}</dl>{hasRange && <div className={`fd-e-anomaly-range is-${String(insight.direction || '').toLowerCase()}`}><div className="fd-e-observed-marker"><span>{copy.valueFields.observed}</span><strong>{value('observed')}</strong></div><div className="fd-e-range-line"><i /><i /></div><div className="fd-e-range-labels"><span>{copy.valueFields.lowerBound}<strong>{value('lowerBound')}</strong></span><span>{copy.referenceRange}</span><span>{copy.valueFields.upperBound}<strong>{value('upperBound')}</strong></span></div></div>}{(available('q1') || available('q3')) && <dl className="fd-e-subordinate-values">{available('q1') && <ValueItem label={copy.valueFields.q1} value={value('q1')} />}{available('q3') && <ValueItem label={copy.valueFields.q3} value={value('q3')} />}</dl>}</>
  } else if (insight.type === 'CONTRIBUTION') {
    content = <dl className="fd-e-supporting-values">{available('segmentAbsoluteChange') && <ValueItem label={copy.valueFields.segmentAbsoluteChange} value={value('segmentAbsoluteChange')} />}{available('totalAbsoluteChange') && <ValueItem label={copy.valueFields.totalAbsoluteChange} value={value('totalAbsoluteChange')} />}{available('contributionShare') && <ValueItem label={copy.valueFields.contributionShare} value={value('contributionShare')} emphasis />}{available('contributorRole') && <ValueItem label={copy.valueFields.contributorRole} value={value('contributorRole')} />}</dl>
  } else if (insight.type === 'CONTRAST') {
    content = <><div className="fd-e-contrast-flow"><ValueItem label={insight.values?.subject || copy.valueFields.subject} value={value('subjectChangePercent')} emphasis /><span aria-hidden="true">↔</span><ValueItem label={insight.values?.comparison || copy.valueFields.comparison} value={value('comparisonChangePercent')} emphasis /></div>{available('differencePercentagePoints') && <dl className="fd-e-supporting-values"><ValueItem label={copy.valueFields.differencePercentagePoints} value={value('differencePercentagePoints')} emphasis /></dl>}</>
  }

  return <section className="fd-e-what-happened" aria-labelledby="what-happened-title"><h3 id="what-happened-title">{copy.whatHappened}</h3>{content || <p className="insight-neutral-copy">{copy.notAvailableForInsight}</p>}</section>
}

function ScoreItem({ label, value, rawValue, tone }) {
  return <div className={`fd-e-trust-score ${tone || ''}`}><div><dt>{label}</dt><dd>{value}</dd></div>{isFiniteNumber(rawValue) && <progress max="1" value={rawValue} aria-label={`${label}: ${value}`} />}</div>
}

function TrustRail({ insight, integrityEvaluation, selectedCausality, formatScore, copy }) {
  const integrityLabel = integrityEvaluation ? copy.integrityStatuses[integrityEvaluation.status] || integrityEvaluation.status : copy.unavailable
  const causalityLabel = selectedCausality ? copy.causalityStatuses[selectedCausality.status] || selectedCausality.status : copy.unavailable
  const integrityTone = integrityEvaluation?.status === 'FAIL' ? 'is-risk' : ['PASS_WITH_WARNINGS', 'REVIEW_REQUIRED'].includes(integrityEvaluation?.status) ? 'is-caution' : integrityEvaluation?.status === 'PASS' ? 'is-positive' : 'is-neutral'
  const causalityTone = selectedCausality?.causalityEstablished === true ? 'is-positive' : ['ASSOCIATION_ONLY', 'CAUSALITY_NOT_ESTABLISHED'].includes(selectedCausality?.status) ? 'is-caution' : 'is-neutral'

  return <aside className="fd-e-trust-rail" aria-labelledby="fd-e-trust-title"><h3 id="fd-e-trust-title">{copy.trustSummary}</h3><dl><ScoreItem label={copy.confidence} value={formatScore(insight.confidence)} rawValue={insight.confidence} tone="is-trust" /><ScoreItem label={copy.importance} value={formatScore(insight.importance)} rawValue={insight.importance} /><ScoreItem label={copy.businessPriority} value={formatScore(insight.priorityScore)} rawValue={insight.priorityScore} tone="is-priority" /><div className={`fd-e-trust-status ${integrityTone}`}><dt>{copy.integrity}</dt><dd>{integrityLabel}</dd></div><div className={`fd-e-trust-status ${causalityTone}`}><dt>{copy.causalityGuard}</dt><dd>{causalityLabel}</dd></div></dl></aside>
}

export { InsightHero, TrustRail, WhatHappened }
