function SelectedFileCard({ file, language, copy, uploading, onRemove }) {
  const extension = file.name.split('.').pop()?.toUpperCase() || copy.unknownType
  const formattedSize = new Intl.NumberFormat(
    language === 'tr' ? 'tr-TR' : 'en-US',
    { minimumFractionDigits: 2, maximumFractionDigits: 2 },
  ).format(file.size / 1024 / 1024)

  return (
    <div className="selected-file-card">
      <span className="file-type-indicator" aria-hidden="true">{extension}</span>

      <div className="selected-file-details">
        <p className="selected-file-label"><span aria-hidden="true">✓</span>{copy.ready}</p>
        <strong title={file.name}>{file.name}</strong>
        <span>{extension} · {formattedSize} MB</span>
      </div>

      <button
        type="button"
        className="remove-file-button"
        disabled={uploading}
        aria-label={`${copy.removeFile}: ${file.name}`}
        onClick={onRemove}
      >
        {copy.remove}
      </button>
    </div>
  )
}

export default SelectedFileCard
