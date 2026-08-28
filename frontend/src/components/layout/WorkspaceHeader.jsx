function WorkspaceHeader({
  title,
  description,
  language,
  onLanguageChange,
  theme,
  onThemeChange,
  onNewAnalysis,
  analysis,
  analysisCopy,
  languageCopy,
}) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const completedDate = analysis?.completedAt ? new Date(analysis.completedAt) : null
  const completedAt = completedDate && !Number.isNaN(completedDate.getTime())
    ? new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(completedDate)
    : null
  const status = analysisCopy?.statuses?.[analysis?.status] || analysis?.status
  const statusTone = analysis?.status === 'Completed'
    ? 'header-status-success'
    : analysis?.status === 'Failed'
      ? 'header-status-danger'
      : 'header-status-warning'

  return (
    <header className="workspace-header">
      <div className="workspace-heading-copy">
        <h1>{title}</h1>
        {analysis ? (
          <div className="workspace-analysis-context">
            <strong>{analysis.fileName || analysisCopy.notAvailable}</strong>
            {status && <span className={`header-status-dot ${statusTone}`}>{status}</span>}
            {completedAt && <time dateTime={analysis.completedAt}>{completedAt}</time>}
          </div>
        ) : <p className="workspace-description">{description}</p>}
      </div>

      <div className="workspace-controls">
        <button
          type="button"
          className="theme-toggle"
          aria-label={theme === 'dark' ? languageCopy.useLightTheme : languageCopy.useDarkTheme}
          aria-pressed={theme === 'dark'}
          onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
        >
          <span className="theme-toggle-track" aria-hidden="true">
            <span className={`theme-toggle-option${theme === 'light' ? ' is-active' : ''}`}>
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            </span>
            <span className={`theme-toggle-option${theme === 'dark' ? ' is-active' : ''}`}>
              <svg viewBox="0 0 24 24">
                <path d="M20.5 14.4A8 8 0 019.6 3.5 8.5 8.5 0 1020.5 14.4z" />
              </svg>
            </span>
          </span>
        </button>

        <div className="language-switcher" role="group" aria-label={languageCopy.language}>
          <button type="button" aria-label={languageCopy.turkish} aria-pressed={language === 'tr'} onClick={() => onLanguageChange('tr')}>TR</button>
          <button type="button" aria-label={languageCopy.english} aria-pressed={language === 'en'} onClick={() => onLanguageChange('en')}>EN</button>
        </div>

        <button type="button" className="header-new-analysis" onClick={onNewAnalysis}>
          <span aria-hidden="true">+</span>
          {languageCopy.newAnalysis}
        </button>
      </div>
    </header>
  )
}

export default WorkspaceHeader
