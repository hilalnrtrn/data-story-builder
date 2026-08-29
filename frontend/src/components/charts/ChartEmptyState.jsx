import StatePanel from '../feedback/StatePanel.jsx'

function ChartEmptyState({ title, description }) {
  return (
    <StatePanel
      variant="empty"
      size="inline"
      className="chart-empty-state"
      title={title}
      description={description}
    />
  )
}

export default ChartEmptyState
