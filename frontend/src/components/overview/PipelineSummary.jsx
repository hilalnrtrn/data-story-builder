function PipelineSummary({ analysis, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const formatNumber = (value) => new Intl.NumberFormat(locale).format(value)
  const storyStatus = analysis.storyGeneration?.status
  const storyGeneratedLabel = copy.generationStatuses[storyStatus]
    || storyStatus
    || copy.notAvailable
  const auditAvailable = Boolean(analysis.storyAudit || analysis.fullStoryAudit)

  const items = [
    { label: copy.insights, value: formatNumber(analysis.insights.length) },
    { label: copy.relationships, value: formatNumber(analysis.relationships.length) },
    { label: copy.insightIntegrity, value: formatNumber(analysis.insightIntegrity.length) },
    { label: copy.storyGenerated, value: storyGeneratedLabel },
    { label: copy.storyAudited, value: auditAvailable ? copy.available : copy.notAvailable },
    { label: copy.hypotheses, value: formatNumber(analysis.hypotheses.length) },
  ]

  return (
    <details className="overview-section pipeline-summary">
      <summary id="pipeline-summary-title">
        <span>{copy.title}</span>
        <span aria-hidden="true">+</span>
      </summary>
      <dl className="pipeline-summary-grid">
          {items.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
    </details>
  )
}

export default PipelineSummary
