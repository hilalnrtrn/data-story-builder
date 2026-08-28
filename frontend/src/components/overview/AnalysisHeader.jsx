function AnalysisHeader({ analysis, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const columns = analysis.profile?.datasetProfile?.columns
  const datetimeColumn = Array.isArray(columns)
    ? columns.find((column) => column?.dataType === 'datetime')
    : null

  const formatDateTime = (value) => {
    if (!value) return copy.notAvailable
    const date = new Date(value)
    return Number.isNaN(date.getTime())
      ? copy.notAvailable
      : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
  }

  const formatPeriodDate = (value) => {
    if (!value) return null
    const date = new Date(`${value}T00:00:00`)
    return Number.isNaN(date.getTime())
      ? value
      : new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)
  }

  const periodStart = formatPeriodDate(datetimeColumn?.minDate)
  const periodEnd = formatPeriodDate(datetimeColumn?.maxDate)
  const datasetPeriod = periodStart && periodEnd
    ? `${periodStart} – ${periodEnd}`
    : copy.notAvailable
  const shortenedId = analysis.id.length > 16
    ? `${analysis.id.slice(0, 8)}…${analysis.id.slice(-4)}`
    : analysis.id
  return (
    <section className="overview-analysis-header" aria-labelledby="analysis-summary-title">
      <div className="overview-analysis-heading">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="analysis-summary-title">{copy.detailsTitle}</h2>
        </div>
      </div>

      <dl className="analysis-metadata-grid">
        <div><dt>{copy.fileName}</dt><dd>{analysis.fileName || copy.notAvailable}</dd></div>
        <div><dt>{copy.analysisId}</dt><dd title={analysis.id}>{shortenedId}</dd></div>
        <div><dt>{copy.createdAt}</dt><dd>{formatDateTime(analysis.createdAt)}</dd></div>
        <div><dt>{copy.completedAt}</dt><dd>{formatDateTime(analysis.completedAt)}</dd></div>
        <div><dt>{copy.datasetPeriod}</dt><dd>{datasetPeriod}</dd></div>
      </dl>
    </section>
  )
}

export default AnalysisHeader
