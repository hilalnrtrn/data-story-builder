import StatePanel from './StatePanel.jsx'

function AnalysisProgressPanel({ phase, fileName, copy }) {
  const isLoadingDetail = phase === 'loading-detail'

  return (
    <StatePanel
      variant="loading"
      size="panel"
      className="analysis-progress-panel"
      role="status"
      ariaLive="polite"
      ariaAtomic="true"
      icon={<span className="indeterminate-spinner" aria-hidden="true" />}
    >
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

        {!isLoadingDetail && <p className="pipeline-note">{copy.indeterminateNote}</p>}
      </div>
    </StatePanel>
  )
}

export default AnalysisProgressPanel
