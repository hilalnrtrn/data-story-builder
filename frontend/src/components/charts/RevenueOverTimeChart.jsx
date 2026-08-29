import { Line } from 'react-chartjs-2'
import ChartCard from './ChartCard.jsx'
import './chartSetup.js'

function RevenueOverTimeChart({ chart, language, copy, theme }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const points = (Array.isArray(chart?.points) ? chart.points : []).filter(
    (point) => (
      typeof point?.period === 'string'
      && point.period.trim().length > 0
      && Number.isFinite(point?.value)
    ),
  )
  const isReady = chart?.status === 'READY' && points.length > 0
  const numberFormatter = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  })
  const styles = getComputedStyle(document.documentElement)
  const brandColor = styles.getPropertyValue('--color-brand-primary').trim()
  const brandGlow = styles.getPropertyValue('--color-brand-glow').trim()
  const gridColor = styles.getPropertyValue('--color-border').trim()
  const textColor = styles.getPropertyValue('--color-text-muted').trim()
  const tooltipBackground = styles.getPropertyValue('--color-surface-raised').trim()
  const tooltipText = styles.getPropertyValue('--color-text-primary').trim()

  const data = {
    labels: points.map((point) => point.period),
    datasets: [
      {
        label: copy.datasetLabel,
        data: points.map((point) => point.value),
        borderColor: brandColor,
        backgroundColor: brandGlow,
        fill: true,
        borderWidth: 2.25,
        pointRadius: 2.25,
        pointHoverRadius: 5,
        tension: 0.3,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: {
      intersect: false,
      mode: 'index',
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: { color: textColor, maxRotation: 0, autoSkip: true, font: { size: 12 } },
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
  const periodContext = isReady
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
      <p className="chart-text-summary">
        {copy.summary
          .replace('{count}', numberFormatter.format(points.length))
          .replace('{start}', chart?.periodStart || copy.notAvailable)
          .replace('{end}', chart?.periodEnd || copy.notAvailable)}
      </p>
      <div className="chart-canvas-container">
        <Line
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

export default RevenueOverTimeChart
