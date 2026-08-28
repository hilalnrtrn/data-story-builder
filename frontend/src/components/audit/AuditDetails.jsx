import {
  asArrayOrNull,
  BIAS_CATEGORIES,
  BIAS_RISKS,
  BIAS_STATUSES,
  displayValue,
  EVIDENCE_STRENGTHS,
  semanticClass,
} from './auditPresentation.js'

const AuditBadge = ({ label, state = 'neutral' }) => (
  <span className={`audit-badge ${semanticClass(state)}`}>{label}</span>
)

const SourceReference = ({ sourceItemId, sourceById, copy }) => {
  const source = sourceById.get(sourceItemId)
  return (
    <div className="audit-source-reference">
      <code>{sourceItemId}</code>
      {source?.text && <p>{source.text}</p>}
      {source?.insightId && <span>{copy.insight}: {source.insightId}</span>}
    </div>
  )
}

export function StoryDataDiff({ audit, sourceById, copy }) {
  const groups = [
    ['covered', asArrayOrNull(audit.coveredSourceItemIds)],
    ['omitted', asArrayOrNull(audit.omittedSourceItemIds)],
    ['unexpected', asArrayOrNull(audit.unexpectedSourceItemIds)],
  ]
  const itemAudits = asArrayOrNull(audit.itemAudits)

  return (
    <section className="audit-panel" aria-labelledby="story-data-diff-title">
      <div className="audit-panel-heading">
        <div><p className="eyebrow">{copy.diff.eyebrow}</p><h3 id="story-data-diff-title">{copy.diff.title}</h3></div>
        <span>{copy.diff.required.replace('{count}', asArrayOrNull(audit.requiredSourceItemIds)?.length ?? copy.unavailable)}</span>
      </div>

      <div className="audit-diff-grid">
        {groups.map(([key, items]) => (
          <section key={key} className={`audit-diff-group is-${key}`}>
            <header><h4>{copy.diff[key]}</h4><span>{items?.length ?? copy.unavailable}</span></header>
            {items === null ? <p>{copy.unavailable}</p> : items.length === 0 ? (
              <p>{copy.diff.empty[key]}</p>
            ) : (
              <ul>{items.map((id) => <li key={id}><SourceReference sourceItemId={id} sourceById={sourceById} copy={copy} /></li>)}</ul>
            )}
          </section>
        ))}
      </div>

      {itemAudits && itemAudits.length > 0 && (
        <details className="audit-detail-disclosure">
          <summary>{copy.diff.itemAudits.replace('{count}', itemAudits.length)}</summary>
          <div className="audit-item-list">
            {itemAudits.map((item, index) => {
              const strengthKey = EVIDENCE_STRENGTHS[item?.evidenceStrength]
              const evidence = asArrayOrNull(item?.evidenceTrace?.resolvedEvidence)
              const reasons = asArrayOrNull(item?.reasons)
              return (
                <article key={item?.sourceItemId || index} className="audit-item-record">
                  <header>
                    <div><code>{item?.sourceItemId || copy.unavailable}</code>{item?.role && <span>{item.role}</span>}</div>
                    <AuditBadge
                      state={item?.isCovered === true ? 'pass' : item?.isCovered === false ? 'fail' : 'neutral'}
                      label={item?.isCovered === true ? copy.covered : item?.isCovered === false ? copy.notCovered : copy.unavailable}
                    />
                  </header>
                  <dl className="audit-record-metadata">
                    <div><dt>{copy.insight}</dt><dd>{item?.insightId || copy.unavailable}</dd></div>
                    <div><dt>{copy.evidenceStrength}</dt><dd>{strengthKey ? copy.evidenceStrengths[strengthKey] : copy.unavailable}</dd></div>
                    <div><dt>{copy.resolvedEvidence}</dt><dd>{evidence?.length ?? copy.unavailable}</dd></div>
                  </dl>
                  {evidence && evidence.length > 0 && (
                    <ul className="audit-evidence-list">
                      {evidence.map((entry, evidenceIndex) => (
                        <li key={`${entry?.code || 'evidence'}-${evidenceIndex}`}>
                          <span><strong>{entry?.label || entry?.code || copy.evidenceLabel}</strong>{entry?.code && <code>{entry.code}</code>}</span>
                          <b>{displayValue(entry?.value, copy.unavailable)}{entry?.unit ? ` ${entry.unit}` : ''}</b>
                        </li>
                      ))}
                    </ul>
                  )}
                  {reasons && reasons.length > 0 && <ul className="audit-reason-list">{reasons.map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul>}
                </article>
              )
            })}
          </div>
        </details>
      )}
    </section>
  )
}

export function NumericalAccuracy({ audit, copy }) {
  const numericalAudits = asArrayOrNull(audit.numericalAudits)
  const mismatches = asArrayOrNull(audit.numericalMismatches)

  return (
    <section className="audit-panel" aria-labelledby="numerical-audit-title">
      <div className="audit-panel-heading"><div><p className="eyebrow">{copy.numerical.eyebrow}</p><h3 id="numerical-audit-title">{copy.numerical.title}</h3></div></div>
      {mismatches === null ? <p className="audit-neutral-state">{copy.numerical.unavailable}</p> : mismatches.length === 0 ? (
        <p className="audit-success-state">{copy.numerical.noMismatches}</p>
      ) : (
        <div className="audit-mismatch-list">
          {mismatches.map((mismatch, index) => (
            <article key={`${mismatch?.sourceItemId || 'mismatch'}-${index}`}>
              <header><code>{mismatch?.sourceItemId || copy.unavailable}</code><AuditBadge state="fail" label={copy.numerical.mismatch} /></header>
              <dl className="audit-record-metadata">
                <div><dt>{copy.numerical.originalToken}</dt><dd>{mismatch?.originalToken ?? copy.unavailable}</dd></div>
                <div><dt>{copy.numerical.normalizedValue}</dt><dd>{displayValue(mismatch?.normalizedValue, copy.unavailable)}</dd></div>
                <div><dt>{copy.numerical.percent}</dt><dd>{typeof mismatch?.isPercent === 'boolean' ? (mismatch.isPercent ? copy.yes : copy.no) : copy.unavailable}</dd></div>
              </dl>
              {mismatch?.reason && <p>{mismatch.reason}</p>}
            </article>
          ))}
        </div>
      )}
      {numericalAudits && numericalAudits.length > 0 && (
        <details className="audit-detail-disclosure">
          <summary>{copy.numerical.details.replace('{count}', numericalAudits.length)}</summary>
          <div className="audit-item-list">
            {numericalAudits.map((item, index) => (
              <article className="audit-item-record" key={`${item?.sourceItemId || 'numeric'}-${index}`}>
                <header><code>{item?.sourceItemId || copy.unavailable}</code><AuditBadge state={item?.passed === true ? 'pass' : item?.passed === false ? 'fail' : 'neutral'} label={item?.passed === true ? copy.passed : item?.passed === false ? copy.failed : copy.unavailable} /></header>
                <dl className="audit-record-metadata">
                  <div><dt>{copy.numerical.extractedTokens}</dt><dd>{asArrayOrNull(item?.extractedTokens)?.length ?? copy.unavailable}</dd></div>
                  <div><dt>{copy.numerical.unsupportedTokens}</dt><dd>{asArrayOrNull(item?.unsupportedTokens)?.length ?? copy.unavailable}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        </details>
      )}
    </section>
  )
}

export function NarrativeBias({ bias, copy }) {
  if (!bias) return <section className="audit-panel"><h3>{copy.bias.title}</h3><p className="audit-neutral-state">{copy.bias.unavailable}</p></section>
  const statusKey = BIAS_STATUSES[bias.status]
  const riskKey = BIAS_RISKS[bias.riskLevel]
  const findings = asArrayOrNull(bias.findings)

  return (
    <section className="audit-panel" aria-labelledby="narrative-bias-title">
      <div className="audit-panel-heading">
        <div><p className="eyebrow">{copy.bias.eyebrow}</p><h3 id="narrative-bias-title">{copy.bias.title}</h3></div>
        <div className="audit-heading-badges">
          <AuditBadge state={statusKey} label={statusKey ? copy.bias.statuses[statusKey] : copy.unavailable} />
          <AuditBadge state={riskKey} label={riskKey ? copy.bias.risks[riskKey] : copy.unavailable} />
        </div>
      </div>
      {findings === null ? <p className="audit-neutral-state">{copy.bias.unavailable}</p> : findings.length === 0 ? (
        <p className="audit-success-state">{copy.bias.noFindings}</p>
      ) : (
        <div className="bias-finding-list">
          {findings.map((finding, index) => {
            const categoryKey = BIAS_CATEGORIES[finding?.category]
            const findingRisk = BIAS_RISKS[finding?.riskLevel]
            const reasons = asArrayOrNull(finding?.reasons)
            return (
              <article key={`${finding?.sourceItemId || 'bias'}-${index}`}>
                <header><h4>{categoryKey ? copy.bias.categories[categoryKey] : copy.bias.unknownCategory}</h4><AuditBadge state={findingRisk} label={findingRisk ? copy.bias.risks[findingRisk] : copy.unavailable} /></header>
                {finding?.message && <p>{finding.message}</p>}
                {finding?.recommendation && <p><strong>{copy.bias.recommendation}:</strong> {finding.recommendation}</p>}
                {finding?.sourceItemId && <code>{finding.sourceItemId}</code>}
                {reasons && reasons.length > 0 && <ul className="audit-reason-list">{reasons.map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul>}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
