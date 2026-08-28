import Sidebar from './Sidebar.jsx'
import WorkspaceHeader from './WorkspaceHeader.jsx'

function AppShell({ activeSection, onSectionChange, header, language, onLanguageChange, copy, children }) {
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
          languageCopy={copy.shell}
        />
        <div className="workspace-content">{children}</div>
      </main>
    </div>
  )
}

export default AppShell
