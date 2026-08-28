import { Bar } from 'react-chartjs-2'
import ChartCard from './ChartCard.jsx'
import './chartSetup.js'

function RevenueByRegionChart({ chart, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const points = (Array.isArray(chart?.points) ? chart.points : []).filter(
    (point) => (
      typeof point?.segment === 'string'
      && point.segment.trim().length > 0
      && Number.isFinite(point?.value)
    ),
  )
  const isReady = chart?.status === 'READY' && points.length > 0
  const numberFormatter = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  })

  const data = {
    labels: points.map((point) => point.segment),
    datasets: [
      {
        label: copy.datasetLabel,
        data: points.map((point) => point.value),
        backgroundColor: '#4777ad',
        borderColor: '#315f9d',
        borderWidth: 1,
        borderRadius: 3,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        grid: { display: false },
        ticks: { autoSkip: false, maxRotation: 45, minRotation: 0 },
      },
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value) => numberFormatter.format(value),
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => (
            `${copy.datasetLabel}: ${numberFormatter.format(context.parsed.y)}`
          ),
        },
      },
    },
  }

  const emptyDescription = chart?.unavailableReason
    ? `${copy.emptyDescription} ${chart.unavailableReason}`
    : copy.emptyDescription
  const periodContext = isReady && chart.periodStart && chart.periodEnd
    ? `${copy.period}: ${chart.periodStart} – ${chart.periodEnd}`
    : null

  return (
    <ChartCard
      eyebrow={copy.eyebrow}
      title={copy.title}
      description={copy.description}
      footer={periodContext}
      isEmpty={!isReady}
      emptyTitle={copy.emptyTitle}
      emptyDescription={emptyDescription}
    >
      <p className="chart-text-summary">
        {copy.summary.replace('{count}', numberFormatter.format(points.length))}
      </p>
      <div className="chart-canvas-container">
        <Bar
          data={data}
          options={options}
          role="img"
          aria-label={copy.canvasLabel}
        />
      </div>
    </ChartCard>
  )
}

export default RevenueByRegionChart
