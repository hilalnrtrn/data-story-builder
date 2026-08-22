import { useEffect, useState } from 'react'
import './App.css'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const SUPPORTED_EXTENSIONS = ['csv', 'xlsx']

function App() {
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)

  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

        const response = await fetch(`${apiBaseUrl}/api/health`)

        if (!response.ok) {
          throw new Error('System health request failed.')
        }

        const data = await response.json()
        setSystemStatus(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchSystemStatus()
  }, [])

  const renderStatus = (status) => {
    if (status === 'healthy') {
      return <span className="status healthy">✓ Healthy</span>
    }

    return <span className="status unhealthy">✕ Unhealthy</span>
  }

  const validateFile = (file) => {
    if (!file) {
      return 'Please select a file.'
    }

    if (file.size === 0) {
      return 'The selected file is empty.'
    }

    if (file.size > MAX_FILE_SIZE) {
      return 'The selected file exceeds the 10 MB limit.'
    }

    const extension = file.name
      .split('.')
      .pop()
      ?.toLowerCase()

    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      return 'Only CSV and XLSX files are supported.'
    }

    return null
  }

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] ?? null

    setAnalysisResult(null)

    if (!file) {
      setSelectedFile(null)
      setUploadError(null)
      return
    }

    const validationError = validateFile(file)

    if (validationError) {
      setSelectedFile(null)
      setUploadError(validationError)
      event.target.value = ''
      return
    }

    setSelectedFile(file)
    setUploadError(null)
  }

  const handleUpload = async () => {
    const validationError = validateFile(selectedFile)

    if (validationError) {
      setUploadError(validationError)
      return
    }

    setUploading(true)
    setUploadError(null)
    setAnalysisResult(null)

    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(`${apiBaseUrl}/api/analyses`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        let message = 'Upload failed.'

        try {
          const errorBody = await response.json()

          message =
            errorBody.error ||
            errorBody.detail ||
            message
        } catch {
          // Response body was not JSON.
        }

        throw new Error(message)
      }

      const result = await response.json()
      setAnalysisResult(result)
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <main className="page">
      <section className="status-card">
        <p className="eyebrow">DATA STORY BUILDER</p>

        <h1>System Status</h1>

        <p className="description">
          Technical services required by Data Story Builder.
        </p>

        {loading && (
          <p className="message">
            Checking services...
          </p>
        )}

        {error && (
          <p className="message error">
            Unable to reach backend: {error}
          </p>
        )}

        {systemStatus && (
          <div className="services">
            <div className="service-row">
              <span>Backend API</span>
              {renderStatus(systemStatus.backend?.status)}
            </div>

            <div className="service-row">
              <span>Analytics Service</span>
              {renderStatus(systemStatus.analytics?.status)}
            </div>

            <div className="service-row">
              <span>PostgreSQL</span>
              {renderStatus(systemStatus.database?.status)}
            </div>
          </div>
        )}

        {systemStatus && (
          <div className="overall">
            Overall system: {renderStatus(systemStatus.status)}
          </div>
        )}
      </section>

      <section className="upload-card">
        <p className="eyebrow">DATA INGESTION</p>

        <h2>Upload Dataset</h2>

        <p className="description">
          Select a CSV or XLSX dataset to prepare for analysis.
        </p>

        <div className="upload-box">
          <input
            id="dataset-file"
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileChange}
          />

          <p className="upload-hint">
            Supported formats: CSV, XLSX · Maximum size: 10 MB
          </p>
        </div>

        {selectedFile && (
          <div className="selected-file">
            <strong>Selected file:</strong>
            <span>{selectedFile.name}</span>
            <span>
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </span>
          </div>
        )}

        {uploadError && (
          <p className="message error">
            {uploadError}
          </p>
        )}

        <button
          type="button"
          className="upload-button"
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
        >
          {uploading ? 'Preparing dataset...' : 'Upload and Prepare'}
        </button>

        {analysisResult && (
          <div className="analysis-result">
            <h3>Preparation Complete</h3>

            <div className="result-grid">
              <div>
                <span>Analysis ID</span>
                <strong>{analysisResult.analysisId}</strong>
              </div>

              <div>
                <span>File</span>
                <strong>{analysisResult.fileName}</strong>
              </div>

              <div>
                <span>Rows Read</span>
                <strong>
                  {analysisResult.preparationReport?.rowsRead}
                </strong>
              </div>

              <div>
                <span>Rows Prepared</span>
                <strong>
                  {analysisResult.preparationReport?.rowsPrepared}
                </strong>
              </div>

              <div>
                <span>Columns</span>
                <strong>
                  {analysisResult.preparedSchema?.columnCount}
                </strong>
              </div>

              <div>
                <span>Duplicates Removed</span>
                <strong>
                  {analysisResult.preparationReport?.duplicatesRemoved}
                </strong>
              </div>

              <div>
                <span>Missing Values</span>
                <strong>
                  {analysisResult.preparationReport?.missingValuesDetected}
                </strong>
              </div>

              <div>
                <span>Date Errors</span>
                <strong>
                  {analysisResult.preparationReport?.dateConversionErrors}
                </strong>
              </div>
            </div>
          </div>
        )}
      </section>
    </main>
  )
}

export default App