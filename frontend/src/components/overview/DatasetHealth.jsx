import RevenueOverTimeChart from '../charts/RevenueOverTimeChart.jsx'
import RevenueByRegionChart from '../charts/RevenueByRegionChart.jsx'
import KeyMetricChangesChart from '../charts/KeyMetricChangesChart.jsx'

function DatasetHealth({ analysis, language, copy }) {
  const locale = language === 'tr' ? 'tr-TR' : 'en-US'
  const preparation = analysis.profile?.preparationReport
  const integrity = analysis.profile?.integrity
  const quality = analysis.quality

  const formatNumber = (value) =>
    typeof value === 'number'
      ? new Intl.NumberFormat(locale).format(value)
      : copy.notAvailable
  const formatScore = (value) =>
    typeof value === 'number'
      ? `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value)}%`
      : copy.notAvailable
  const enumLabel = (labels, value) => labels[value] || value || copy.notAvailable
  const integrityStatusClass = integrity?.status === 'PASS'
    ? 'healthy'
    : integrity?.status === 'WARNING'
      ? 'warning'
      : integrity?.status === 'FAILED' || integrity?.status === 'FAIL'
        ? 'unhealthy'
        : 'neutral-status'

  const qualityDimensions = [
    [copy.completeness, quality?.completeness],
    [copy.validity, quality?.validity],
    [copy.consistency, quality?.consistency],
    [copy.uniqueness, quality?.uniqueness],
  ]
  const preparationItems = [
    [copy.rowsRead, preparation?.rowsRead],
    [copy.rowsPrepared, preparation?.rowsPrepared],
    [copy.missingValues, preparation?.missingValuesDetected],
    [copy.duplicatesRemoved, preparation?.duplicatesRemoved],
    [copy.categoriesNormalized, preparation?.categoricalValuesNormalized],
    [copy.whitespaceFixes, preparation?.whitespaceFixes],
    [copy.numericConversions, preparation?.numericConversions],
    [copy.dateErrors, preparation?.dateConversionErrors],
  ]

  return (
    <>
      <section className="overview-section" aria-labelledby="dataset-health-title">
      <div className="overview-section-heading">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2 id="dataset-health-title">{copy.title}</h2>
        <p>{copy.description}</p>
      </div>

      <div className="dataset-health-sections">
        <article className="dataset-health-subsection quality-subsection">
          <div className="health-subsection-heading">
            <h3>{copy.overallQuality}</h3>
            <p>{copy.qualityDescription}</p>
          </div>

          <div className="quality-overview-layout">
            <div className="quality-score-card">
              <span>{copy.qualityScore}</span>
              <strong>{formatScore(quality?.score)}</strong>
              <small>
                {copy.basis}: {enumLabel(copy.basisLabels, quality?.basis)}
              </small>
            </div>

            <div className="quality-dimensions">
              <p className="health-group-label">{copy.qualityDimensions}</p>
              <dl className="health-value-grid quality-dimension-grid">
                {qualityDimensions.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{formatScore(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </article>

        <article className="dataset-health-subsection">
          <div className="health-subsection-heading">
            <h3>{copy.preparation}</h3>
            <p>{copy.preparationDescription}</p>
          </div>
          <dl className="health-value-grid preparation-grid">
            {preparationItems.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{formatNumber(value)}</dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="dataset-health-subsection integrity-subsection">
          <div className="health-subsection-heading">
            <h3>{copy.datasetIntegrity}</h3>
            <p>{copy.integrityDescription}</p>
          </div>

          <div className="integrity-summary-layout">
            <div className="integrity-status-block">
              <span>{copy.status}</span>
              <strong className={`status ${integrityStatusClass}`}>
                {enumLabel(copy.integrityStatuses, integrity?.status)}
              </strong>
            </div>
            <dl className="health-value-grid integrity-count-grid">
              <div>
                <dt>{copy.findings}</dt>
                <dd>{formatNumber(integrity?.findingCount)}</dd>
              </div>
              <div>
                <dt>{copy.affectedRows}</dt>
                <dd>{formatNumber(integrity?.affectedRowCount)}</dd>
              </div>
            </dl>
          </div>
        </article>
      </div>
      </section>

      <div className="overview-chart-grid">
        <RevenueOverTimeChart
          chart={analysis.profile?.overviewCharts?.revenueOverTime}
          language={language}
          copy={copy.revenueOverTime}
        />
        <RevenueByRegionChart
          chart={analysis.profile?.overviewCharts?.revenueByRegion}
          language={language}
          copy={copy.revenueByRegion}
        />
        <div className="overview-chart-wide">
          <KeyMetricChangesChart
            insights={analysis.insights}
            language={language}
            copy={copy.keyMetricChanges}
          />
        </div>
      </div>
    </>
  )
}

export default DatasetHealth
