import { Bar } from 'react-chartjs-2'
import ChartCard from './ChartCard.jsx'
import './chartSetup.js'

function RevenueByRegionChart({ chart, language, copy, theme }) {
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
  const styles = getComputedStyle(document.documentElement)
  const brandColor = styles.getPropertyValue('--color-brand-secondary').trim()
  const borderColor = styles.getPropertyValue('--color-brand-primary').trim()
  const gridColor = styles.getPropertyValue('--color-border').trim()
  const textColor = styles.getPropertyValue('--color-text-muted').trim()
  const tooltipBackground = styles.getPropertyValue('--color-surface-raised').trim()
  const tooltipText = styles.getPropertyValue('--color-text-primary').trim()

  const data = {
    labels: points.map((point) => point.segment),
    datasets: [
      {
        label: copy.datasetLabel,
        data: points.map((point) => point.value),
        backgroundColor: brandColor,
        borderColor,
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
        border: { display: false },
        ticks: { color: textColor, autoSkip: false, maxRotation: 45, minRotation: 0, font: { size: 12 } },
      },
      y: {
        beginAtZero: true,
        border: { display: false },
        grid: { color: gridColor },
        ticks: {
          color: textColor,
          font: { size: 12 },
          callback: (value) => numberFormatter.format(value),
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: tooltipBackground,
        titleColor: tooltipText,
        bodyColor: tooltipText,
        borderColor: gridColor,
        borderWidth: 1,
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
      title={copy.title}
      footer={periodContext}
      isEmpty={!isReady}
      emptyTitle={copy.emptyTitle}
      emptyDescription={emptyDescription}
    >
      <p className="chart-text-summary visually-hidden-chart-summary">
        {copy.summary.replace('{count}', numberFormatter.format(points.length))}
      </p>
      <div className="chart-canvas-container">
        <Bar
          key={theme}
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
