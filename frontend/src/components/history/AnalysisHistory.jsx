function AnalysisHistory({ analyses, currentAnalysisId, language, loadState, loadError, selectingId, selectionError, copy, onRetry, onSelect }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const numberFormatter = new Intl.NumberFormat(locale)
  const scoreFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 })
  const formatNumber = (value) => Number.isFinite(value) ? numberFormatter.format(value) : copy.notAvailable
  const formatScore = (value) => Number.isFinite(value) ? `${scoreFormatter.format(value)}%` : copy.notAvailable
  const formatDate = (value) => {
    if (!value) return copy.notAvailable
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? copy.notAvailable : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
  }
  const completedCount = analyses.filter((analysis) => analysis?.status === 'Completed').length
  const failedCount = analyses.filter((analysis) => analysis?.status === 'Failed').length

  if (loadState === 'loading') {
    return <section className="history-state history-loading" role="status" aria-live="polite" aria-label={copy.loadingTitle}><div className="history-state-copy"><h2>{copy.loadingTitle}</h2><p>{copy.loadingDescription}</p></div><div className="history-skeleton" aria-hidden="true">{[0, 1, 2, 3].map((item) => <span key={item} />)}</div></section>
  }

  if (loadState === 'failed') {
    return <section className="history-state" role="alert"><div className="history-state-copy"><p className="eyebrow">{copy.errorEyebrow}</p><h2>{copy.errorTitle}</h2><p>{loadError || copy.errorDescription}</p><button type="button" className="secondary-button" onClick={onRetry}>{copy.retry}</button></div></section>
  }

  if (loadState === 'succeeded' && analyses.length === 0) {
    return <section className="history-state" role="status"><div className="history-state-copy"><p className="eyebrow">{copy.eyebrow}</p><h2>{copy.emptyTitle}</h2><p>{copy.emptyDescription}</p></div></section>
  }

  return (
    <section className="history-panel" aria-labelledby="history-list-title">
      <header className="history-heading"><div><p className="eyebrow">{copy.eyebrow}</p><h2 id="history-list-title">{copy.archiveTitle}</h2><p>{copy.description}</p></div><p className="history-count">{copy.analysisCount.replace('{count}', numberFormatter.format(analyses.length))}</p></header>
      <dl className="history-summary" aria-label={copy.summaryLabel}><div><dt>{copy.total}</dt><dd>{formatNumber(analyses.length)}</dd></div><div><dt>{copy.statuses.Completed}</dt><dd>{formatNumber(completedCount)}</dd></div><div><dt>{copy.statuses.Failed}</dt><dd>{formatNumber(failedCount)}</dd></div></dl>
      {selectionError && <p className="message error history-selection-error" role="alert">{selectionError}</p>}
      <ul className="history-list">
        {analyses.map((analysis) => {
          const isCurrent = analysis?.id === currentAnalysisId
          const isSelecting = selectingId === analysis?.id
          const status = analysis?.status || 'Unknown'
          const statusLabel = copy.statuses[status] || status || copy.notAvailable
          return (
            <li className={`history-item status-${status.toLowerCase()}${isCurrent ? ' is-current' : ''}`} key={analysis.id}>
              <span className="history-marker" aria-hidden="true" />
              <article>
                <div className="history-primary"><div className="history-identity"><h3 title={analysis.fileName || undefined}>{analysis.fileName || copy.notAvailable}</h3><p><time dateTime={analysis.createdAt || undefined} title={analysis.createdAt || undefined}>{formatDate(analysis.createdAt)}</time><span aria-hidden="true"> · </span>{analysis.fileType || copy.notAvailable}</p></div><div className="history-state-labels">{isCurrent && <span className="history-current">{copy.currentAnalysis}</span>}<span className="history-status"><span aria-hidden="true" />{statusLabel}</span></div></div>
                <dl className="history-signals" aria-label={copy.contextLabel}><div><dt>{copy.insights}</dt><dd>{formatNumber(analysis.insightCount)}</dd></div><div><dt>{copy.rows}</dt><dd>{formatNumber(analysis.rowCount)}</dd></div><div><dt>{copy.dataQuality}</dt><dd>{formatScore(analysis.dataQualityScore)}</dd></div></dl>
                <div className="history-actions">
                  <details className="history-technical"><summary>{copy.technicalDetails}</summary><dl><div><dt>{copy.analysisId}</dt><dd><code>{analysis.id}</code></dd></div><div><dt>{copy.status}</dt><dd>{statusLabel}</dd></div><div><dt>{copy.created}</dt><dd title={analysis.createdAt || undefined}>{formatDate(analysis.createdAt)}</dd></div><div><dt>{copy.completed}</dt><dd title={analysis.completedAt || undefined}>{formatDate(analysis.completedAt)}</dd></div><div><dt>{copy.columns}</dt><dd>{formatNumber(analysis.columnCount)}</dd></div><div><dt>{copy.analysisVersion}</dt><dd>{analysis.analysisVersion || copy.notAvailable}</dd></div></dl></details>
                  <button type="button" className="history-open-button" onClick={() => onSelect(analysis.id)} disabled={Boolean(selectingId) || isCurrent} aria-label={`${copy.openAnalysis}: ${analysis.fileName || copy.notAvailable}`}>{isCurrent ? copy.currentAnalysis : isSelecting ? copy.loadingAnalysis : copy.openAnalysis}<span aria-hidden="true">›</span></button>
                </div>
              </article>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default AnalysisHistory
