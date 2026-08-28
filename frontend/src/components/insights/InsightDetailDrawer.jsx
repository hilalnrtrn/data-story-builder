import { useEffect, useRef, useState } from 'react'
import { localizeAnalyticsCode, localizeAnalyticsText } from '../../i18n/analyticsText.js'

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)
const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)

const CALCULATION_FIELDS = {
  CHANGE: ['previous', 'current', 'absoluteChange', 'percentageChange'],
  TREND: ['startValue', 'endValue', 'periodCount'],
  ANOMALY: ['observed', 'lowerBound', 'upperBound', 'iqr'],
  CONTRIBUTION: ['segmentAbsoluteChange', 'totalAbsoluteChange', 'contributionShare'],
  CONTRAST: ['subjectChangePercent', 'comparisonChangePercent', 'differencePercentagePoints'],
}

const DETECTION_FIELDS = [
  'method',
  'aggregation',
  'slope',
  'persistenceRatio',
  'persistenceLevel',
  'monotonicMovement',
  'minimumPersistenceThreshold',
  'iqrMultiplier',
  'minimumPeriods',
  'minimumPercentageChange',
  'minimumAbsoluteContributionShare',
  'minimumPercentagePointGap',
]

const EXECUTIVE_FIELDS = {
  CHANGE: ['previous', 'current', 'absoluteChange', 'percentageChange'],
  TREND: ['startValue', 'endValue'],
  ANOMALY: ['observed', 'lowerBound', 'upperBound'],
  CONTRIBUTION: ['segmentAbsoluteChange', 'contributionShare'],
  CONTRAST: ['subjectChangePercent', 'comparisonChangePercent', 'differencePercentagePoints'],
}

function AccordionSection({ id, title, open, onToggle, children }) {
  return (
    <section className="explainability-accordion">
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={`${id}-content`}
          id={`${id}-control`}
          onClick={onToggle}
        >
          <span>{title}</span>
          <span aria-hidden="true">{open ? '−' : '+'}</span>
        </button>
      </h3>
      {open && <div className="explainability-accordion-content" id={`${id}-content`} aria-labelledby={`${id}-control`}>{children}</div>}
    </section>
  )
}

function InsightDetailDrawer({
  insight,
  insights,
  relationships,
  integrityEvaluations,
  causalityEvaluations,
  missingContextEvaluations,
  language,
  copy,
  onClose,
}) {
  const closeButtonRef = useRef(null)
  const [openSections, setOpenSections] = useState(() => new Set(['evidence']))
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'

  useEffect(() => {
    const previousFocus = document.activeElement
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      previousFocus?.focus?.()
    }
  }, [onClose])

  const formatNumber = (value) => isFiniteNumber(value)
    ? new Intl.NumberFormat(locale, { maximumFractionDigits: 4 }).format(value)
    : copy.unavailable
  const formatScaledPercent = (value) => isFiniteNumber(value)
    ? `${formatNumber(value)}%`
    : copy.unavailable
  const formatRatioPercent = (value) => isFiniteNumber(value)
    ? new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : copy.unavailable
  const formatScore = (value) => formatRatioPercent(value)
  const localizeText = (value) => localizeAnalyticsText(value, language)
  const formatPeriod = (period) => {
    if (!isObject(period)) return copy.unavailable
    if (period.previous && period.current) return `${period.previous} → ${period.current}`
    if (period.start && period.end) return `${period.start} → ${period.end}`
    return period.current || period.start || copy.unavailable
  }
  const humanizeKey = (value) => String(value)
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/^./, (character) => character.toUpperCase())
  const formatValue = (field, value) => {
    if (value === null || value === undefined || value === '') return copy.unavailable
    if (field === 'contributionShare') return formatRatioPercent(value)
    if (['percentageChange', 'subjectChangePercent', 'comparisonChangePercent', 'minimumPercentageChange'].includes(field)) {
      return formatScaledPercent(value)
    }
    if (field === 'differencePercentagePoints' || field === 'minimumPercentagePointGap') {
      return isFiniteNumber(value) ? `${formatNumber(value)} ${copy.percentagePoints}` : copy.unavailable
    }
    if (['contributionShare', 'persistenceRatio', 'minimumPersistenceThreshold', 'minimumAbsoluteContributionShare'].includes(field)) {
      return formatRatioPercent(value)
    }
    if (typeof value === 'boolean') return value ? copy.yes : copy.no
    if (typeof value === 'string' && copy.controlledValues[value]) return copy.controlledValues[value]
    return isFiniteNumber(value) ? formatNumber(value) : String(value)
  }
  const valueRows = (fields) => fields
    .filter((field) => insight && insight.values?.[field] !== null && insight.values?.[field] !== undefined)
    .map((field) => ({ field, value: insight.values[field] }))
  const detectionRows = DETECTION_FIELDS
    .filter((field) => insight && insight.detection?.[field] !== null && insight.detection?.[field] !== undefined)
    .map((field) => ({ field, value: insight.detection[field] }))
  const toggleSection = (section) => {
    setOpenSections((current) => {
      const next = new Set(current)
      if (next.has(section)) next.delete(section)
      else next.add(section)
      return next
    })
  }

  const renderReadableValue = (value) => {
    if (value === null || value === undefined || value === '') return copy.unavailable
    if (isFiniteNumber(value)) return formatNumber(value)
    if (typeof value === 'boolean') return value ? copy.yes : copy.no
    if (typeof value === 'string') return value
    if (Array.isArray(value)) {
      const scalarItems = value.filter((item) => ['string', 'number', 'boolean'].includes(typeof item))
      return scalarItems.length === value.length
        ? scalarItems.map((item) => renderReadableValue(item)).join(' · ')
        : copy.itemCount.replace('{count}', value.length)
    }
    if (isObject(value)) {
      const scalarEntries = Object.entries(value).filter(([, item]) => (
        item === null || ['string', 'number', 'boolean'].includes(typeof item)
      ))
      if (scalarEntries.length === 0) return copy.notAvailableForInsight
      return (
        <dl className="evidence-object-value">
          {scalarEntries.map(([key, item]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{renderReadableValue(item)}</dd>
            </div>
          ))}
        </dl>
      )
    }
    return copy.notAvailableForInsight
  }
  const renderEvidenceValue = (value, unit) => {
    if (isFiniteNumber(value) && unit === 'PERCENT') return formatScaledPercent(value)
    if (isFiniteNumber(value) && unit === 'RATIO') return formatRatioPercent(value)
    if (isFiniteNumber(value) && unit === 'PERCENTAGE_POINTS') {
      return `${formatNumber(value)} ${copy.percentagePoints}`
    }
    return renderReadableValue(value)
  }

  if (!insight) {
    return (
      <div className="insight-drawer-backdrop" onMouseDown={onClose}>
        <aside
          className="insight-detail-drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="insight-drawer-unavailable-title"
          onMouseDown={(event) => event.stopPropagation()}
        >
          <button ref={closeButtonRef} type="button" className="insight-drawer-close" aria-label={copy.close} onClick={onClose}>×</button>
          <div className="insight-drawer-unavailable">
            <h2 id="insight-drawer-unavailable-title">{copy.unavailableTitle}</h2>
            <p>{copy.notAvailableForInsight}</p>
          </div>
        </aside>
      </div>
    )
  }

  const typeLabel = copy.types[insight.type] || insight.type || copy.unavailable
  const priorityLabel = copy.priorities[insight.priorityLevel]
    || insight.priorityLevel
    || copy.unavailable
  const calculationRows = valueRows(CALCULATION_FIELDS[insight.type] || [])
  const evidence = Array.isArray(insight.evidence) ? insight.evidence : []
  const relatedRelationships = (Array.isArray(relationships) ? relationships : [])
    .filter((relationship) => (
      relationship?.sourceInsightId === insight.id
      || relationship?.targetInsightId === insight.id
    ))
    .map((relationship) => {
      const relatedInsightId = relationship.sourceInsightId === insight.id
        ? relationship.targetInsightId
        : relationship.sourceInsightId
      const relatedInsight = (Array.isArray(insights) ? insights : [])
        .find((candidate) => candidate?.id === relatedInsightId) || null
      return { relationship, relatedInsightId, relatedInsight }
    })
  const businessDetails = isObject(insight.businessRelevanceDetails)
    ? insight.businessRelevanceDetails
    : null
  const businessComponents = Array.isArray(businessDetails?.components)
    ? businessDetails.components.filter((component) => isObject(component))
    : []
  const businessReasons = Array.isArray(businessDetails?.reasons)
    ? businessDetails.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
    : []
  const priorityDetails = isObject(insight.priorityDetails) ? insight.priorityDetails : null
  const priorityBreakdown = isObject(priorityDetails?.breakdown)
    ? Object.entries(priorityDetails.breakdown).filter(([, value]) => isFiniteNumber(value))
    : []
  const priorityReasons = Array.isArray(priorityDetails?.reasons)
    ? priorityDetails.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
    : []
  const hasBusinessOverview = [
    insight.businessRelevance,
    insight.impactDirection,
    insight.priorityScore,
    insight.priorityLevel,
    insight.rank,
  ].some((value) => value !== null && value !== undefined && value !== '')
  const integrityEvaluation = (Array.isArray(integrityEvaluations) ? integrityEvaluations : [])
    .find((evaluation) => evaluation?.insightId === insight.id) || null
  const integrityReasons = Array.isArray(integrityEvaluation?.reasons)
    ? integrityEvaluation.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
    : []
  const counterEvidence = Array.isArray(integrityEvaluation?.counterEvidence)
    ? integrityEvaluation.counterEvidence.filter((item) => isObject(item))
    : []
  const contradictions = Array.isArray(integrityEvaluation?.contradictions)
    ? integrityEvaluation.contradictions.filter((item) => isObject(item))
    : []
  const consistencyChecks = Array.isArray(integrityEvaluation?.consistencyChecks)
    ? integrityEvaluation.consistencyChecks.filter((item) => isObject(item))
    : []
  const integrityBreakdown = isObject(integrityEvaluation?.integrityBreakdown)
    ? Object.entries(integrityEvaluation.integrityBreakdown).filter(([, value]) => isFiniteNumber(value))
    : []
  const integrityStatusClass = (status) => {
    if (status === 'PASS') return 'is-positive'
    if (status === 'FAIL') return 'is-risk'
    if (status === 'PASS_WITH_WARNINGS' || status === 'REVIEW_REQUIRED') return 'is-caution'
    return 'is-neutral'
  }
  const resolveInsightSummary = (insightId) => {
    const resolved = (Array.isArray(insights) ? insights : [])
      .find((candidate) => candidate?.id === insightId)
    if (!resolved) return insightId || copy.unavailable
    return [copy.types[resolved.type] || resolved.type, resolved.metric, resolved.dimension, resolved.segment]
      .filter(Boolean)
      .join(' · ')
  }
  const selectedRelationshipIds = new Set(
    relatedRelationships.map(({ relationship }) => relationship?.id).filter(Boolean),
  )
  const selectedCausalityEvaluations = (Array.isArray(causalityEvaluations) ? causalityEvaluations : [])
    .filter((evaluation) => (
      selectedRelationshipIds.has(evaluation?.relationshipId)
      || evaluation?.sourceInsightId === insight.id
      || evaluation?.targetInsightId === insight.id
    ))
  const missingContextEvaluation = (Array.isArray(missingContextEvaluations)
    ? missingContextEvaluations
    : [])
    .find((evaluation) => evaluation?.insightId === insight.id) || null
  const missingContextItems = Array.isArray(missingContextEvaluation?.missingContext)
    ? missingContextEvaluation.missingContext.filter((item) => isObject(item))
    : []
  const missingContextReasons = Array.isArray(missingContextEvaluation?.reasons)
    ? missingContextEvaluation.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
    : []
  const contextSummary = isObject(missingContextEvaluation?.contextSummary)
    ? missingContextEvaluation.contextSummary
    : null
  const knownContext = Array.isArray(contextSummary?.known)
    ? contextSummary.known.filter((item) => isObject(item))
    : []
  const unknownContext = Array.isArray(contextSummary?.unknown)
    ? contextSummary.unknown.filter((item) => isObject(item))
    : []
  const executiveRows = valueRows(EXECUTIVE_FIELDS[insight.type] || []).slice(0, 4)
  const selectedCausality = selectedCausalityEvaluations[0] || null
  const primarySignal = (() => {
    if (insight.type === 'CHANGE' && isFiniteNumber(insight.values?.percentageChange)) {
      const value = insight.values.percentageChange
      return `${value > 0 ? '↑ +' : value < 0 ? '↓ ' : '→ '}${formatScaledPercent(value)}`
    }
    if (insight.type === 'TREND') {
      const symbol = insight.direction === 'UP' ? '↗' : insight.direction === 'DOWN' ? '↘' : '→'
      return `${symbol} ${copy.directions[insight.direction] || insight.direction || copy.unavailable}`
    }
    if (insight.type === 'ANOMALY') return `! ${typeLabel}`
    if (insight.type === 'CONTRIBUTION' && isFiniteNumber(insight.values?.contributionShare)) {
      return `◆ ${formatRatioPercent(insight.values.contributionShare)} ${copy.primarySignals.contribution}`
    }
    if (insight.type === 'CONTRAST') {
      if (isFiniteNumber(insight.values?.differencePercentagePoints)) {
        const value = insight.values.differencePercentagePoints
        return `⇄ ${value > 0 ? '+' : ''}${formatNumber(value)} ${copy.percentagePoints}`
      }
      return copy.comparisonResults[insight.values?.comparisonResult] || null
    }
    return null
  })()
  const heroContext = [insight.segment || insight.dimension, formatPeriod(insight.period)]
    .filter(Boolean)
    .join(' · ')
  const considerations = [
    counterEvidence.length > 0
      ? copy.considerations.counterEvidence.replace('{count}', counterEvidence.length)
      : null,
    integrityEvaluation && integrityEvaluation.status !== 'PASS'
      ? copy.integrityStatuses[integrityEvaluation.status] || integrityEvaluation.status
      : null,
    selectedCausality?.associationPresent === true && selectedCausality?.causalityEstablished === false
      ? copy.considerations.causality
      : null,
    missingContextItems.length > 0
      ? copy.considerations.missingContext.replace('{count}', missingContextItems.length)
      : null,
  ].filter(Boolean).slice(0, 4)

  return (
    <div className="insight-drawer-backdrop" onMouseDown={onClose}>
      <aside
        className="insight-detail-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="insight-drawer-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="insight-drawer-header">
          <div>
            <p className="eyebrow">{copy.eyebrow}</p>
            <h2 id="insight-drawer-title">{copy.workspaceTitle}</h2>
          </div>
          <button ref={closeButtonRef} type="button" className="insight-drawer-close" aria-label={copy.close} onClick={onClose}>×</button>
        </header>

        <div className="insight-drawer-body">
          <section className="explainability-hero" aria-label={copy.summaryTitle}>
            <div className="explainability-hero-badges">
              <span>{typeLabel}</span>
              <span className={`status ${insight.priorityLevel === 'CRITICAL' ? 'unhealthy' : insight.priorityLevel === 'HIGH' ? 'warning' : 'neutral-status'}`}>{priorityLabel}</span>
            </div>
            <h3>{insight.metric || copy.unavailable}</h3>
            <p>{heroContext}</p>
            {primarySignal && <strong className="explainability-primary-signal">{primarySignal}</strong>}
            <dl className="explainability-hero-scores">
              <div><dt>{copy.businessPriority}</dt><dd>{formatScore(insight.priorityScore)}</dd></div>
              <div><dt>★ {copy.importance}</dt><dd>{formatScore(insight.importance)}</dd></div>
              <div><dt>✓ {copy.confidence}</dt><dd>{formatScore(insight.confidence)}</dd></div>
            </dl>
          </section>

          <section className="explainability-what-happened" aria-labelledby="what-happened-title">
            <h3 id="what-happened-title">{copy.whatHappened}</h3>
            {executiveRows.length > 0 ? (
              <dl>
                {executiveRows.map(({ field, value }) => (
                  <div key={field}><dt>{copy.valueFields[field] || field}</dt><dd>{formatValue(field, value)}</dd></div>
                ))}
              </dl>
            ) : <p className="insight-neutral-copy">{copy.notAvailableForInsight}</p>}
          </section>

          <section className="explainability-status-grid" aria-label={copy.statusSummary}>
            <article><span aria-hidden="true">✓</span><div><h3>{copy.evidence}</h3><strong>{copy.summaryCards.evidence.replace('{count}', evidence.length)}</strong></div></article>
            <article><span aria-hidden="true">◆</span><div><h3>{copy.businessRelevance}</h3><strong>{formatScore(insight.businessRelevance)}</strong></div></article>
            <article><span aria-hidden="true">{!integrityEvaluation ? '—' : integrityEvaluation.status === 'FAIL' ? '×' : integrityEvaluation.status === 'PASS' ? '✓' : '!'}</span><div><h3>{copy.integrity}</h3><strong>{integrityEvaluation ? copy.integrityStatuses[integrityEvaluation.status] || integrityEvaluation.status : copy.unavailable}</strong></div></article>
            <article><span aria-hidden="true">{!selectedCausality ? '—' : selectedCausality.causalityEstablished ? '✓' : '!'}</span><div><h3>{copy.causalityGuard}</h3><strong>{selectedCausality ? copy.causalityStatuses[selectedCausality.status] || selectedCausality.status : copy.unavailable}</strong></div></article>
          </section>

          {considerations.length > 0 && (
            <section className="explainability-considerations" aria-labelledby="considerations-title">
              <h3 id="considerations-title">{copy.thingsToConsider}</h3>
              <div>{considerations.map((item) => <span key={item}>! {item}</span>)}</div>
            </section>
          )}

          <div className="explainability-accordions">
          <AccordionSection id="evidence" title={copy.accordions.evidence} open={openSections.has('evidence')} onToggle={() => toggleSection('evidence')}>

          <section className="insight-drawer-section" aria-labelledby="calculation-title">
            <h3 id="calculation-title">{copy.calculation}</h3>
            {calculationRows.length > 0 ? (
              <dl className="insight-detail-grid">
                {calculationRows.map(({ field, value }) => (
                  <div key={field}><dt>{copy.valueFields[field] || field}</dt><dd>{formatValue(field, value)}</dd></div>
                ))}
              </dl>
            ) : <p className="insight-neutral-copy">{copy.noCalculation}</p>}

          </section>

          <section className="insight-drawer-section" aria-labelledby="evidence-title">
            <div className="insight-section-heading-row">
              <h3 id="evidence-title">{copy.evidence}</h3>
              <span>{evidence.length}</span>
            </div>

            {isObject(insight.source) && (insight.source.fileName || isFiniteNumber(insight.source.rowCount)) && (
              <dl className="insight-source-context">
                {insight.source.fileName && <div><dt>{copy.sourceFile}</dt><dd>{insight.source.fileName}</dd></div>}
                {isFiniteNumber(insight.source.rowCount) && <div><dt>{copy.sourceRows}</dt><dd>{formatNumber(insight.source.rowCount)}</dd></div>}
              </dl>
            )}

            {evidence.length > 0 ? (
              <ol className="insight-evidence-list">
                {evidence.map((item, index) => (
                  <li key={`${item?.code || 'evidence'}-${index}`}>
                    <div className="insight-evidence-heading">
                      <strong>{localizeText(item?.label) || copy.evidenceItem.replace('{number}', index + 1)}</strong>
                      {item?.code && <code>{item.code}</code>}
                    </div>
                    <div className="insight-evidence-value">{renderEvidenceValue(item?.value, item?.unit)}</div>
                    {item?.unit && <p><span>{copy.unit}:</span> {copy.units[item.unit] || humanizeKey(item.unit)}</p>}
                    <p><span>{copy.parentMetric}:</span> {insight.metric || copy.unavailable}</p>
                    <p><span>{copy.parentPeriod}:</span> {formatPeriod(insight.period)}</p>
                  </li>
                ))}
              </ol>
            ) : <p className="insight-neutral-copy">{copy.noEvidence}</p>}
          </section>
          </AccordionSection>

          <AccordionSection id="relationships" title={copy.accordions.relationships} open={openSections.has('relationships')} onToggle={() => toggleSection('relationships')}>

          <section className="insight-drawer-section" aria-labelledby="relationships-title">
            <div className="insight-section-heading-row">
              <h3 id="relationships-title">{copy.relationships}</h3>
              <span>{relatedRelationships.length}</span>
            </div>

            {relatedRelationships.length > 0 ? (
              <ol className="insight-relationship-list">
                {relatedRelationships.map(({ relationship, relatedInsightId, relatedInsight }) => {
                  const relationshipType = copy.relationshipTypes[relationship.type]
                    || humanizeKey(relationship.type || copy.unavailable)
                  const relatedType = relatedInsight
                    ? copy.types[relatedInsight.type] || relatedInsight.type
                    : null
                  const relatedHeading = relatedInsight
                    ? [relatedType, relatedInsight.metric, relatedInsight.dimension, relatedInsight.segment]
                      .filter(Boolean)
                      .join(' · ')
                    : relatedInsightId || copy.unavailable
                  const reasons = Array.isArray(relationship.reasons)
                    ? relationship.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
                    : []
                  const metadataRows = isObject(relationship.metadata)
                    ? Object.entries(relationship.metadata).filter(([, value]) => (
                      value === null
                      || ['string', 'number', 'boolean'].includes(typeof value)
                      || Array.isArray(value) && value.every((item) => ['string', 'number', 'boolean'].includes(typeof item))
                    ))
                    : []

                  return (
                    <li key={relationship.id}>
                      <div className="insight-relationship-heading">
                        <strong>{relationshipType}</strong>
                        <span>{relationship.type || copy.unavailable}</span>
                      </div>
                      <div className="related-insight-summary">
                        <span>{copy.relatedInsight}</span>
                        <strong>{relatedHeading}</strong>
                        {relatedInsight && <small>{formatPeriod(relatedInsight.period)}</small>}
                      </div>
                      <dl className="relationship-score-grid">
                        <div><dt>{copy.relationshipStrength}</dt><dd>{formatScore(relationship.strength)}</dd></div>
                        <div><dt>{copy.relationshipConfidence}</dt><dd>{formatScore(relationship.confidence)}</dd></div>
                      </dl>
                      {reasons.length > 0 && (
                        <div className="persisted-reason-group">
                          <h4>{copy.relationshipReasons}</h4>
                          <ul>{reasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul>
                        </div>
                      )}
                      {metadataRows.length > 0 && (
                        <div className="relationship-metadata">
                          <h4>{copy.relationshipMetadata}</h4>
                          <dl className="insight-detail-grid">
                            {metadataRows.map(([key, value]) => (
                              <div key={key}>
                                <dt>{copy.metadataFields[key] || humanizeKey(key)}</dt>
                                <dd>{formatValue(key, value)}</dd>
                              </div>
                            ))}
                          </dl>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ol>
            ) : <p className="insight-neutral-copy">{copy.noRelationships}</p>}
          </section>

          <section className="insight-drawer-section" aria-labelledby="business-relevance-title">
            <h3 id="business-relevance-title">{copy.businessRelevance}</h3>

            {hasBusinessOverview ? (
              <dl className="insight-detail-grid business-relevance-overview">
                <div><dt>{copy.businessRelevanceScore}</dt><dd>{formatScore(insight.businessRelevance)}</dd></div>
                <div><dt>{copy.impactDirection}</dt><dd>{copy.impactDirections[insight.impactDirection] || insight.impactDirection || copy.unavailable}</dd></div>
                <div><dt>{copy.priorityScore}</dt><dd>{formatScore(insight.priorityScore)}</dd></div>
                <div><dt>{copy.priorityLevel}</dt><dd>{copy.priorities[insight.priorityLevel] || insight.priorityLevel || copy.unavailable}</dd></div>
                <div><dt>{copy.rank}</dt><dd>{Number.isInteger(insight.rank) && insight.rank > 0 ? `#${insight.rank}` : copy.unavailable}</dd></div>
              </dl>
            ) : <p className="insight-neutral-copy">{copy.noBusinessRelevance}</p>}

            {businessComponents.length > 0 && (
              <div className="business-detail-group">
                <h4>{copy.relevanceComponents}</h4>
                <div className="business-component-list">
                  {businessComponents.map((component, index) => (
                    <article key={`${component.name || 'component'}-${index}`}>
                      <div>
                        <strong>{copy.componentNames[component.name] || humanizeKey(component.name || copy.component)}</strong>
                        <span>{formatScore(component.score)}</span>
                      </div>
                      {typeof component.reason === 'string' && component.reason.trim() && <p>{localizeText(component.reason)}</p>}
                    </article>
                  ))}
                </div>
              </div>
            )}

            {businessReasons.length > 0 && (
              <div className="persisted-reason-group business-detail-group">
                <h4>{copy.businessReasons}</h4>
                <ul>{businessReasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul>
              </div>
            )}

            {(priorityBreakdown.length > 0 || priorityReasons.length > 0) && (
              <div className="business-detail-group priority-detail-group">
                <h4>{copy.priorityDetails}</h4>
                {priorityBreakdown.length > 0 && (
                  <dl className="insight-detail-grid">
                    {priorityBreakdown.map(([key, value]) => (
                      <div key={key}><dt>{copy.priorityBreakdownFields[key] || humanizeKey(key)}</dt><dd>{formatScore(value)}</dd></div>
                    ))}
                  </dl>
                )}
                {priorityReasons.length > 0 && (
                  <div className="persisted-reason-group">
                    <h4>{copy.priorityReasons}</h4>
                    <ul>{priorityReasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </section>
          </AccordionSection>

          <AccordionSection id="integrity" title={copy.accordions.integrity} open={openSections.has('integrity')} onToggle={() => toggleSection('integrity')}>

          <section className="insight-drawer-section integrity-detail-section" aria-labelledby="integrity-detail-title">
            <h3 id="integrity-detail-title">{copy.integrity}</h3>

            {!integrityEvaluation ? (
              <p className="insight-neutral-copy">{copy.noIntegrityEvaluation}</p>
            ) : (
              <>
                <div className="integrity-detail-overview">
                  <div className={`integrity-status-chip ${integrityStatusClass(integrityEvaluation.status)}`}>
                    <span>{copy.integrityStatus}</span>
                    <strong>{copy.integrityStatuses[integrityEvaluation.status] || integrityEvaluation.status || copy.unavailable}</strong>
                  </div>
                  <dl className="insight-detail-grid">
                    <div><dt>{copy.integrityScore}</dt><dd>{formatRatioPercent(integrityEvaluation.integrityScore)}</dd></div>
                    <div><dt>{copy.storyEligible}</dt><dd>{typeof integrityEvaluation.storyEligible === 'boolean' ? (integrityEvaluation.storyEligible ? copy.yes : copy.no) : copy.unavailable}</dd></div>
                    <div><dt>{copy.qualificationRequired}</dt><dd>{typeof integrityEvaluation.requiresQualification === 'boolean' ? (integrityEvaluation.requiresQualification ? copy.yes : copy.no) : copy.unavailable}</dd></div>
                  </dl>
                </div>

                <ul className="integrity-checklist" aria-label={copy.integrityChecklist}>
                  <li><span>{copy.counterEvidence}</span><strong>{counterEvidence.length > 0 ? `! ${counterEvidence.length}` : `✓ ${copy.none}`}</strong></li>
                  <li><span>{copy.contradictions}</span><strong>{contradictions.length > 0 ? `! ${contradictions.length}` : `✓ ${copy.none}`}</strong></li>
                  <li><span>{copy.outlierCheck}</span><strong>{isObject(integrityEvaluation.outlierCheck) ? copy.riskLevels[integrityEvaluation.outlierCheck.level] || integrityEvaluation.outlierCheck.level : `— ${copy.notApplicableShort}`}</strong></li>
                  <li><span>{copy.oneOffCheck}</span><strong>{isObject(integrityEvaluation.oneOffCheck) ? copy.riskLevels[integrityEvaluation.oneOffCheck.risk] || integrityEvaluation.oneOffCheck.risk : `— ${copy.notApplicableShort}`}</strong></li>
                  <li><span>{copy.dataConsistency}</span><strong>{consistencyChecks.some((check) => check.status === 'FAIL') ? `× ${copy.checkStatuses.FAIL}` : `✓ ${copy.checkCount.replace('{count}', consistencyChecks.length)}`}</strong></li>
                </ul>

                {integrityReasons.length > 0 && (
                  <div className="persisted-reason-group integrity-subsection">
                    <h4>{copy.integrityReasons}</h4>
                    <ul>{integrityReasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul>
                  </div>
                )}

                {integrityBreakdown.length > 0 && (
                  <div className="integrity-subsection">
                    <h4>{copy.integrityBreakdown}</h4>
                    <dl className="insight-detail-grid">
                      {integrityBreakdown.map(([key, value]) => (
                        <div key={key}><dt>{copy.integrityBreakdownFields[key] || humanizeKey(key)}</dt><dd>{formatRatioPercent(value)}</dd></div>
                      ))}
                    </dl>
                  </div>
                )}

                <div className="integrity-subsection">
                  <div className="insight-section-heading-row"><h4>{copy.counterEvidence}</h4><span>{counterEvidence.length}</span></div>
                  {counterEvidence.length > 0 ? (
                    <ol className="integrity-record-list">
                      {counterEvidence.map((item, index) => {
                        const relationship = (Array.isArray(relationships) ? relationships : [])
                          .find((candidate) => candidate?.id === item.relationshipId)
                        const reasons = Array.isArray(item.reasons)
                          ? item.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
                          : []
                        return (
                          <li key={`${item.insightId || 'counter'}-${item.relationshipId || index}`}>
                            <strong>{copy.relatedCounterSignal}</strong>
                            <dl className="insight-detail-grid">
                              {item.insightId && <div><dt>{copy.relatedInsight}</dt><dd>{resolveInsightSummary(item.insightId)}</dd></div>}
                              {item.relationshipId && <div><dt>{copy.relationship}</dt><dd>{relationship ? (copy.relationshipTypes[relationship.type] || relationship.type || item.relationshipId) : item.relationshipId}</dd></div>}
                              {item.metric && <div><dt>{copy.metric}</dt><dd>{item.metric}</dd></div>}
                              {item.direction && <div><dt>{copy.direction}</dt><dd>{copy.directions[item.direction] || item.direction}</dd></div>}
                            </dl>
                            {reasons.length > 0 && <ul className="integrity-reason-list">{reasons.map((reason, reasonIndex) => <li key={reasonIndex}>{localizeText(reason)}</li>)}</ul>}
                          </li>
                        )
                      })}
                    </ol>
                  ) : <p className="insight-neutral-copy">{copy.noCounterEvidence}</p>}
                </div>

                <div className="integrity-subsection">
                  <div className="insight-section-heading-row"><h4>{copy.contradictions}</h4><span>{contradictions.length}</span></div>
                  {contradictions.length > 0 ? (
                    <ol className="integrity-record-list">
                      {contradictions.map((item, index) => (
                        <li key={`${item.code || item.type || 'contradiction'}-${index}`}>
                          <div className="integrity-record-heading">
                            <strong>{copy.contradictionTypes[item.type] || item.type || copy.unavailable}</strong>
                            {item.code && <code>{item.code}</code>}
                          </div>
                          {item.relatedInsightId && <p><span>{copy.relatedInsight}:</span> {resolveInsightSummary(item.relatedInsightId)}</p>}
                          {item.reason && <p>{localizeText(item.reason)}</p>}
                        </li>
                      ))}
                    </ol>
                  ) : <p className="insight-neutral-copy integrity-none-state">{copy.noContradictions}</p>}
                </div>

                <div className="integrity-subsection">
                  <h4>{copy.outlierCheck}</h4>
                  {isObject(integrityEvaluation.outlierCheck) ? (
                    <dl className="insight-detail-grid">
                      {integrityEvaluation.outlierCheck.level && <div><dt>{copy.level}</dt><dd>{copy.riskLevels[integrityEvaluation.outlierCheck.level] || integrityEvaluation.outlierCheck.level}</dd></div>}
                      {typeof integrityEvaluation.outlierCheck.detected === 'boolean' && <div><dt>{copy.detected}</dt><dd>{integrityEvaluation.outlierCheck.detected ? copy.yes : copy.no}</dd></div>}
                      {integrityEvaluation.outlierCheck.statisticName && <div><dt>{copy.statistic}</dt><dd>{integrityEvaluation.outlierCheck.statisticName}</dd></div>}
                      {isFiniteNumber(integrityEvaluation.outlierCheck.originalStatistic) && <div><dt>{copy.originalStatistic}</dt><dd>{formatNumber(integrityEvaluation.outlierCheck.originalStatistic)}</dd></div>}
                      {isFiniteNumber(integrityEvaluation.outlierCheck.adjustedStatistic) && <div><dt>{copy.adjustedStatistic}</dt><dd>{formatNumber(integrityEvaluation.outlierCheck.adjustedStatistic)}</dd></div>}
                      {integrityEvaluation.outlierCheck.outlierPeriod && <div><dt>{copy.outlierPeriod}</dt><dd>{integrityEvaluation.outlierCheck.outlierPeriod}</dd></div>}
                      {integrityEvaluation.outlierCheck.reason && <div className="integrity-grid-wide"><dt>{copy.reason}</dt><dd>{localizeText(integrityEvaluation.outlierCheck.reason)}</dd></div>}
                    </dl>
                  ) : <p className="insight-neutral-copy">{copy.notApplicable}</p>}
                </div>

                <div className="integrity-subsection">
                  <h4>{copy.oneOffCheck}</h4>
                  {isObject(integrityEvaluation.oneOffCheck) ? (
                    <dl className="insight-detail-grid">
                      {integrityEvaluation.oneOffCheck.risk && <div><dt>{copy.risk}</dt><dd>{copy.riskLevels[integrityEvaluation.oneOffCheck.risk] || integrityEvaluation.oneOffCheck.risk}</dd></div>}
                      {integrityEvaluation.oneOffCheck.eventPeriod && <div><dt>{copy.eventPeriod}</dt><dd>{integrityEvaluation.oneOffCheck.eventPeriod}</dd></div>}
                      {integrityEvaluation.oneOffCheck.nextPeriod && <div><dt>{copy.nextPeriod}</dt><dd>{integrityEvaluation.oneOffCheck.nextPeriod}</dd></div>}
                      {isFiniteNumber(integrityEvaluation.oneOffCheck.baselineValue) && <div><dt>{copy.baselineValue}</dt><dd>{formatNumber(integrityEvaluation.oneOffCheck.baselineValue)}</dd></div>}
                      {isFiniteNumber(integrityEvaluation.oneOffCheck.eventValue) && <div><dt>{copy.eventValue}</dt><dd>{formatNumber(integrityEvaluation.oneOffCheck.eventValue)}</dd></div>}
                      {isFiniteNumber(integrityEvaluation.oneOffCheck.nextValue) && <div><dt>{copy.nextValue}</dt><dd>{formatNumber(integrityEvaluation.oneOffCheck.nextValue)}</dd></div>}
                      {isFiniteNumber(integrityEvaluation.oneOffCheck.reversionRatio) && <div><dt>{copy.reversionRatio}</dt><dd>{formatRatioPercent(integrityEvaluation.oneOffCheck.reversionRatio)}</dd></div>}
                      {integrityEvaluation.oneOffCheck.reason && <div className="integrity-grid-wide"><dt>{copy.reason}</dt><dd>{localizeText(integrityEvaluation.oneOffCheck.reason)}</dd></div>}
                    </dl>
                  ) : <p className="insight-neutral-copy">{copy.notApplicable}</p>}
                </div>

                <div className="integrity-subsection">
                  <div className="insight-section-heading-row"><h4>{copy.dataConsistency}</h4><span>{consistencyChecks.length}</span></div>
                  {consistencyChecks.length > 0 ? (
                    <ol className="integrity-record-list">
                      {consistencyChecks.map((check, index) => (
                        <li key={`${check.code || 'consistency'}-${index}`}>
                          <div className="integrity-record-heading">
                            <strong>{check.code || copy.consistencyCheck}</strong>
                            {check.status && <span className={`integrity-mini-status ${integrityStatusClass(check.status === 'WARNING' ? 'PASS_WITH_WARNINGS' : check.status)}`}>{copy.checkStatuses[check.status] || check.status}</span>}
                          </div>
                          <dl className="insight-detail-grid">
                            {isFiniteNumber(check.expectedValue) && <div><dt>{copy.expected}</dt><dd>{formatNumber(check.expectedValue)}</dd></div>}
                            {isFiniteNumber(check.actualValue) && <div><dt>{copy.actual}</dt><dd>{formatNumber(check.actualValue)}</dd></div>}
                            {isFiniteNumber(check.difference) && <div><dt>{copy.difference}</dt><dd>{formatNumber(check.difference)}</dd></div>}
                            {isFiniteNumber(check.tolerance) && <div><dt>{copy.tolerance}</dt><dd>{formatNumber(check.tolerance)}</dd></div>}
                          </dl>
                          {check.reason && <p>{localizeText(check.reason)}</p>}
                        </li>
                      ))}
                    </ol>
                  ) : <p className="insight-neutral-copy integrity-none-state">{copy.noConsistencyChecks}</p>}
                </div>
              </>
            )}
          </section>
          </AccordionSection>

          <AccordionSection id="limitations" title={copy.accordions.limitations} open={openSections.has('limitations')} onToggle={() => toggleSection('limitations')}>

          <section className="insight-drawer-section" aria-labelledby="causality-guard-title">
            <div className="insight-section-heading-row">
              <h3 id="causality-guard-title">{copy.causalityGuard}</h3>
              <span>{selectedCausalityEvaluations.length}</span>
            </div>

            {selectedCausalityEvaluations.length > 0 ? (
              <ol className="causality-evaluation-list">
                {selectedCausalityEvaluations.map((evaluation, index) => {
                  const relationship = (Array.isArray(relationships) ? relationships : [])
                    .find((candidate) => candidate?.id === evaluation.relationshipId)
                  const causalEvidence = Array.isArray(evaluation.causalEvidence)
                    ? evaluation.causalEvidence.filter((item) => isObject(item))
                    : []
                  const reasons = Array.isArray(evaluation.reasons)
                    ? evaluation.reasons.filter((reason) => typeof reason === 'string' && reason.trim())
                    : []
                  const allowedConcepts = Array.isArray(evaluation.allowedConcepts)
                    ? evaluation.allowedConcepts.filter((item) => typeof item === 'string' && item.trim())
                    : []
                  const forbiddenConcepts = Array.isArray(evaluation.forbiddenConcepts)
                    ? evaluation.forbiddenConcepts.filter((item) => typeof item === 'string' && item.trim())
                    : []
                  const associationWithoutCausality = evaluation.associationPresent === true
                    && evaluation.causalityEstablished === false

                  return (
                    <li key={evaluation.relationshipId || index}>
                      <div className="integrity-record-heading">
                        <strong>{copy.causalityStatuses[evaluation.status] || humanizeKey(evaluation.status || copy.unavailable)}</strong>
                        {relationship?.type && <span className="causality-relationship-type">{copy.relationshipTypes[relationship.type] || relationship.type}</span>}
                      </div>

                      {associationWithoutCausality && (
                        <p className="causality-distinction" role="note">{copy.associationWithoutCausality}</p>
                      )}

                      <dl className="insight-detail-grid">
                        <div><dt>{copy.associationPresent}</dt><dd>{typeof evaluation.associationPresent === 'boolean' ? (evaluation.associationPresent ? copy.yes : copy.no) : copy.unavailable}</dd></div>
                        <div><dt>{copy.causalityEstablished}</dt><dd>{typeof evaluation.causalityEstablished === 'boolean' ? (evaluation.causalityEstablished ? copy.yes : copy.no) : copy.unavailable}</dd></div>
                        {evaluation.sourceMetric && <div><dt>{copy.sourceMetric}</dt><dd>{evaluation.sourceMetric}</dd></div>}
                        {evaluation.targetMetric && <div><dt>{copy.targetMetric}</dt><dd>{evaluation.targetMetric}</dd></div>}
                        {relationship && <div><dt>{copy.relationshipStrength}</dt><dd>{formatScore(relationship.strength)}</dd></div>}
                        {relationship && <div><dt>{copy.relationshipConfidence}</dt><dd>{formatScore(relationship.confidence)}</dd></div>}
                      </dl>

                      <div className="causality-subsection">
                        <h4>{copy.causalEvidence}</h4>
                        {causalEvidence.length > 0 ? (
                          <ul className="causal-evidence-list">
                            {causalEvidence.map((item, evidenceIndex) => (
                              <li key={`${item.type || 'evidence'}-${evidenceIndex}`}>
                                <strong>{copy.causalEvidenceTypes[item.type] || humanizeKey(item.type || copy.causalEvidenceItem)}</strong>
                                {item.source && <p><span>{copy.source}:</span> {item.source}</p>}
                                {item.description && <p>{localizeText(item.description)}</p>}
                              </li>
                            ))}
                          </ul>
                        ) : <p className="insight-neutral-copy">{copy.noCausalEvidence}</p>}
                      </div>

                      {reasons.length > 0 && (
                        <div className="persisted-reason-group causality-subsection">
                          <h4>{copy.causalityReasons}</h4>
                          <ul>{reasons.map((reason, reasonIndex) => <li key={reasonIndex}>{localizeText(reason)}</li>)}</ul>
                        </div>
                      )}

                      {(allowedConcepts.length > 0 || forbiddenConcepts.length > 0) && (
                        <div className="causality-framing-grid causality-subsection">
                          {allowedConcepts.length > 0 && (
                            <div><h4>{copy.allowedFraming}</h4><ul>{allowedConcepts.map((concept) => <li key={concept}>{copy.causalityConcepts[concept] || humanizeKey(concept)}</li>)}</ul></div>
                          )}
                          {forbiddenConcepts.length > 0 && (
                            <div><h4>{copy.framingToAvoid}</h4><ul>{forbiddenConcepts.map((concept) => <li key={concept}>{copy.causalityConcepts[concept] || humanizeKey(concept)}</li>)}</ul></div>
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}
              </ol>
            ) : <p className="insight-neutral-copy">{copy.noCausalityEvaluation}</p>}
          </section>

          <section className="insight-drawer-section" aria-labelledby="missing-context-title">
            <h3 id="missing-context-title">{copy.missingContext}</h3>

            {!missingContextEvaluation ? (
              <p className="insight-neutral-copy">{copy.noMissingContextEvaluation}</p>
            ) : (
              <>
                <p className="missing-context-distinction">{copy.missingContextDistinction}</p>
                <dl className="insight-detail-grid">
                  <div><dt>{copy.interpretationLimited}</dt><dd>{typeof missingContextEvaluation.interpretationLimited === 'boolean' ? (missingContextEvaluation.interpretationLimited ? copy.yes : copy.no) : copy.unavailable}</dd></div>
                </dl>

                <div className="integrity-subsection">
                  <div className="insight-section-heading-row"><h4>{copy.missingContextItems}</h4><span>{missingContextItems.length}</span></div>
                  {missingContextItems.length > 0 ? (
                    <ol className="integrity-record-list">
                      {missingContextItems.map((item, index) => (
                        <li key={`${item.field || 'context'}-${index}`}>
                          <div className="integrity-record-heading">
                            <strong>{copy.contextFields[item.field] || humanizeKey(item.field || copy.unavailable)}</strong>
                            {item.status && <span className="integrity-mini-status is-neutral">{copy.missingContextStatuses[item.status] || humanizeKey(item.status)}</span>}
                          </div>
                          {typeof item.isDataQualityError === 'boolean' && (
                            <p><span>{copy.dataQualityError}:</span> {item.isDataQualityError ? copy.yes : copy.no}</p>
                          )}
                          {item.reason && <p>{localizeText(item.reason)}</p>}
                        </li>
                      ))}
                    </ol>
                  ) : <p className="insight-neutral-copy">{copy.noMissingContextItems}</p>}
                </div>

                {missingContextReasons.length > 0 && (
                  <div className="persisted-reason-group integrity-subsection">
                    <h4>{copy.missingContextReasons}</h4>
                    <ul>{missingContextReasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul>
                  </div>
                )}

                {(knownContext.length > 0 || unknownContext.length > 0) && (
                  <div className="context-summary-grid integrity-subsection">
                    <div>
                      <h4>{copy.knownContext}</h4>
                      {knownContext.length > 0 ? (
                        <ul>{knownContext.map((item, index) => <li key={`${item.code || 'known'}-${index}`}><strong>{localizeAnalyticsCode(item.code, language)}</strong><span>{localizeText(item.statement)}</span></li>)}</ul>
                      ) : <p className="insight-neutral-copy">{copy.noKnownContext}</p>}
                    </div>
                    <div>
                      <h4>{copy.unknownContext}</h4>
                      {unknownContext.length > 0 ? (
                        <ul>{unknownContext.map((item, index) => <li key={`${item.code || 'unknown'}-${index}`}><strong>{localizeAnalyticsCode(item.code, language)}</strong><span>{localizeText(item.statement)}</span></li>)}</ul>
                      ) : <p className="insight-neutral-copy">{copy.noUnknownContext}</p>}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
          </AccordionSection>

          <AccordionSection id="technical" title={copy.accordions.technical} open={openSections.has('technical')} onToggle={() => toggleSection('technical')}>
            <section className="insight-drawer-section" aria-labelledby="technical-detail-title">
              <h3 id="technical-detail-title">{copy.technicalDetails}</h3>
              <dl className="insight-drawer-summary-grid">
                <div><dt>{copy.metric}</dt><dd>{insight.metric || copy.unavailable}</dd></div>
                {insight.dimension && <div><dt>{copy.dimension}</dt><dd>{insight.dimension}</dd></div>}
                {insight.segment && <div><dt>{copy.segment}</dt><dd>{insight.segment}</dd></div>}
                <div><dt>{copy.period}</dt><dd>{formatPeriod(insight.period)}</dd></div>
                <div><dt>{copy.granularity}</dt><dd>{copy.granularities[insight.periodGranularity] || insight.periodGranularity || copy.unavailable}</dd></div>
                <div><dt>{copy.direction}</dt><dd>{copy.directions[insight.direction] || insight.direction || copy.unavailable}</dd></div>
                <div><dt>{copy.rank}</dt><dd>{Number.isInteger(insight.rank) && insight.rank > 0 ? `#${insight.rank}` : copy.unavailable}</dd></div>
              </dl>
              {detectionRows.length > 0 && (
                <div className="insight-detection-details">
                  <h4>{copy.detectionDetails}</h4>
                  <dl className="insight-detail-grid">
                    {detectionRows.map(({ field, value }) => (
                      <div key={field}><dt>{copy.detectionFields[field] || field}</dt><dd>{formatValue(field, value)}</dd></div>
                    ))}
                  </dl>
                </div>
              )}
              {isObject(insight.source) && (
                <dl className="insight-source-context">
                  {insight.source.fileName && <div><dt>{copy.sourceFile}</dt><dd>{insight.source.fileName}</dd></div>}
                  {isFiniteNumber(insight.source.rowCount) && <div><dt>{copy.sourceRows}</dt><dd>{formatNumber(insight.source.rowCount)}</dd></div>}
                </dl>
              )}
            </section>
          </AccordionSection>
          </div>
        </div>
      </aside>
    </div>
  )
}

export default InsightDetailDrawer
