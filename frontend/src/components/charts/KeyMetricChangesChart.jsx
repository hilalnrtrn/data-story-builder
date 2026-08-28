import { Bar } from 'react-chartjs-2'
import ChartCard from './ChartCard.jsx'
import './chartSetup.js'

const DISPLAY_LIMIT = 5

const persistedChange = (insight) => {
  if (Number.isFinite(insight?.values?.relativeChange)) {
    return insight.values.relativeChange
  }
  if (Number.isFinite(insight?.values?.percentageChange)) {
    return insight.values.percentageChange
  }
  return null
}

const persistedValue = (values, preferredKey, existingKey) => {
  if (Number.isFinite(values?.[preferredKey])) return values[preferredKey]
  if (Number.isFinite(values?.[existingKey])) return values[existingKey]
  return null
}

function KeyMetricChangesChart({ insights, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const numberFormatter = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  })
  const percentFormatter = (value) => `${numberFormatter.format(value)}%`
  const usableChanges = (Array.isArray(insights) ? insights : [])
    .filter((insight) => insight?.type === 'CHANGE')
    .filter((insight) => persistedChange(insight) !== null)
  const rankedChanges = usableChanges.filter(
    (insight) => insight?.rank !== null && insight?.rank !== undefined,
  )
  const unrankedChanges = usableChanges.filter(
    (insight) => insight?.rank === null || insight?.rank === undefined,
  )
  const displayedChanges = [...rankedChanges, ...unrankedChanges]
    .slice(0, DISPLAY_LIMIT)
  const isReady = displayedChanges.length > 0

  const labelFor = (insight) => {
    const period = insight?.period?.current
    return period ? `${insight.metric || copy.notAvailable} · ${period}` : insight.metric || copy.notAvailable
  }
  const directionColor = (direction) => {
    if (direction === 'UP') return '#315f9d'
    if (direction === 'DOWN') return '#a5652a'
    return '#687386'
  }
  const formatOptionalNumber = (value) => (
    Number.isFinite(value) ? numberFormatter.format(value) : copy.notAvailable
  )

  const data = {
    labels: displayedChanges.map(labelFor),
    datasets: [
      {
        label: copy.datasetLabel,
        data: displayedChanges.map(persistedChange),
        backgroundColor: displayedChanges.map((insight) => directionColor(insight.direction)),
        borderWidth: 0,
        borderRadius: 3,
      },
    ],
  }

  const options = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        ticks: { callback: (value) => percentFormatter(value) },
      },
      y: {
        grid: { display: false },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `${copy.relativeChange}: ${percentFormatter(context.parsed.x)}`,
          afterLabel: (context) => {
            const insight = displayedChanges[context.dataIndex]
            const values = insight?.values
            const previousValue = persistedValue(values, 'previousValue', 'previous')
            const currentValue = persistedValue(values, 'currentValue', 'current')
            return [
              `${copy.period}: ${insight?.period?.previous || copy.notAvailable} → ${insight?.period?.current || copy.notAvailable}`,
              `${copy.previousValue}: ${formatOptionalNumber(previousValue)}`,
              `${copy.currentValue}: ${formatOptionalNumber(currentValue)}`,
              `${copy.priority}: ${copy.priorities[insight?.priorityLevel] || insight?.priorityLevel || copy.notAvailable}`,
              `${copy.direction}: ${copy.directions[insight?.direction] || insight?.direction || copy.notAvailable}`,
            ]
          },
        },
      },
    },
  }

  return (
    <ChartCard
      eyebrow={copy.eyebrow}
      title={copy.title}
      description={copy.description}
      footer={isReady ? copy.footer.replace('{count}', numberFormatter.format(displayedChanges.length)) : null}
      isEmpty={!isReady}
      emptyTitle={copy.emptyTitle}
      emptyDescription={copy.emptyDescription}
    >
      <p className="chart-text-summary">
        {copy.summary.replace('{count}', numberFormatter.format(displayedChanges.length))}
      </p>
      <div className="chart-canvas-container key-metric-chart-canvas">
        <Bar data={data} options={options} role="img" aria-label={copy.canvasLabel} />
      </div>
    </ChartCard>
  )
}

export default KeyMetricChangesChart
