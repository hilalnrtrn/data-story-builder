import { useEffect, useRef, useState } from 'react'
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
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false)
  const navigationRef = useRef(null)
  const menuButtonRef = useRef(null)

  useEffect(() => {
    if (!mobileNavigationOpen) return undefined

    const previousOverflow = document.body.style.overflow
    const menuButton = menuButtonRef.current
    document.body.style.overflow = 'hidden'
    navigationRef.current?.querySelector('.sidebar-mobile-close')?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setMobileNavigationOpen(false)
        return
      }

      if (event.key !== 'Tab' || !navigationRef.current) return
      const focusable = [...navigationRef.current.querySelectorAll(
        'button:not(:disabled), [href], [tabindex]:not([tabindex="-1"])',
      )]
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      menuButton?.focus()
    }
  }, [mobileNavigationOpen])

  const closeMobileNavigation = () => setMobileNavigationOpen(false)
  const handleSectionChange = (section) => {
    onSectionChange(section)
    closeMobileNavigation()
  }
  const handleNewAnalysis = () => {
    onNewAnalysis()
    closeMobileNavigation()
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">{copy.shell.skipToContent}</a>
      <div
        className={`mobile-navigation-backdrop${mobileNavigationOpen ? ' is-open' : ''}`}
        aria-hidden="true"
        onMouseDown={closeMobileNavigation}
      />
      <Sidebar
        navigationRef={navigationRef}
        mobileOpen={mobileNavigationOpen}
        activeSection={activeSection}
        onSectionChange={handleSectionChange}
        onNewAnalysis={handleNewAnalysis}
        onDismiss={closeMobileNavigation}
        copy={copy}
      />

      <main className="workspace" id="main-content">
        <WorkspaceHeader
          {...header}
          sectionId={activeSection}
          language={language}
          onLanguageChange={onLanguageChange}
          theme={theme}
          onThemeChange={onThemeChange}
          onNewAnalysis={onNewAnalysis}
          analysis={analysis}
          analysisCopy={copy.overview.header}
          languageCopy={copy.shell}
          menuButtonRef={menuButtonRef}
          mobileNavigationOpen={mobileNavigationOpen}
          onMobileNavigationToggle={() => setMobileNavigationOpen((open) => !open)}
        />
        <div className="workspace-content">{children}</div>
      </main>
    </div>
  )
}

export default AppShell
