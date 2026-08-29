const EVIDENCE_STRENGTH_KEYS = {
  0: 'strong',
  1: 'none',
  2: 'notApplicable',
}

const presentValue = (value, unavailable) => {
  if (value === null || value === undefined) return unavailable
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return unavailable
}

function ClaimEvidence({ sourceItemId, planItem, itemAudit, fallbackEvidence, copy }) {
  const resolvedEvidence = Array.isArray(itemAudit?.evidenceTrace?.resolvedEvidence)
    ? itemAudit.evidenceTrace.resolvedEvidence
    : fallbackEvidence
  const strengthKey = EVIDENCE_STRENGTH_KEYS[itemAudit?.evidenceStrength]
  const insightId = itemAudit?.insightId || planItem?.insightId || null
  const hasAudit = itemAudit !== null && itemAudit !== undefined

  return (
    <details className="story-evidence-disclosure">
      <summary>
        <span className="story-evidence-label"><span aria-hidden="true">◇</span>{copy.evidenceCompact.replace('{count}', resolvedEvidence.length)}</span>
      </summary>

      <div className="story-trace-panel">
        {resolvedEvidence.length > 0 ? (
          <ul className="story-evidence-list">
            {resolvedEvidence.map((evidence, index) => (
              <li key={`${evidence?.code || 'evidence'}-${index}`}>
                <div>
                  <strong>{evidence?.label || evidence?.code || copy.evidence}</strong>
                </div>
                <span>
                  {presentValue(evidence?.value, copy.unavailable)}
                  {evidence?.unit ? ` ${evidence.unit}` : ''}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="story-evidence-empty">{copy.noResolvedEvidence}</p>
        )}

        {!hasAudit && (
          <p className="story-trace-note">{copy.auditUnavailable}</p>
        )}

        <details className="story-technical-trace">
          <summary>{copy.technicalTraceability}</summary>
          <dl className="story-trace-metadata">
            <div><dt>{copy.sourceItem}</dt><dd>{sourceItemId}</dd></div>
            <div><dt>{copy.sourceInsight}</dt><dd>{insightId || copy.unavailable}</dd></div>
            <div><dt>{copy.coverage}</dt><dd>{hasAudit ? (itemAudit.isCovered ? copy.covered : copy.notCovered) : copy.unavailable}</dd></div>
            <div><dt>{copy.evidenceStrength}</dt><dd>{strengthKey ? copy.evidenceStrengths[strengthKey] : copy.unavailable}</dd></div>
          </dl>
          {resolvedEvidence.some((evidence) => evidence?.code) && (
            <ul className="story-technical-codes">
              {resolvedEvidence.map((evidence, index) => evidence?.code && <li key={`${evidence.code}-${index}`}><span>{evidence.label || copy.evidence}</span><code>{evidence.code}</code></li>)}
            </ul>
          )}
        </details>
      </div>
    </details>
  )
}

export default ClaimEvidence
