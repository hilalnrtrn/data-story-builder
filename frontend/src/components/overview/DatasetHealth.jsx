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
  const qualityProgress = qualityScore !== null && qualityScore >= 0 && qualityScore <= 100
    ? qualityScore
    : 0
  const qualityTone = integrity?.status === 'PASS'
    ? 'quality-donut-success'
    : integrity?.status === 'WARNING'
      ? 'quality-donut-warning'
      : integrity?.status === 'FAILED' || integrity?.status === 'FAIL'
        ? 'quality-donut-danger'
        : 'quality-donut-neutral'

  return (
    <>
      <div className="overview-hero-grid">
        <div className="overview-hero-revenue">
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

        <article className="quality-hero-card" aria-labelledby="quality-hero-title">
          <div className="quality-hero-heading">
            <p className="eyebrow">{copy.eyebrow}</p>
            <h2 id="quality-hero-title">{copy.overallQuality}</h2>
          </div>
          <div
            className={`quality-donut ${qualityTone}`}
            style={{ '--quality-progress': `${qualityProgress * 3.6}deg` }}
            role="img"
            aria-label={`${copy.qualityScore}: ${formatScore(qualityScore)}`}
          >
            <span>
              <strong>{formatScore(qualityScore)}</strong>
              <small>{copy.qualityScore}</small>
            </span>
          </div>
          <p>{copy.qualityDescription}</p>
          <small className="quality-basis">
            {copy.basis}: {enumLabel(copy.basisLabels, quality?.basis)}
          </small>
          <dl className="quality-hero-dimensions">
            {qualityDimensions.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{formatScore(value)}</dd>
              </div>
            ))}
          </dl>
        </article>
      </div>

      <AnalysisHeader
        analysis={analysis}
        language={language}
        copy={analysisHeaderCopy}
      />

      <section className="overview-section" aria-labelledby="dataset-health-title">
      <div className="overview-section-heading">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2 id="dataset-health-title">{copy.title}</h2>
        <p>{copy.description}</p>
      </div>

      <div className="dataset-health-sections">
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
    </>
  )
}

export default DatasetHealth
