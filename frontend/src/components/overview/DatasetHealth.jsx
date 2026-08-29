import RevenueOverTimeChart from '../charts/RevenueOverTimeChart.jsx'
import RevenueByRegionChart from '../charts/RevenueByRegionChart.jsx'
import KeyMetricChangesChart from '../charts/KeyMetricChangesChart.jsx'
import KeyFindings from './KeyFindings.jsx'
import AnalysisHeader from './AnalysisHeader.jsx'

function DatasetHealth({ analysis, language, copy, findingsCopy, analysisHeaderCopy, theme }) {
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
  const qualityScore = typeof quality?.score === 'number' && Number.isFinite(quality.score)
    ? quality.score
    : null
  const integrityStatusLabel = enumLabel(copy.integrityStatuses, integrity?.status)

  return (
    <>
      <div className="overview-primary-evidence-grid">
        <div className="overview-primary-chart">
          <RevenueOverTimeChart
            chart={analysis.profile?.overviewCharts?.revenueOverTime}
            language={language}
            copy={copy.revenueOverTime}
            theme={theme}
          />
        </div>

        <KeyFindings
          insights={analysis.insights}
          language={language}
          copy={findingsCopy}
          compact
        />

      </div>

      <section className="overview-section overview-data-health" aria-labelledby="dataset-health-title">
      <div className="overview-section-heading">
        <h2 id="dataset-health-title">{copy.title}</h2>
      </div>

      <div className="data-health-overview">
        <div className="data-health-score">
          <span>{copy.overallQuality}</span>
          <strong>{formatScore(qualityScore)}</strong>
          <span className={`status ${integrityStatusClass}`}>
            <span aria-hidden="true">{integrity?.status === 'PASS' ? '✓' : integrity?.status ? '!' : '○'}</span>
            {integrityStatusLabel}
          </span>
          <small>{copy.basis}: {enumLabel(copy.basisLabels, quality?.basis)}</small>
        </div>
        <dl className="data-health-dimensions">
          {qualityDimensions.map(([label, value]) => (
            <div key={label}>
              <div><dt>{label}</dt><dd>{formatScore(value)}</dd></div>
              <progress max="100" value={Number.isFinite(value) ? value : 0} aria-label={`${label}: ${formatScore(value)}`} />
            </div>
          ))}
        </dl>
      </div>

      <div className="dataset-health-sections">
        <details className="dataset-health-subsection preparation-disclosure">
          <summary>
            <span><strong>{copy.preparation}</strong><small>{copy.preparationDescription}</small></span>
            <span aria-hidden="true">+</span>
          </summary>
          <div className="preparation-content">
            <dl className="health-value-grid preparation-grid">
              {preparationItems.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{formatNumber(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        </details>

        <article className="dataset-health-subsection integrity-subsection">
          <div className="health-subsection-heading">
            <h3>{copy.datasetIntegrity}</h3>
          </div>

          <div className="integrity-summary-layout">
            <div className="integrity-status-block">
              <span>{copy.status}</span>
              <strong className={`status ${integrityStatusClass}`}>
                {integrityStatusLabel}
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
        <RevenueByRegionChart
          chart={analysis.profile?.overviewCharts?.revenueByRegion}
          language={language}
          copy={copy.revenueByRegion}
          theme={theme}
        />
        <div className="overview-chart-wide">
          <KeyMetricChangesChart
            insights={analysis.insights}
            language={language}
            copy={copy.keyMetricChanges}
            theme={theme}
          />
        </div>
      </div>

      <AnalysisHeader
        analysis={analysis}
        language={language}
        copy={analysisHeaderCopy}
      />
    </>
  )
}

export default DatasetHealth
