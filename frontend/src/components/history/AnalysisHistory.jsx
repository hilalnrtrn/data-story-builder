function AnalysisHistory({
  analyses,
  currentAnalysisId,
  language,
  loadState,
  loadError,
  selectingId,
  selectionError,
  copy,
  onRetry,
  onSelect,
}) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const numberFormatter = new Intl.NumberFormat(locale)
  const scoreFormatter = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  })
  const formatNumber = (value) => (
    Number.isFinite(value) ? numberFormatter.format(value) : copy.notAvailable
  )
  const formatScore = (value) => (
    Number.isFinite(value) ? `${scoreFormatter.format(value)}%` : copy.notAvailable
  )
  const formatDate = (value) => {
    if (!value) return copy.notAvailable
    const date = new Date(value)
    return Number.isNaN(date.getTime())
      ? copy.notAvailable
      : new Intl.DateTimeFormat(locale, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date)
  }
  const statusClass = (status) => {
    if (status === 'Completed') return 'healthy'
    if (status === 'Failed') return 'unhealthy'
    if (status === 'Processing') return 'warning'
    return 'neutral-status'
  }

  if (loadState === 'loading') {
    return (
      <section className="history-state" role="status" aria-live="polite">
        <span className="indeterminate-spinner" aria-hidden="true" />
        <div>
          <h2>{copy.loadingTitle}</h2>
          <p>{copy.loadingDescription}</p>
        </div>
      </section>
    )
  }

  if (loadState === 'failed') {
    return (
      <section className="history-state" role="alert">
        <div>
          <h2>{copy.errorTitle}</h2>
          <p>{loadError || copy.errorDescription}</p>
          <button type="button" className="secondary-button" onClick={onRetry}>
            {copy.retry}
          </button>
        </div>
      </section>
    )
  }

  if (loadState === 'succeeded' && analyses.length === 0) {
    return (
      <section className="history-state" role="status">
        <div>
          <h2>{copy.emptyTitle}</h2>
          <p>{copy.emptyDescription}</p>
        </div>
      </section>
    )
  }

  return (
    <section className="history-panel" aria-labelledby="history-list-title">
      <div className="history-heading">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2 id="history-list-title">{copy.title}</h2>
        <p>{copy.description}</p>
      </div>

      {selectionError && (
        <p className="message error" role="alert">{selectionError}</p>
      )}

      <ul className="history-list">
        {analyses.map((analysis) => {
          const isCurrent = analysis?.id === currentAnalysisId
          const isSelecting = selectingId === analysis?.id
          const statusLabel = copy.statuses[analysis?.status]
            || analysis?.status
            || copy.notAvailable

          return (
            <li className="history-item" key={analysis.id}>
              <article>
                <div className="history-item-heading">
                  <div>
                    <p className="history-file-type">
                      {analysis.fileType || copy.notAvailable}
                    </p>
                    <h3>{analysis.fileName || copy.notAvailable}</h3>
                  </div>
                  <div className="history-badges">
                    {isCurrent && (
                      <span className="status neutral-status">{copy.currentAnalysis}</span>
                    )}
                    <span className={`status ${statusClass(analysis.status)}`}>
                      {statusLabel}
                    </span>
                  </div>
                </div>

                <dl className="history-metadata">
                  <div><dt>{copy.created}</dt><dd>{formatDate(analysis.createdAt)}</dd></div>
                  <div><dt>{copy.completed}</dt><dd>{formatDate(analysis.completedAt)}</dd></div>
                  <div><dt>{copy.rows}</dt><dd>{formatNumber(analysis.rowCount)}</dd></div>
                  <div><dt>{copy.columns}</dt><dd>{formatNumber(analysis.columnCount)}</dd></div>
                  <div><dt>{copy.insights}</dt><dd>{formatNumber(analysis.insightCount)}</dd></div>
                  <div><dt>{copy.dataQuality}</dt><dd>{formatScore(analysis.dataQualityScore)}</dd></div>
                </dl>

                <button
                  type="button"
                  className="secondary-button history-open-button"
                  onClick={() => onSelect(analysis.id)}
                  disabled={Boolean(selectingId)}
                  aria-label={`${copy.openAnalysis}: ${analysis.fileName || copy.notAvailable}`}
                >
                  {isSelecting ? copy.loadingAnalysis : copy.openAnalysis}
                </button>
              </article>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default AnalysisHistory
