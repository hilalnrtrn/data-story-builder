function ChartEmptyState({ title, description }) {
  return (
    <div className="chart-empty-state" role="status">
      <span className="chart-empty-mark" aria-hidden="true" />
      <div>
        <h3>{title}</h3>
        {description && <p>{description}</p>}
      </div>
    </div>
  )
}

export default ChartEmptyState
