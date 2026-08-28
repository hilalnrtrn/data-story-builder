import { useMemo } from 'react'
import StorySection from './StorySection.jsx'

const PLAN_COLLECTIONS = [
  'context',
  'contributors',
  'secondaryFindings',
  'counterSignals',
  'associatedSignals',
  'risks',
  'missingContext',
]

const indexStoryPlan = (storyPlan) => {
  const items = storyPlan?.mainOutcome ? [storyPlan.mainOutcome] : []
  PLAN_COLLECTIONS.forEach((key) => {
    if (Array.isArray(storyPlan?.[key])) items.push(...storyPlan[key])
  })
  return new Map(items.filter((item) => item?.id).map((item) => [item.id, item]))
}

function ExecutiveStory({ analysis, language, copy, onStartAnalysis, onOpenHistory }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const story = analysis?.generatedStory
  const generation = analysis?.storyGeneration
  const storyPlan = analysis?.storyPlan
  const storyAuditItems = analysis?.storyAudit?.itemAudits
  const insights = analysis?.insights
  const generationStatus = generation?.status || null
  const generationFailed = generationStatus === 'Failed'
  const sections = Array.isArray(story?.sections)
    ? [...story.sections].sort((left, right) => left.order - right.order)
    : []
  const planById = useMemo(() => indexStoryPlan(storyPlan), [storyPlan])
  const auditById = useMemo(() => new Map(
    (Array.isArray(storyAuditItems) ? storyAuditItems : [])
      .filter((item) => item?.sourceItemId)
      .map((item) => [item.sourceItemId, item]),
  ), [storyAuditItems])
  const insightById = useMemo(() => new Map(
    (Array.isArray(insights) ? insights : [])
      .filter((insight) => insight?.id)
      .map((insight) => [insight.id, insight]),
  ), [insights])
  const formatDate = (value) => {
    if (!value) return null
    const date = new Date(value)
    return Number.isNaN(date.getTime())
      ? null
      : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
  }
  const generatedAt = formatDate(generation?.generatedAt)
  const generationLanguage = generation?.language || null
  const languageMismatch = generationLanguage && generationLanguage !== language

  if (!analysis) {
    return (
      <section className="empty-state" aria-labelledby="story-no-analysis-title">
        <p className="empty-state-kicker">{copy.eyebrow}</p>
        <h2 id="story-no-analysis-title">{copy.noAnalysisTitle}</h2>
        <p>{copy.noAnalysisDescription}</p>
        <div className="empty-state-actions">
          <button type="button" className="secondary-button" onClick={onStartAnalysis}>{copy.startAnalysis}</button>
          <button type="button" className="secondary-button" onClick={onOpenHistory}>{copy.openHistory}</button>
        </div>
      </section>
    )
  }

  if (generationFailed) {
    return (
      <section className="empty-state story-state-panel" role="alert" aria-labelledby="story-failed-title">
        <p className="empty-state-kicker">{copy.generationFailedEyebrow}</p>
        <h2 id="story-failed-title">{copy.generationFailedTitle}</h2>
        <p>{generation.failureReason || copy.generationFailedDescription}</p>
      </section>
    )
  }

  if (!story || sections.length === 0) {
    return (
      <section className="empty-state story-state-panel" role="status" aria-labelledby="story-unavailable-title">
        <p className="empty-state-kicker">{copy.eyebrow}</p>
        <h2 id="story-unavailable-title">{copy.unavailableTitle}</h2>
        <p>{generation ? copy.metadataWithoutStory : copy.historicalUnavailable}</p>
      </section>
    )
  }

  return (
    <article className="executive-story" aria-labelledby="executive-story-title">
      <header className="executive-story-hero">
        <div className="executive-story-heading">
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="executive-story-title">{story.title}</h2>
          <p className="executive-story-file">{analysis.fileName || copy.unavailable}</p>
        </div>
        <dl className="story-generation-metadata">
          <div><dt>{copy.generationStatus}</dt><dd>{copy.generationStatuses[generationStatus] || generationStatus || copy.unavailable}</dd></div>
          {generatedAt && <div><dt>{copy.generatedAt}</dt><dd>{generatedAt}</dd></div>}
          {generation?.modelIdentifier && <div><dt>{copy.provider}</dt><dd>{generation.modelIdentifier}</dd></div>}
        </dl>
      </header>

      <section className="executive-summary" aria-labelledby="executive-summary-title">
        <p className="eyebrow">{copy.summaryEyebrow}</p>
        <h3 id="executive-summary-title">{copy.executiveSummary}</h3>
        <p>{story.executiveSummary}</p>
      </section>

      {(!generationLanguage || languageMismatch) && (
        <aside className="story-language-notice" role="note">
          <strong>{copy.languageNoticeTitle}</strong>
          <p>
            {generationLanguage
              ? copy.languageMismatch
                .replace('{storyLanguage}', copy.languageNames[generationLanguage] || generationLanguage)
              : copy.languageUnavailable}
          </p>
        </aside>
      )}

      <div className="executive-story-sections">
        {sections.map((section) => (
          <StorySection
            key={`${section.order}-${section.type}`}
            section={section}
            planById={planById}
            auditById={auditById}
            insightById={insightById}
            copy={copy}
          />
        ))}
      </div>
    </article>
  )
}

export default ExecutiveStory
