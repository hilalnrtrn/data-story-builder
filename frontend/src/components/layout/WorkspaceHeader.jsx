function WorkspaceHeader({ eyebrow, title, description, language, onLanguageChange, languageCopy }) {
  return (
    <header className="workspace-header">
      <div className="workspace-heading-copy">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="workspace-description">{description}</p>
      </div>

      <div className="language-switcher" role="group" aria-label={languageCopy.language}>
        <button
          type="button"
          aria-label={languageCopy.turkish}
          aria-pressed={language === 'tr'}
          onClick={() => onLanguageChange('tr')}
        >
          TR
        </button>
        <button
          type="button"
          aria-label={languageCopy.english}
          aria-pressed={language === 'en'}
          onClick={() => onLanguageChange('en')}
        >
          EN
        </button>
      </div>
    </header>
  )
}

export default WorkspaceHeader
