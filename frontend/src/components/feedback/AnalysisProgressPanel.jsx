function AnalysisProgressPanel({ phase, fileName, copy }) {
  const isLoadingDetail = phase === 'loading-detail'

  return (
    <section
      className="analysis-progress-panel"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div
        className="indeterminate-spinner"
        role="img"
        aria-label={copy.indicatorLabel}
      />

      <div className="analysis-progress-copy">
        <p className="analysis-progress-kicker">
          {isLoadingDetail ? copy.detailKicker : copy.analysisKicker}
        </p>
        <h3>{isLoadingDetail ? copy.detailTitle : copy.analysisTitle}</h3>
        <p>
          {isLoadingDetail ? copy.detailDescription : copy.analysisDescription}
        </p>

        {fileName && (
          <p className="analysis-progress-file">
            <span>{copy.fileLabel}</span>
            <strong>{fileName}</strong>
          </p>
        )}

        {!isLoadingDetail && (
          <>
            <ul className="pipeline-explanation">
              {copy.steps.map((step) => <li key={step}>{step}</li>)}
            </ul>
            <p className="pipeline-note">{copy.informationalNote}</p>
          </>
        )}
      </div>
    </section>
  )
}

export default AnalysisProgressPanel
