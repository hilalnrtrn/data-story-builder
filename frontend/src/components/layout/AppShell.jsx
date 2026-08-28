import Sidebar from './Sidebar.jsx'
import WorkspaceHeader from './WorkspaceHeader.jsx'

function AppShell({
  activeSection,
  onSectionChange,
  header,
  language,
  onLanguageChange,
  theme,
  onThemeChange,
  onNewAnalysis,
  analysis,
  copy,
  children,
}) {
  return (
    <div className="app-shell">
      <Sidebar
        activeSection={activeSection}
        onSectionChange={onSectionChange}
        copy={copy}
      />

      <main className="workspace" id="main-content">
        <WorkspaceHeader
          {...header}
          language={language}
          onLanguageChange={onLanguageChange}
          theme={theme}
          onThemeChange={onThemeChange}
          onNewAnalysis={onNewAnalysis}
          analysis={analysis}
          analysisCopy={copy.overview.header}
          languageCopy={copy.shell}
        />
        <div className="workspace-content">{children}</div>
      </main>
    </div>
  )
}

export default AppShell
