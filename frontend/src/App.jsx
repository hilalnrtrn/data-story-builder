import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AnalysisApiError,
  getAnalysisDetail,
  getAnalysisHistory,
  uploadAnalysis,
} from './api/analyses.js'
import AppShell from './components/layout/AppShell.jsx'
import AnalysisHistory from './components/history/AnalysisHistory.jsx'
import AnalysisErrorPanel from './components/feedback/AnalysisErrorPanel.jsx'
import AnalysisProgressPanel from './components/feedback/AnalysisProgressPanel.jsx'
import AnalysisHeader from './components/overview/AnalysisHeader.jsx'
import DatasetHealth from './components/overview/DatasetHealth.jsx'
import KeyFindings from './components/overview/KeyFindings.jsx'
import PipelineSummary from './components/overview/PipelineSummary.jsx'
import SummaryCards from './components/overview/SummaryCards.jsx'
import DatasetDropzone from './components/upload/DatasetDropzone.jsx'
import SelectedFileCard from './components/upload/SelectedFileCard.jsx'
import { translations } from './i18n/translations.js'
import { mapAnalysisDetail } from './models/analysisMappers.js'
import './App.css'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const SUPPORTED_EXTENSIONS = ['csv', 'xlsx']

const LANGUAGE_STORAGE_KEY = 'data-story-builder-language'
const ANALYSIS_SESSION_KEY = 'data-story-builder-current-analysis-id'

const getInitialLanguage = () => {
  try {
    const savedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return savedLanguage === 'en' || savedLanguage === 'tr'
      ? savedLanguage
      : 'tr'
  } catch {
    return 'tr'
  }
}

const getStoredAnalysisId = () => {
  try {
    const analysisId = sessionStorage.getItem(ANALYSIS_SESSION_KEY)?.trim()
    return analysisId || null
  } catch {
    return null
  }
}

const storeAnalysisId = (analysisId) => {
  try {
    sessionStorage.setItem(ANALYSIS_SESSION_KEY, analysisId)
  } catch {
    // The canonical analysis remains available in memory for this page load.
  }
}

const removeStoredAnalysisId = () => {
  try {
    sessionStorage.removeItem(ANALYSIS_SESSION_KEY)
  } catch {
    // Storage is optional; the application remains usable without it.
  }
}

function App() {
  const [initialAnalysisId] = useState(getStoredAnalysisId)
  const [language, setLanguage] = useState(getInitialLanguage)
  const [activeSection, setActiveSection] = useState(
    initialAnalysisId ? 'overview' : 'new-analysis',
  )
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [analysisRequestState, setAnalysisRequestState] = useState(
    initialAnalysisId ? 'restoring' : 'idle',
  )
  const [analysisError, setAnalysisError] = useState(null)
  const [currentAnalysis, setCurrentAnalysis] = useState(null)
  const [restoreNotice, setRestoreNotice] = useState(null)
  const [historyItems, setHistoryItems] = useState([])
  const [historyLoadState, setHistoryLoadState] = useState('idle')
  const [historyError, setHistoryError] = useState(null)
  const [historySelectionId, setHistorySelectionId] = useState(null)
  const [historySelectionError, setHistorySelectionError] = useState(null)
  const restoreStartedRef = useRef(false)
  const copy = translations[language]
  const uploading =
    analysisRequestState === 'uploading'
    || analysisRequestState === 'loading-detail'

  const sectionHeaders = {
    'new-analysis': copy.sections.newAnalysis,
    overview: copy.sections.overview,
    insights: copy.sections.insights,
    'executive-story': copy.sections.executiveStory,
    'story-audit': copy.sections.storyAudit,
    hypotheses: copy.sections.hypotheses,
    history: copy.sections.history,
  }

  const futureSectionAvailability = {
    insights: copy.empty.day18,
    'executive-story': copy.empty.day19,
    'story-audit': copy.empty.day19,
    hypotheses: copy.empty.day19,
  }

  useEffect(() => {
    document.documentElement.lang = language

    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
    } catch {
      // The selected language still applies for the current session.
    }
  }, [language])

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
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }

    fetchSystemStatus()
  }, [])

  const renderStatus = (status) => {
    if (status === 'healthy') {
      return (
        <span className="status healthy">
          <span aria-hidden="true">●</span> {copy.health.healthy}
        </span>
      )
    }

    return (
      <span className="status unhealthy">
        <span aria-hidden="true">●</span> {copy.health.unhealthy}
      </span>
    )
  }

  const validateFile = (file) => {
    if (!file) {
      return copy.upload.errors.selectFile
    }

    if (file.size === 0) {
      return copy.upload.errors.emptyFile
    }

    if (file.size > MAX_FILE_SIZE) {
      return copy.upload.errors.tooLarge
    }

    const extension = file.name.split('.').pop()?.toLowerCase()

    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      return copy.upload.errors.unsupported
    }

    return null
  }

  const handleFilesSelected = (files) => {
    if (!files || files.length === 0) {
      return
    }

    setAnalysisError(null)
    setAnalysisRequestState('idle')

    if (files.length !== 1) {
      setSelectedFile(null)
      setUploadError(copy.upload.errors.multipleFiles)
      return
    }

    const file = files[0]
    const validationError = validateFile(file)

    if (validationError) {
      setSelectedFile(null)
      setUploadError(validationError)
      return
    }

    setSelectedFile(file)
    setUploadError(null)
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    setUploadError(null)
    setAnalysisError(null)
    setAnalysisRequestState('idle')
  }

  const handleUpload = async () => {
    const validationError = validateFile(selectedFile)

    if (validationError) {
      setUploadError(validationError)
      return
    }

    setAnalysisRequestState('uploading')
    setUploadError(null)
    setAnalysisError(null)

    let uploadedAnalysisId = null

    try {
      uploadedAnalysisId = await uploadAnalysis(selectedFile)
      storeAnalysisId(uploadedAnalysisId)
      setAnalysisRequestState('loading-detail')
      await loadPersistedAnalysis(uploadedAnalysisId)
    } catch (error) {
      const normalizedError = error instanceof AnalysisApiError
        ? error
        : new AnalysisApiError('')

      setAnalysisError({
        error: normalizedError,
        phase: uploadedAnalysisId ? 'detail' : 'upload',
        analysisId: normalizedError.analysisId || uploadedAnalysisId,
      })
      setAnalysisRequestState('failed')
    }
  }

  const loadPersistedAnalysis = useCallback(async (analysisId) => {
    const persistedDetail = await getAnalysisDetail(analysisId)
    const mappedAnalysis = mapAnalysisDetail(persistedDetail)

    setCurrentAnalysis(mappedAnalysis)
    setAnalysisRequestState('succeeded')
    setActiveSection('overview')
  }, [])

  const loadAnalysisHistory = useCallback(async () => {
    setHistoryLoadState('loading')
    setHistoryError(null)

    try {
      const persistedHistory = await getAnalysisHistory()
      setHistoryItems(persistedHistory)
      setHistoryLoadState('succeeded')
    } catch (error) {
      setHistoryError(
        error instanceof AnalysisApiError ? error : new AnalysisApiError(''),
      )
      setHistoryLoadState('failed')
    }
  }, [])

  useEffect(() => {
    if (!initialAnalysisId || restoreStartedRef.current) return

    restoreStartedRef.current = true

    const restoreAnalysis = async () => {
      try {
        await loadPersistedAnalysis(initialAnalysisId)
      } catch (error) {
        const normalizedError = error instanceof AnalysisApiError
          ? error
          : new AnalysisApiError('')

        if (normalizedError.isNotFound) {
          removeStoredAnalysisId()
          setAnalysisError(null)
          setRestoreNotice('not-found')
          setAnalysisRequestState('idle')
          return
        }

        setAnalysisError({
          error: normalizedError,
          phase: 'restore',
          analysisId: normalizedError.analysisId || initialAnalysisId,
        })
        setAnalysisRequestState('failed')
      }
    }

    restoreAnalysis()
  }, [initialAnalysisId, loadPersistedAnalysis])

  const handleRetryDetail = async () => {
    if (!analysisError?.analysisId || analysisError.phase !== 'detail') return

    const analysisId = analysisError.analysisId
    setAnalysisError(null)
    setAnalysisRequestState('loading-detail')

    try {
      await loadPersistedAnalysis(analysisId)
    } catch (error) {
      const normalizedError = error instanceof AnalysisApiError
        ? error
        : new AnalysisApiError('')

      setAnalysisError({
        error: normalizedError,
        phase: 'detail',
        analysisId: normalizedError.analysisId || analysisId,
      })
      setAnalysisRequestState('failed')
    }
  }

  const handleChooseAnotherFile = () => {
    setSelectedFile(null)
    setUploadError(null)
    setAnalysisError(null)
    setAnalysisRequestState('idle')
  }

  const handleStartAfterRestoreFailure = () => {
    setAnalysisError(null)
    setAnalysisRequestState('idle')
    setActiveSection('new-analysis')
  }

  const handleRetryRestore = async () => {
    if (!analysisError?.analysisId || analysisError.phase !== 'restore') return

    const analysisId = analysisError.analysisId
    setAnalysisError(null)
    setAnalysisRequestState('restoring')

    try {
      await loadPersistedAnalysis(analysisId)
    } catch (error) {
      const normalizedError = error instanceof AnalysisApiError
        ? error
        : new AnalysisApiError('')

      if (normalizedError.isNotFound) {
        removeStoredAnalysisId()
        setRestoreNotice('not-found')
        setAnalysisRequestState('idle')
        return
      }

      setAnalysisError({
        error: normalizedError,
        phase: 'restore',
        analysisId: normalizedError.analysisId || analysisId,
      })
      setAnalysisRequestState('failed')
    }
  }

  const handleSectionChange = (section) => {
    setActiveSection(section)

    if (section === 'history' && historyLoadState === 'idle') {
      loadAnalysisHistory()
    }
  }

  const handleHistorySelection = async (analysisId) => {
    if (!analysisId || historySelectionId) return

    setHistorySelectionId(analysisId)
    setHistorySelectionError(null)

    try {
      setAnalysisError(null)
      setRestoreNotice(null)
      await loadPersistedAnalysis(analysisId)
      storeAnalysisId(analysisId)
    } catch (error) {
      setHistorySelectionError(
        error instanceof AnalysisApiError ? error : new AnalysisApiError(''),
      )
    } finally {
      setHistorySelectionId(null)
    }
  }

  const getAnalysisErrorMessage = () => {
    if (!analysisError) return null
    if (analysisError.error.isNotFound) return copy.integration.analysisNotFound
    if (analysisError.error.message) return analysisError.error.message
    if (analysisError.phase === 'restore') return copy.restoration.failed
    if (analysisError.phase === 'detail') {
      return copy.integration.detailAfterCompletionFailed
    }
    return copy.integration.uploadFailed
  }

  const renderHealthStatus = () => (
    <section className="status-card" aria-labelledby="service-health-title">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">{copy.health.eyebrow}</p>
          <h2 id="service-health-title">{copy.health.title}</h2>
        </div>

        {systemStatus && renderStatus(systemStatus.status)}
      </div>

      {loading && (
        <p className="message" role="status">{copy.health.checking}</p>
      )}

      {error && (
        <p className="message error" role="alert">
          {copy.health.unreachable} {copy.health.requestFailed}
        </p>
      )}

      {systemStatus && (
        <div className="services">
          <div className="service-row">
            <span>{copy.health.backend}</span>
            {renderStatus(systemStatus.backend?.status)}
          </div>
          <div className="service-row">
            <span>{copy.health.analytics}</span>
            {renderStatus(systemStatus.analytics?.status)}
          </div>
          <div className="service-row">
            <span>{copy.health.database}</span>
            {renderStatus(systemStatus.database?.status)}
          </div>
        </div>
      )}
    </section>
  )

  const renderNewAnalysis = () => (
    <>
      <section className="upload-card" aria-labelledby="upload-title">
        <p className="eyebrow">{copy.upload.eyebrow}</p>
        <h2 id="upload-title">{copy.upload.title}</h2>
        <p className="description">
          {copy.upload.description}
        </p>

        <DatasetDropzone
          selectedFile={selectedFile}
          uploading={uploading}
          hasError={Boolean(uploadError || analysisError)}
          copy={copy.upload}
          onFilesSelected={handleFilesSelected}
        />

        {selectedFile && (
          <SelectedFileCard
            file={selectedFile}
            language={language}
            copy={copy.upload}
            uploading={uploading}
            onRemove={handleRemoveFile}
          />
        )}

        {uploading && (
          <AnalysisProgressPanel
            phase={analysisRequestState}
            fileName={selectedFile?.name}
            copy={copy.progress}
          />
        )}

        {uploadError && (
          <p className="message error" id="upload-error" role="alert">
            {uploadError}
          </p>
        )}

        {analysisError && (
          <AnalysisErrorPanel
            message={getAnalysisErrorMessage()}
            canRetryDetail={analysisError.phase === 'detail' && Boolean(analysisError.analysisId)}
            copy={copy.analysisError}
            onRetryDetail={handleRetryDetail}
            onChooseAnother={handleChooseAnotherFile}
          />
        )}

        <button
          type="button"
          className="upload-button"
          onClick={handleUpload}
          disabled={
            !selectedFile
            || uploading
            || analysisError?.phase === 'detail'
          }
        >
          {uploading ? copy.upload.working : copy.upload.startAnalysis}
        </button>

      </section>

      {renderHealthStatus()}
    </>
  )

  const renderSection = () => {
    if (activeSection === 'new-analysis') {
      return renderNewAnalysis()
    }

    if (activeSection === 'overview') {
      if (analysisRequestState === 'restoring') {
        return (
          <section
            className="empty-state analysis-restore-state"
            role="status"
            aria-live="polite"
            aria-labelledby="analysis-restore-title"
          >
            <div
              className="indeterminate-spinner"
              role="img"
              aria-label={copy.restoration.indicatorLabel}
            />
            <div>
              <p className="empty-state-kicker">{copy.restoration.kicker}</p>
              <h2 id="analysis-restore-title">{copy.restoration.title}</h2>
              <p>{copy.restoration.description}</p>
            </div>
          </section>
        )
      }

      if (analysisError?.phase === 'restore') {
        return (
          <section className="empty-state" role="alert" aria-labelledby="restore-error-title">
            <p className="empty-state-kicker">{copy.restoration.errorKicker}</p>
            <h2 id="restore-error-title">{copy.restoration.errorTitle}</h2>
            <p>{getAnalysisErrorMessage()}</p>
            <div className="empty-state-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={handleRetryRestore}
              >
                {copy.restoration.retry}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={handleStartAfterRestoreFailure}
              >
                {copy.empty.startAnalysis}
              </button>
            </div>
          </section>
        )
      }

      if (currentAnalysis) {
        return (
          <div className="analysis-overview">
            <AnalysisHeader
              analysis={currentAnalysis}
              language={language}
              copy={copy.overview.header}
            />
            <SummaryCards
              analysis={currentAnalysis}
              language={language}
              copy={copy.overview.summary}
            />
            <DatasetHealth
              analysis={currentAnalysis}
              language={language}
              copy={copy.overview.health}
            />
            <PipelineSummary
              analysis={currentAnalysis}
              language={language}
              copy={copy.overview.pipeline}
            />
            <KeyFindings
              insights={currentAnalysis.insights}
              language={language}
              copy={copy.overview.findings}
            />
          </div>
        )
      }

      return (
        <section className="empty-state" aria-labelledby="overview-empty-title">
          <p className="empty-state-kicker">{copy.empty.noAnalysis}</p>
          <h2 id="overview-empty-title">{copy.empty.overviewTitle}</h2>
          <p>{copy.empty.overviewDescription}</p>
          {restoreNotice === 'not-found' && (
            <p className="message warning" role="status">
              {copy.restoration.notFoundRemoved}
            </p>
          )}
          <div className="empty-state-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => handleSectionChange('new-analysis')}
            >
              {copy.empty.startAnalysis}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => handleSectionChange('history')}
            >
              {copy.empty.openHistory}
            </button>
          </div>
        </section>
      )
    }

    if (activeSection === 'history') {
      return (
        <AnalysisHistory
          analyses={historyItems}
          currentAnalysisId={currentAnalysis?.id || null}
          language={language}
          loadState={historyLoadState}
          loadError={historyError?.message || null}
          selectingId={historySelectionId}
          selectionError={
            historySelectionError?.isNotFound
              ? copy.history.detailNotFound
              : historySelectionError?.message || (
                historySelectionError ? copy.history.detailError : null
              )
          }
          copy={copy.history}
          onRetry={loadAnalysisHistory}
          onSelect={handleHistorySelection}
        />
      )
    }

    return (
      <section className="empty-state" aria-labelledby="future-section-title">
        <p className="empty-state-kicker">{copy.empty.roadmap}</p>
        <h2 id="future-section-title">{copy.empty.comingSoon}</h2>
        <p>{futureSectionAvailability[activeSection]}</p>
      </section>
    )
  }

  return (
    <AppShell
      activeSection={activeSection}
      onSectionChange={handleSectionChange}
      header={sectionHeaders[activeSection]}
      language={language}
      onLanguageChange={setLanguage}
      copy={copy}
    >
      {renderSection()}
    </AppShell>
  )
}

export default App
