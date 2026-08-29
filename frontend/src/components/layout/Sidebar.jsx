import { useEffect, useState } from 'react'

const navigationItems = [
  { id: 'overview', labelKey: 'overview', icon: 'overview' },
  { id: 'insights', labelKey: 'insights', icon: 'insights' },
  { id: 'executive-story', labelKey: 'executiveStory', icon: 'story' },
  { id: 'story-audit', labelKey: 'storyAudit', icon: 'audit' },
  { id: 'hypotheses', labelKey: 'hypotheses', icon: 'hypotheses' },
  { id: 'history', labelKey: 'history', icon: 'history' },
]

const NavIcon = ({ name }) => {
  const paths = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
    insights: <><path d="M9 18h6" /><path d="M10 21h4" /><path d="M8.4 14.5a6 6 0 1 1 7.2 0c-1 .75-1.6 1.75-1.6 2.5h-4c0-.75-.6-1.75-1.6-2.5Z" /></>,
    story: <><path d="M5 4.5h10a3 3 0 0 1 3 3v12H8a3 3 0 0 1-3-3Z" /><path d="M8 8h7M8 12h7" /><path d="M8 19.5a3 3 0 0 1 0-6h10" /></>,
    audit: <><path d="M12 3.25 19 6.5v5.25c0 4.25-2.75 7.25-7 9-4.25-1.75-7-4.75-7-9V6.5Z" /><path d="m8.5 12 2.25 2.25 4.75-5" /></>,
    hypotheses: <><path d="M9 3.5h6" /><path d="M10 3.5v5.25l-5 8.75a2 2 0 0 0 1.75 3h10.5a2 2 0 0 0 1.75-3l-5-8.75V3.5" /><path d="M7.5 16h9" /></>,
    history: <><path d="M3.5 12a8.5 8.5 0 1 0 2.15-5.65" /><path d="M3.5 4.5v4h4" /><path d="M12 7.5V12l3 2" /></>,
  }

  return (
    <svg
      className="navigation-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  )
}

function Sidebar({
  activeSection,
  onSectionChange,
  onNewAnalysis,
  onDismiss,
  mobileOpen,
  navigationRef,
  copy,
}) {
  const [mobileViewport, setMobileViewport] = useState(false)

  useEffect(() => {
    const query = window.matchMedia('(max-width: 900px)')
    const updateViewport = () => setMobileViewport(query.matches)
    updateViewport()
    query.addEventListener('change', updateViewport)
    return () => query.removeEventListener('change', updateViewport)
  }, [])

  const primaryItems = navigationItems.filter((item) => item.id !== 'history')
  const utilityItems = navigationItems.filter((item) => item.id === 'history')
  const renderNavigationItem = (item) => (
    <button
      key={item.id}
      type="button"
      className="navigation-item"
      aria-current={activeSection === item.id ? 'page' : undefined}
      title={copy.navigation[item.labelKey]}
      onClick={() => onSectionChange(item.id)}
    >
      <NavIcon name={item.icon} />
      <span>{copy.navigation[item.labelKey]}</span>
    </button>
  )

  return (
    <aside
      ref={navigationRef}
      id="application-sidebar"
      className={`sidebar${mobileOpen ? ' is-mobile-open' : ''}`}
      aria-label={copy.shell.applicationNavigation}
      aria-hidden={mobileViewport && !mobileOpen ? 'true' : undefined}
      inert={mobileViewport && !mobileOpen ? true : undefined}
    >
      <div className="brand-block" aria-label="Data Story Builder">
        <span className="brand-mark" aria-hidden="true">
          <span className="brand-symbol">
            <img src="/data-story-builder-mark.png" alt="" />
          </span>
          <span className="brand-lockup">
            <strong className="brand-name">Data Story</strong>
            <span className="brand-builder">Builder</span>
          </span>
        </span>
        <button
          type="button"
          className="sidebar-mobile-close"
          aria-label={copy.shell.closeNavigation}
          onClick={onDismiss}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>

      <button
        type="button"
        className="sidebar-new-analysis"
        aria-current={activeSection === 'new-analysis' ? 'page' : undefined}
        aria-label={copy.shell.newAnalysis}
        title={copy.shell.newAnalysis}
        onClick={onNewAnalysis}
      >
        <span aria-hidden="true">+</span>
        <span>{copy.shell.newAnalysis}</span>
      </button>

      <nav className="primary-navigation" aria-label={copy.shell.workspaceNavigation}>
        <p className="navigation-label">{copy.shell.workspace}</p>
        {primaryItems.map(renderNavigationItem)}

        <div className="navigation-utility-group">
          {utilityItems.map(renderNavigationItem)}
        </div>
      </nav>

      <div className="sidebar-note">
        <span className="workspace-utility-icon" aria-hidden="true">DS</span>
        <span>
          <strong>{copy.shell.workspaceUtility}</strong>
          <small>{copy.shell.productDescriptor}</small>
        </span>
      </div>
    </aside>
  )
}

export default Sidebar
