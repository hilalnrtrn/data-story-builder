import { useState } from 'react'

function Disclosure({ id, title, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="fd-e2-disclosure">
      <button type="button" aria-expanded={open} aria-controls={`${id}-content`} onClick={() => setOpen((current) => !current)}>
        <span>{title}</span><span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && <div id={`${id}-content`}>{children}</div>}
    </div>
  )
}

function EvidenceSection({ evidence, insight, localizeText, renderEvidenceValue, renderReadableValue, formatNumber, copy }) {
  return (
    <section className="fd-e2-section fd-e2-evidence" aria-labelledby="fd-e2-evidence-title">
      <div className="fd-e2-section-heading">
        <div><span className="fd-e2-epistemic is-fact">{copy.fact}</span><h3 id="fd-e2-evidence-title">{copy.evidence}</h3></div>
        <span>{copy.evidenceRecords.replace('{count}', evidence.length)}</span>
      </div>
      {evidence.length > 0 ? (
        <ol className="fd-e2-evidence-list">
          {evidence.map((item, index) => (
            <li key={`${item?.code || 'evidence'}-${index}`}>
              <span className="fd-e2-fact-node" aria-hidden="true">F</span>
              <div><strong>{localizeText(item?.label) || copy.evidenceItem.replace('{number}', index + 1)}</strong>{item?.unit && <small>{copy.units[item.unit] || item.unit}</small>}</div>
              <div className="fd-e2-evidence-value">{renderEvidenceValue(item?.value, item?.unit)}</div>
            </li>
          ))}
        </ol>
      ) : <p className="insight-neutral-copy">{copy.noEvidence}</p>}
      <Disclosure id="evidence-traceability" title={copy.sourceTraceability}>
        <dl className="fd-e2-trace-grid">
          {insight.source?.fileName && <div><dt>{copy.sourceFile}</dt><dd>{insight.source.fileName}</dd></div>}
          {typeof insight.source?.rowCount === 'number' && <div><dt>{copy.sourceRows}</dt><dd>{formatNumber(insight.source.rowCount)}</dd></div>}
        </dl>
        {evidence.length > 0 && <ol className="fd-e2-code-list">{evidence.map((item, index) => <li key={`${item?.code || 'code'}-${index}`}><code>{item?.code || copy.unavailable}</code><div>{renderReadableValue(item?.value)}</div></li>)}</ol>}
      </Disclosure>
    </section>
  )
}

function CalculationSection({ calculationRows, visibleDetectionRows, methodDetailRows, insight, formatValue, copy }) {
  const method = insight.detection?.method
  return (
    <section className="fd-e2-section fd-e2-calculation" aria-labelledby="fd-e2-calculation-title">
      <div className="fd-e2-section-heading"><div><span className="fd-e2-step-label">{copy.analyticalMethod}</span><h3 id="fd-e2-calculation-title">{copy.analyticalInputs}</h3></div>{method && <span className="fd-e2-method-badge">{formatValue('method', method)}</span>}</div>
      {[...calculationRows, ...visibleDetectionRows].length > 0 ? (
        <dl className="fd-e2-input-grid">
          {[...calculationRows, ...visibleDetectionRows].map(({ field, value }) => <div key={field}><dt>{copy.valueFields[field] || copy.detectionFields[field] || field}</dt><dd>{formatValue(field, value)}</dd></div>)}
        </dl>
      ) : <p className="insight-neutral-copy">{copy.noCalculation}</p>}
      {methodDetailRows.length > 0 && (
        <Disclosure id="method-details" title={copy.methodDetails}>
          <dl className="fd-e2-detail-grid">{methodDetailRows.map(({ field, value }) => <div key={field}><dt>{copy.detectionFields[field] || field}</dt><dd>{formatValue(field, value)}</dd></div>)}</dl>
        </Disclosure>
      )}
      <div className="fd-e2-result-node"><span className="fd-e2-epistemic is-insight">{copy.insightLabel}</span><strong>{[copy.types[insight.type] || insight.type, insight.metric].filter(Boolean).join(' · ') || copy.unavailable}</strong></div>
    </section>
  )
}

function BusinessRelevanceSection({ insight, businessComponents, businessReasons, priorityBreakdown, priorityReasons, formatScore, localizeText, humanizeKey, copy }) {
  const hasOverview = [insight.businessRelevance, insight.impactDirection, insight.priorityLevel, insight.priorityScore].some((value) => value !== null && value !== undefined && value !== '')
  return (
    <section className="fd-e2-section fd-e2-relevance" aria-labelledby="fd-e2-relevance-title">
      <div className="fd-e2-section-heading"><div><span className="fd-e2-epistemic is-insight">{copy.insightLabel}</span><h3 id="fd-e2-relevance-title">{copy.whyItMatters}</h3></div></div>
      {hasOverview ? <dl className="fd-e2-relevance-overview"><div><dt>{copy.businessRelevanceScore}</dt><dd>{formatScore(insight.businessRelevance)}</dd></div><div><dt>{copy.impactDirection}</dt><dd><span className="fd-e2-impact-symbol" aria-hidden="true">◇</span>{copy.impactDirections[insight.impactDirection] || insight.impactDirection || copy.unavailable}</dd></div><div><dt>{copy.priorityLevel}</dt><dd>{copy.priorities[insight.priorityLevel] || insight.priorityLevel || copy.unavailable}</dd></div><div><dt>{copy.priorityScore}</dt><dd>{formatScore(insight.priorityScore)}</dd></div></dl> : <p className="insight-neutral-copy">{copy.noBusinessRelevance}</p>}
      {businessComponents.length > 0 && <div className="fd-e2-rationale-stack"><h4>{copy.relevanceComponents}</h4>{businessComponents.map((component, index) => <article key={`${component.name || 'component'}-${index}`}><div><strong>{copy.componentNames[component.name] || humanizeKey(component.name || copy.component)}</strong><span>{formatScore(component.score)}</span></div>{component.reason && <p>{localizeText(component.reason)}</p>}</article>)}</div>}
      {businessReasons.length > 0 && <div className="fd-e2-reasons"><h4>{copy.businessReasons}</h4><ul>{businessReasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul></div>}
      {priorityReasons.length > 0 && <div className="fd-e2-reasons is-priority"><h4>{copy.priorityRationale}</h4><ul>{priorityReasons.map((reason, index) => <li key={index}>{localizeText(reason)}</li>)}</ul></div>}
      {priorityBreakdown.length > 0 && <Disclosure id="priority-breakdown" title={copy.priorityBreakdown}><dl className="fd-e2-detail-grid">{priorityBreakdown.map(([key, value]) => <div key={key}><dt>{copy.priorityBreakdownFields[key] || humanizeKey(key)}</dt><dd>{formatScore(value)}</dd></div>)}</dl></Disclosure>}
    </section>
  )
}

export { BusinessRelevanceSection, CalculationSection, EvidenceSection }
