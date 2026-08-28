import { useEffect, useRef, useState } from 'react'

function DatasetDropzone({ selectedFile, uploading, hasError, copy, onFilesSelected }) {
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    if (!selectedFile && inputRef.current) {
      inputRef.current.value = ''
    }
  }, [selectedFile])

  const openFilePicker = () => {
    if (!uploading) {
      inputRef.current?.click()
    }
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)

    if (!uploading) {
      onFilesSelected(event.dataTransfer.files)
    }
  }

  return (
    <div
      className={`dataset-dropzone${isDragging ? ' is-dragging' : ''}`}
      aria-labelledby="dropzone-title"
      aria-describedby={`dropzone-instructions${hasError ? ' upload-error' : ''}`}
      onClick={(event) => {
        if (event.target !== inputRef.current) {
          openFilePicker()
        }
      }}
      onDragEnter={(event) => {
        event.preventDefault()
        if (!uploading) setIsDragging(true)
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setIsDragging(false)
        }
      }}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        className="visually-hidden-file-input"
        type="file"
        accept=".csv,.xlsx"
        aria-label={copy.chooseFile}
        disabled={uploading}
        onChange={(event) => onFilesSelected(event.target.files)}
      />

      <span className="upload-symbol" aria-hidden="true">
        <span className="upload-symbol-arrow">↑</span>
      </span>

      <div className="dropzone-copy">
        <h3 id="dropzone-title">
          {isDragging ? copy.dropActive : copy.dropTitle}
        </h3>
        <p id="dropzone-instructions">{copy.or}</p>
      </div>

      <button
        type="button"
        className="browse-button"
        disabled={uploading}
        onClick={(event) => {
          event.stopPropagation()
          openFilePicker()
        }}
      >
        {selectedFile ? copy.replaceFile : copy.chooseFile}
      </button>

      <p className="dropzone-helper">{copy.helper}</p>
    </div>
  )
}

export default DatasetDropzone
