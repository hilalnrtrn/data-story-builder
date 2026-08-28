const navigationItems = [
  { id: 'overview', labelKey: 'overview' },
  { id: 'insights', labelKey: 'insights' },
  { id: 'executive-story', labelKey: 'executiveStory' },
  { id: 'story-audit', labelKey: 'storyAudit' },
  { id: 'hypotheses', labelKey: 'hypotheses' },
  { id: 'history', labelKey: 'history' },
]

function Sidebar({ activeSection, onSectionChange, copy }) {
  return (
    <aside className="sidebar" aria-label={copy.shell.applicationNavigation}>
      <div className="brand-block">
        <span className="brand-mark" aria-hidden="true">DS</span>
        <div>
          <p className="brand-name">Data Story Builder</p>
          <p className="brand-description">{copy.shell.productDescriptor}</p>
        </div>
      </div>

      <button
        type="button"
        className="new-analysis-button"
        aria-current={activeSection === 'new-analysis' ? 'page' : undefined}
        onClick={() => onSectionChange('new-analysis')}
      >
        <span aria-hidden="true">+</span>
        {copy.navigation.newAnalysis}
      </button>

      <nav className="primary-navigation" aria-label={copy.shell.workspaceNavigation}>
        <p className="navigation-label">{copy.shell.workspace}</p>

        {navigationItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className="navigation-item"
            aria-current={activeSection === item.id ? 'page' : undefined}
            onClick={() => onSectionChange(item.id)}
          >
            <span className="navigation-indicator" aria-hidden="true" />
            {copy.navigation[item.labelKey]}
          </button>
        ))}
      </nav>

      <p className="sidebar-note">{copy.shell.sidebarNote}</p>
    </aside>
  )
}

export default Sidebar
