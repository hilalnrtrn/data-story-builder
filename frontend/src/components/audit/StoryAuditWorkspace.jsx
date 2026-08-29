import { useMemo } from 'react'
import { NarrativeBias, NumericalAccuracy, StoryDataDiff } from './AuditDetails.jsx'
import { asArrayOrNull, AUDIT_DECISIONS, BIAS_RISKS, BIAS_STATUSES, DIFF_STATUSES, formatScore, semanticClass } from './auditPresentation.js'
import '../../StoryAudit.css'

const PLAN_COLLECTIONS = ['context', 'contributors', 'secondaryFindings', 'counterSignals', 'associatedSignals', 'risks', 'missingContext']
const buildSourceMap = (analysis) => {
  const result = new Map()
  const planItems = analysis?.storyPlan?.mainOutcome ? [analysis.storyPlan.mainOutcome] : []
  PLAN_COLLECTIONS.forEach((key) => { if (Array.isArray(analysis?.storyPlan?.[key])) planItems.push(...analysis.storyPlan[key]) })
  planItems.forEach((item) => { if (item?.id) result.set(item.id, { insightId: item.insightId || null }) })
  if (Array.isArray(analysis?.generatedStory?.sections)) analysis.generatedStory.sections.forEach((section) => { if (Array.isArray(section?.items)) section.items.forEach((item) => { if (item?.sourceItemId) result.set(item.sourceItemId, { ...result.get(item.sourceItemId), text: item.text || null }) }) })
  return result
}

function StoryAuditWorkspace({ analysis, language, copy, onStartAnalysis, onOpenHistory }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const fullAudit = analysis?.fullStoryAudit || null
  const storyAudit = analysis?.storyAudit || fullAudit?.storyDataDiff || null
  const decisionKey = AUDIT_DECISIONS[fullAudit?.decision]
  const diffStatusKey = DIFF_STATUSES[storyAudit?.status]
  const biasStatusKey = BIAS_STATUSES[fullAudit?.narrativeBias?.status]
  const biasRiskKey = BIAS_RISKS[fullAudit?.narrativeBias?.riskLevel]
  const reasons = asArrayOrNull(fullAudit?.reasons)
  const limitations = asArrayOrNull(storyAudit?.auditLimitations)
  const mismatches = asArrayOrNull(storyAudit?.numericalMismatches)
  const sourceById = useMemo(() => buildSourceMap(analysis), [analysis])

  if (!analysis) return <section className="empty-state" aria-labelledby="audit-no-analysis-title"><p className="empty-state-kicker">{copy.eyebrow}</p><h2 id="audit-no-analysis-title">{copy.noAnalysisTitle}</h2><p>{copy.noAnalysisDescription}</p><div className="empty-state-actions"><button type="button" className="secondary-button" onClick={onStartAnalysis}>{copy.startAnalysis}</button><button type="button" className="secondary-button" onClick={onOpenHistory}>{copy.openHistory}</button></div></section>
  if (!storyAudit && !fullAudit) return <section className="empty-state" role="status" aria-labelledby="audit-unavailable-title"><p className="empty-state-kicker">{copy.eyebrow}</p><h2 id="audit-unavailable-title">{copy.unavailableTitle}</h2><p>{analysis.generatedStory ? copy.historicalUnavailable : copy.noStoryAudit}</p></section>

  return <section className="story-audit-workspace" aria-labelledby="story-audit-workspace-title">
    <header className={`audit-decision-hero ${semanticClass(decisionKey)}`}><div><p className="eyebrow">{copy.decision.reliability}</p><h2 id="story-audit-workspace-title">{decisionKey ? copy.decision.labels[decisionKey] : copy.decision.unavailable}</h2><p>{copy.decision.description}</p>{reasons && <small>{copy.decision.findingCount.replace('{count}', reasons.length)}</small>}</div></header>
    {reasons && reasons.length > 0 && <section className="audit-reasons"><h3>{copy.decision.findings}</h3><ul>{reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></section>}
    {!fullAudit && <p className="audit-info-state" role="status">{copy.fullAuditUnavailable}</p>}
    <dl className="audit-pillar-grid" aria-label={copy.summary.label}>
      <div className={semanticClass(diffStatusKey)}><dt>{copy.pillars.grounding}</dt><dd>{diffStatusKey ? copy.diff.statuses[diffStatusKey] : copy.unavailable}</dd><small>{copy.summary.storyCoverage}: {formatScore(storyAudit?.storyCoverageScore, locale, copy.unavailable)}</small></div>
      <div className={mismatches === null ? 'is-neutral' : mismatches.length > 0 ? 'is-risk' : 'is-positive'}><dt>{copy.pillars.numerical}</dt><dd>{mismatches === null ? copy.unavailable : copy.summary.mismatches.replace('{count}', mismatches.length)}</dd><small>{copy.pillars.numericalHelper}</small></div>
      <div><dt>{copy.pillars.evidence}</dt><dd>{formatScore(storyAudit?.evidenceCoverageScore, locale, copy.unavailable)}</dd><small>{copy.pillars.evidenceHelper}</small></div>
      <div className={semanticClass(biasStatusKey)}><dt>{copy.pillars.narrative}</dt><dd>{biasStatusKey ? copy.bias.statuses[biasStatusKey] : copy.unavailable}</dd><small>{biasRiskKey ? copy.bias.risks[biasRiskKey] : copy.unavailable}</small></div>
    </dl>
    {storyAudit && <StoryDataDiff audit={storyAudit} sourceById={sourceById} locale={locale} copy={copy} />}
    {storyAudit && <NumericalAccuracy audit={storyAudit} copy={copy} />}
    <section className="audit-panel" aria-labelledby="evidence-coverage-title"><div className="audit-panel-heading"><div><p className="eyebrow">{copy.evidence.eyebrow}</p><h3 id="evidence-coverage-title">{copy.evidence.title}</h3></div><strong>{formatScore(storyAudit?.evidenceCoverageScore, locale, copy.unavailable)}</strong></div><p className="audit-panel-description">{copy.evidence.description}</p>{typeof storyAudit?.evidenceCoverageScore === 'number' && <progress className="audit-coverage-meter" max="1" value={storyAudit.evidenceCoverageScore} aria-label={`${copy.summary.evidenceCoverage}: ${formatScore(storyAudit.evidenceCoverageScore, locale, copy.unavailable)}`} />}<div className="evidence-strength-legend">{['strong', 'none', 'notApplicable'].map((key) => <span key={key} className={`audit-badge ${semanticClass(key)}`}>{copy.evidenceStrengths[key]}</span>)}</div></section>
    <NarrativeBias bias={fullAudit?.narrativeBias || null} copy={copy} />
    <section className="audit-panel audit-limitations" aria-labelledby="audit-limitations-title"><div className="audit-panel-heading"><div><p className="eyebrow">{copy.limitations.eyebrow}</p><h3 id="audit-limitations-title">{copy.limitations.title}</h3></div></div>{limitations === null ? <p className="audit-neutral-state">{copy.limitations.unavailable}</p> : limitations.length === 0 ? <p className="audit-neutral-state">{copy.limitations.none}</p> : <ul>{limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>}{fullAudit?.regenerationFailureReason && <p className="audit-regeneration-failure"><strong>{copy.limitations.regenerationFailure}:</strong> {fullAudit.regenerationFailureReason}</p>}</section>
    <details className="audit-technical-details"><summary>{copy.technical.title}</summary><dl><div><dt>{copy.decision.auditorVersion}</dt><dd>{fullAudit?.auditorVersion || copy.unavailable}</dd></div><div><dt>{copy.decision.regenerationEligible}</dt><dd>{typeof fullAudit?.regenerationEligible === 'boolean' ? (fullAudit.regenerationEligible ? copy.yes : copy.no) : copy.unavailable}</dd></div>{fullAudit?.regenerationAttempted === true && <div><dt>{copy.decision.attempts}</dt><dd>{fullAudit.regenerationAttemptCount ?? copy.unavailable}</dd></div>}</dl></details>
  </section>
}

export default StoryAuditWorkspace
