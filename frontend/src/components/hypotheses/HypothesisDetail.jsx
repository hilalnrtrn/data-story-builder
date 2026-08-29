import { useState } from 'react'

const asArray = (value) => Array.isArray(value) ? value : []

const nextStatuses = {
  OPEN: ['SUPPORTED', 'REJECTED'],
  SUPPORTED: ['CONFIRMED', 'REJECTED'],
  CONFIRMED: [],
  REJECTED: [],
}

const presentValue = (value, unavailable) => {
  if (value === null || value === undefined) return unavailable
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return unavailable
}

function HypothesisDetail({ hypothesis, insights, relationships, language, copy, onStatusUpdate, onClose }) {
  const [pendingStatus, setPendingStatus] = useState(null)
  const [updateState, setUpdateState] = useState(null)
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const insightById = new Map(asArray(insights).filter((item) => item?.id).map((item) => [item.id, item]))
  const relationshipById = new Map(asArray(relationships).filter((item) => item?.id).map((item) => [item.id, item]))
  const supportingEvidence = asArray(hypothesis?.supportingEvidence)
  const counterEvidence = asArray(hypothesis?.counterEvidence)
  const missingContext = asArray(hypothesis?.missingContext)
  const reasons = asArray(hypothesis?.reasons)
  const sourceInsights = asArray(hypothesis?.sourceInsightIds)
  const sourceRelationships = asArray(hypothesis?.sourceRelationshipIds)
  const confidence = typeof hypothesis?.confidence === 'number' && Number.isFinite(hypothesis.confidence)
    ? new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 2 }).format(hypothesis.confidence)
    : copy.unavailable
  const availableStatuses = nextStatuses[hypothesis?.status] || []

  const handleStatusUpdate = async (status) => {
    setPendingStatus(status)
    setUpdateState(null)
    try {
      await onStatusUpdate(hypothesis.id, status)
      setUpdateState('succeeded')
    } catch (error) {
      setUpdateState(error?.status === 404 ? 'not-found' : 'failed')
    } finally {
      setPendingStatus(null)
    }
  }

  return (
    <aside className="hypothesis-detail" aria-labelledby="hypothesis-detail-title">
      <header className="hypothesis-detail-header">
        <div><p className="eyebrow">{copy.detail.eyebrow}</p><h2 id="hypothesis-detail-title">{copy.detail.title}</h2></div>
        <button type="button" onClick={onClose} aria-label={copy.detail.close}>×</button>
      </header>

      <section className="hypothesis-detail-hero">
        <span className="hypothesis-kind"><span aria-hidden="true">◇</span>{copy.possibleExplanation}</span>
        <p>{hypothesis?.statement || copy.unavailable}</p>
        <dl>
          <div><dt>{copy.status}</dt><dd>{copy.statuses[hypothesis?.status] || hypothesis?.status || copy.unavailable}</dd></div>
          <div><dt>{copy.confidenceScore}</dt><dd>{confidence}</dd></div>
          <div><dt>{copy.causality}</dt><dd>{copy.causalityStatuses[hypothesis?.causalityStatus] || hypothesis?.causalityStatus || copy.unavailable}</dd></div>
        </dl>
        <p className="hypothesis-safety-note">{copy.detail.safetyNote}</p>
      </section>

      <section className="hypothesis-lifecycle" aria-labelledby="hypothesis-lifecycle-title">
        <div>
          <p className="eyebrow">{copy.lifecycle.currentStatus}</p>
          <h3 id="hypothesis-lifecycle-title">{copy.statuses[hypothesis?.status] || hypothesis?.status || copy.unavailable}</h3>
        </div>
        <div className="hypothesis-lifecycle-actions">
          <strong>{availableStatuses.length > 0 ? copy.lifecycle.availableActions : copy.lifecycle.terminalStatus}</strong>
          {availableStatuses.length > 0 && <div>{availableStatuses.map((status) => (
            <button key={status} type="button" disabled={Boolean(pendingStatus)} onClick={() => handleStatusUpdate(status)}>
              {pendingStatus === status ? copy.lifecycle.updating : copy.lifecycle.actions[status]}
            </button>
          ))}</div>}
        </div>
        {updateState === 'succeeded' && <p className="hypothesis-lifecycle-feedback is-success" role="status">{copy.lifecycle.statusUpdated}</p>}
        {updateState === 'failed' && <p className="hypothesis-lifecycle-feedback is-error" role="alert">{copy.lifecycle.transitionFailed}</p>}
        {updateState === 'not-found' && <p className="hypothesis-lifecycle-feedback is-error" role="alert">{copy.lifecycle.notFound}</p>}
      </section>

      <section className="hypothesis-detail-section" aria-labelledby="hypothesis-support-title">
        <div className="hypothesis-detail-heading"><div><span className="epistemic-label is-fact">{copy.epistemic.verifiedEvidence}</span><h3 id="hypothesis-support-title">{copy.supportingEvidence}</h3></div><span>{supportingEvidence.length}</span></div>
        {supportingEvidence.length === 0 ? <p className="hypothesis-empty-copy">{copy.detail.noSupportingEvidence}</p> : (
          <ul className="hypothesis-evidence-list">
            {supportingEvidence.map((reference, index) => {
              const insight = insightById.get(reference?.insightId)
              const evidence = asArray(insight?.evidence).find((item) => item?.code === reference?.evidenceCode)
              return (
                <li key={`${reference?.insightId || 'insight'}-${reference?.evidenceCode || index}`} className={!evidence ? 'is-unresolved' : ''}>
                  <div><strong>{evidence?.label || copy.detail.unresolvedEvidence}</strong><code>{reference?.evidenceCode || copy.unavailable}</code></div>
                  {evidence ? <b>{presentValue(evidence.value, copy.unavailable)}{evidence.unit ? ` ${evidence.unit}` : ''}</b> : <span>{copy.detail.unresolved}</span>}
                  <p>{insight?.metric || copy.unavailable} · {reference?.insightId || copy.unavailable}</p>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="hypothesis-detail-section" aria-labelledby="hypothesis-counter-title">
        <div className="hypothesis-detail-heading"><h3 id="hypothesis-counter-title">{copy.counterEvidence}</h3><span>{counterEvidence.length}</span></div>
        {counterEvidence.length === 0 ? <p className="hypothesis-empty-copy">{copy.detail.noCounterEvidence}</p> : (
          <div className="hypothesis-record-list">
            {counterEvidence.map((item, index) => {
              const insight = insightById.get(item?.insightId)
              return (
                <article key={`${item?.relationshipId || 'counter'}-${index}`}>
                  <header><strong>{item?.metric || insight?.metric || copy.unavailable}</strong><span>{copy.directions[item?.direction] || item?.direction || copy.unavailable}</span></header>
                  <code>{item?.relationshipId || copy.unavailable}</code>
                  {asArray(item?.reasons).length > 0 && <ul>{item.reasons.map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul>}
                </article>
              )
            })}
          </div>
        )}
      </section>

      <section className="hypothesis-detail-section" aria-labelledby="hypothesis-context-title">
        <div className="hypothesis-detail-heading"><h3 id="hypothesis-context-title">{copy.missingContext}</h3><span>{missingContext.length}</span></div>
        {missingContext.length === 0 ? <p className="hypothesis-empty-copy">{copy.detail.noMissingContext}</p> : (
          <div className="hypothesis-record-list">
            {missingContext.map((reference, index) => (
              <article key={`${reference?.sourceInsightId || 'context'}-${reference?.item?.field || index}`}>
                <header><strong>{reference?.item?.field || copy.unavailable}</strong><span>{copy.contextStatuses[reference?.item?.status] || reference?.item?.status || copy.unavailable}</span></header>
                <p className={reference?.item?.isDataQualityError ? 'is-quality-issue' : 'is-context-gap'}>{reference?.item?.isDataQualityError ? copy.dataQualityIssue : copy.contextGap}</p>
                {reference?.item?.reason && <p>{reference.item.reason}</p>}
                <code>{reference?.sourceInsightId || copy.unavailable}</code>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="hypothesis-causality-boundary" aria-labelledby="hypothesis-causality-title">
        <div><p className="eyebrow">{copy.causality}</p><h3 id="hypothesis-causality-title">{copy.causalityStatuses[hypothesis?.causalityStatus] || hypothesis?.causalityStatus || copy.unavailable}</h3></div>
        <p>{copy.detail.causalityBoundary}</p>
      </section>

      {reasons.length > 0 && <details className="hypothesis-reasoning"><summary>{copy.reasons}</summary><ul className="hypothesis-reason-list">{reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></details>}

      <details className="hypothesis-traceability">
        <summary>{copy.detail.traceability}</summary>
        <div>
          <section><h3>{copy.technicalMetadata}</h3><dl><div><dt>{copy.hypothesisId}</dt><dd><code>{hypothesis?.id || copy.unavailable}</code></dd></div><div><dt>{copy.trackerVersion}</dt><dd>{hypothesis?.trackerVersion || copy.unavailable}</dd></div></dl></section>
          <section><span className="epistemic-label is-insight">{copy.epistemic.analyticalFinding}</span><h3>{copy.sourceInsights}</h3>{sourceInsights.length === 0 ? <p>{copy.unavailable}</p> : <ul>{sourceInsights.map((id) => <li key={id}><code>{id}</code><span>{insightById.get(id)?.metric || copy.unavailable}</span></li>)}</ul>}</section>
          <section><h3>{copy.sourceRelationships}</h3>{sourceRelationships.length === 0 ? <p>{copy.unavailable}</p> : <ul>{sourceRelationships.map((id) => <li key={id}><code>{id}</code><span>{relationshipById.get(id)?.type || copy.unavailable}</span></li>)}</ul>}</section>
        </div>
      </details>
    </aside>
  )
}

export default HypothesisDetail
