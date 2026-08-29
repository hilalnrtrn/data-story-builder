import { useEffect, useRef, useState } from 'react'
import { localizeAnalyticsCode, localizeAnalyticsText } from '../../i18n/analyticsText.js'
import { InsightHero, TrustRail, WhatHappened } from './ExplainabilityFoundation.jsx'
import { BusinessRelevanceSection, CalculationSection, EvidenceSection } from './EvidenceAndRelevance.jsx'
import { IntegrityChallenge, RelatedFindings } from './RelationshipIntegrity.jsx'
import { CausalityBoundary, MissingContext } from './CausalityContext.jsx'

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)
const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)

const CALCULATION_FIELDS = {
  CHANGE: ['previous', 'current', 'absoluteChange', 'percentageChange'],
  TREND: ['startValue', 'endValue', 'periodCount'],
  ANOMALY: ['observed', 'lowerBound', 'upperBound', 'iqr', 'q1', 'q3'],
  CONTRIBUTION: ['segmentPreviousValue', 'segmentCurrentValue', 'segmentAbsoluteChange', 'totalAbsoluteChange', 'contributionShare'],
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

function AccordionSection({ id, title, open, onToggle, children, hidden = false }) {
  if (hidden) return null
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
  const dialogRef = useRef(null)
  const [openSections, setOpenSections] = useState(() => new Set())
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'

  useEffect(() => {
    const previousFocus = document.activeElement
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = [...(dialogRef.current?.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ) || [])].filter((element) => !element.hidden && element.getClientRects().length > 0)
      if (focusable.length === 0) {
        event.preventDefault()
        closeButtonRef.current?.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
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
    ? `${new Intl.NumberFormat(locale, {
      style: 'percent',
      maximumFractionDigits: 1,
    }).formatToParts(value).filter(({ type }) => type !== 'percentSign').map(({ value: part }) => part).join('').trim()}%`
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
      <div className="insight-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
        <aside
          ref={dialogRef}
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
  const visibleDetectionRows = insight.type === 'TREND'
    ? detectionRows.filter(({ field }) => ['slope', 'persistenceRatio'].includes(field))
    : []
  const methodDetailRows = detectionRows.filter(({ field }) => (
    field !== 'method' && !visibleDetectionRows.some((row) => row.field === field)
  ))
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
  const selectedCausality = selectedCausalityEvaluations[0] || null
  const heroContext = [insight.segment || insight.dimension, formatPeriod(insight.period)]
    .filter(Boolean)
    .join(' · ')
  const considerations = [
    counterEvidence.length > 0
      ? copy.considerations.counterEvidence.replace('{count}', counterEvidence.length)
      : null,
    contradictions.length > 0
      ? copy.considerations.contradictions.replace('{count}', contradictions.length)
      : null,
    integrityEvaluation?.requiresQualification === true
      ? copy.considerations.qualification
      : null,
    missingContextEvaluation?.interpretationLimited === true
      ? copy.considerations.interpretationLimited
      : null,
  ].filter(Boolean).slice(0, 4)

  return (
    <div className="insight-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <aside
        ref={dialogRef}
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
          <div className="fd-e-foundation-grid">
            <InsightHero
              insight={insight}
              typeLabel={typeLabel}
              priorityLabel={priorityLabel}
              context={heroContext}
              formatNumber={formatNumber}
              formatRatioPercent={formatRatioPercent}
              formatScaledPercent={formatScaledPercent}
              copy={copy}
            />
            <TrustRail
              insight={insight}
              integrityEvaluation={integrityEvaluation}
              selectedCausality={selectedCausality}
              formatScore={formatScore}
              copy={copy}
            />
          </div>

          <WhatHappened
            insight={insight}
            formatValue={formatValue}
            copy={copy}
          />

          {considerations.length > 0 && (
            <section className="explainability-considerations" aria-labelledby="considerations-title">
              <h3 id="considerations-title">{copy.thingsToConsider}</h3>
              <div>{considerations.map((item) => <span key={item}>! {item}</span>)}</div>
            </section>
          )}

          <div className="fd-e2-investigation-grid">
            <EvidenceSection
              evidence={evidence}
              insight={insight}
              localizeText={localizeText}
              renderEvidenceValue={renderEvidenceValue}
              renderReadableValue={renderReadableValue}
              formatNumber={formatNumber}
              copy={copy}
            />
            <CalculationSection
              calculationRows={calculationRows}
              visibleDetectionRows={visibleDetectionRows}
              methodDetailRows={methodDetailRows}
              insight={insight}
              formatValue={formatValue}
              copy={copy}
            />
          </div>

          <BusinessRelevanceSection
            insight={insight}
            businessComponents={businessComponents}
            businessReasons={businessReasons}
            priorityBreakdown={priorityBreakdown}
            priorityReasons={priorityReasons}
            formatScore={formatScore}
            localizeText={localizeText}
            humanizeKey={humanizeKey}
            copy={copy}
          />

          <RelatedFindings
            currentInsight={insight}
            relatedRelationships={relatedRelationships}
            formatPeriod={formatPeriod}
            formatScore={formatScore}
            formatValue={formatValue}
            localizeText={localizeText}
            humanizeKey={humanizeKey}
            copy={copy}
          />

          <IntegrityChallenge
            integrityEvaluation={integrityEvaluation}
            counterEvidence={counterEvidence}
            contradictions={contradictions}
            consistencyChecks={consistencyChecks}
            relationships={Array.isArray(relationships) ? relationships : []}
            resolveInsightSummary={resolveInsightSummary}
            integrityReasons={integrityReasons}
            integrityBreakdown={integrityBreakdown}
            formatNumber={formatNumber}
            formatRatioPercent={formatRatioPercent}
            localizeText={localizeText}
            humanizeKey={humanizeKey}
            copy={copy}
          />

          <div className="explainability-accordions">
          <AccordionSection hidden id="relationships" title={copy.accordions.relationships} open={openSections.has('relationships')} onToggle={() => toggleSection('relationships')}>

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

          </AccordionSection>

          <AccordionSection hidden id="integrity" title={copy.accordions.integrity} open={openSections.has('integrity')} onToggle={() => toggleSection('integrity')}>

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

          <CausalityBoundary evaluations={selectedCausalityEvaluations} relationships={Array.isArray(relationships) ? relationships : []} formatScore={formatScore} humanizeKey={humanizeKey} localizeText={localizeText} copy={copy} />
          <MissingContext evaluation={missingContextEvaluation} items={missingContextItems} reasons={missingContextReasons} knownContext={knownContext} unknownContext={unknownContext} language={language} humanizeKey={humanizeKey} localizeText={localizeText} localizeAnalyticsCode={localizeAnalyticsCode} copy={copy} />

          <AccordionSection hidden id="limitations" title={copy.accordions.limitations} open={openSections.has('limitations')} onToggle={() => toggleSection('limitations')}>

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
            </section>
          </AccordionSection>
          </div>
        </div>
      </aside>
    </div>
  )
}

export default InsightDetailDrawer
