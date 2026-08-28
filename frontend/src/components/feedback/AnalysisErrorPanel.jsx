function AnalysisErrorPanel({ message, canRetryDetail, copy, onRetryDetail, onChooseAnother }) {
  return (
    <section className="analysis-error-panel" id="upload-error" role="alert">
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
    </section>
  )
}

export default AnalysisErrorPanel
