import { useId } from 'react'
import ChartEmptyState from './ChartEmptyState.jsx'
import StatePanel from '../feedback/StatePanel.jsx'

function ChartCard({
  eyebrow,
  title,
  description,
  footer,
  children,
  isEmpty = false,
  emptyTitle,
  emptyDescription,
  isLoading = false,
  loadingLabel,
}) {
  const headingId = useId()
  const descriptionId = useId()

  return (
    <section
      className="chart-card"
      aria-labelledby={headingId}
      aria-describedby={description ? descriptionId : undefined}
    >
      <header className="chart-card-header">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 id={headingId}>{title}</h2>
        {description && <p id={descriptionId}>{description}</p>}
      </header>

      <div className="chart-card-content">
        {isLoading ? (
          <StatePanel variant="loading" size="inline" className="chart-loading-state" title={loadingLabel} role="status" ariaLive="polite" />
        ) : isEmpty ? (
          <ChartEmptyState title={emptyTitle} description={emptyDescription} />
        ) : (
          children
        )}
      </div>

      {footer && <footer className="chart-card-footer">{footer}</footer>}
    </section>
  )
}

export default ChartCard
