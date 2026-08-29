import StatePanel from './StatePanel.jsx'

function AnalysisErrorPanel({ message, canRetryDetail, copy, onRetryDetail, onChooseAnother }) {
  return (
    <StatePanel variant="error" size="panel" className="analysis-error-panel" role="alert" icon={<span className="analysis-error-symbol" aria-hidden="true">!</span>}>
      <div>
        <p className="analysis-error-kicker">{copy.kicker}</p>
        <h3>{copy.title}</h3>
        <p className="analysis-error-message">{message}</p>
        <p className="analysis-error-guidance">
          {canRetryDetail ? copy.detailGuidance : copy.uploadGuidance}
        </p>
      </div>

      <div className="analysis-error-actions">
        {canRetryDetail && (
          <button type="button" className="secondary-button" onClick={onRetryDetail}>
            {copy.retryDetail}
          </button>
        )}
        <button type="button" className="secondary-button" onClick={onChooseAnother}>
          {copy.chooseAnother}
        </button>
      </div>
    </StatePanel>
  )
}

export default AnalysisErrorPanel
