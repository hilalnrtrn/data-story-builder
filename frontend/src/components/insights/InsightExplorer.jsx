import { useMemo, useState } from 'react'
import InsightCard from './InsightCard.jsx'
import InsightDetailDrawer from './InsightDetailDrawer.jsx'
import InsightFilters from './InsightFilters.jsx'

const EMPTY_INSIGHTS = []

const finiteNumberOrNull = (value) => (
  typeof value === 'number' && Number.isFinite(value) ? value : null
)

const compareDescendingNullable = (left, right) => {
  const leftValue = finiteNumberOrNull(left)
  const rightValue = finiteNumberOrNull(right)
  if (leftValue === null && rightValue === null) return 0
  if (leftValue === null) return 1
  if (rightValue === null) return -1
  return rightValue - leftValue
}

const validRank = (value) => Number.isInteger(value) && value > 0 ? value : null

const compareRankNullable = (left, right) => {
  const leftRank = validRank(left)
  const rightRank = validRank(right)
  if (leftRank === null && rightRank === null) return 0
  if (leftRank === null) return 1
  if (rightRank === null) return -1
  return leftRank - rightRank
}

const compareBackendOrder = (left, right) => {
  const rankDifference = compareRankNullable(left.insight.rank, right.insight.rank)
  if (rankDifference) return rankDifference
  const priorityDifference = compareDescendingNullable(
    left.insight.priorityScore,
    right.insight.priorityScore,
  )
  return priorityDifference || left.index - right.index
}

function InsightExplorer({ analysis, language, copy, onStartAnalysis, onOpenHistory }) {
  const [activeType, setActiveType] = useState('ALL')
  const [scanFilter, setScanFilter] = useState('ALL')
  const [sortBy, setSortBy] = useState('backend')
  const [selectedInsightId, setSelectedInsightId] = useState(null)
  const insights = Array.isArray(analysis?.insights) ? analysis.insights : EMPTY_INSIGHTS
  const integrityEvaluations = Array.isArray(analysis?.insightIntegrity)
    ? analysis.insightIntegrity
    : EMPTY_INSIGHTS
  const integrityByInsightId = useMemo(() => new Map(
    integrityEvaluations.map((evaluation) => [evaluation?.insightId, evaluation]),
  ), [integrityEvaluations])
  const featuredInsights = useMemo(() => insights
    .map((insight, index) => ({ insight, index }))
    .filter(({ insight }) => validRank(insight?.rank) !== null)
    .sort(compareBackendOrder)
    .slice(0, 3)
    .map(({ insight }) => insight), [insights])
  const featuredIds = useMemo(() => new Set(
    featuredInsights.map((insight) => insight.id),
  ), [featuredInsights])
  const summary = useMemo(() => ({
    critical: insights.filter((insight) => insight?.priorityLevel === 'CRITICAL').length,
    priorityAttention: insights.filter((insight) => ['CRITICAL', 'HIGH'].includes(insight?.priorityLevel)).length,
    integrityAttention: integrityEvaluations.filter((evaluation) => (
      ['PASS_WITH_WARNINGS', 'REVIEW_REQUIRED', 'FAIL'].includes(evaluation?.status)
    )).length,
    counterEvidence: integrityEvaluations.reduce((count, evaluation) => (
      count + (Array.isArray(evaluation?.counterEvidence) ? evaluation.counterEvidence.length : 0)
    ), 0),
    counterEvidenceInsights: integrityEvaluations.filter((evaluation) => (
      Array.isArray(evaluation?.counterEvidence) && evaluation.counterEvidence.length > 0
    )).length,
  }), [insights, integrityEvaluations])

  const visibleInsights = useMemo(() => insights
    .map((insight, index) => ({ insight, index }))
    .filter(({ insight }) => !featuredIds.has(insight?.id))
    .filter(({ insight }) => activeType === 'ALL' || insight?.type === activeType)
    .filter(({ insight }) => {
      const integrity = integrityByInsightId.get(insight?.id)
      if (scanFilter === 'PRIORITY') return ['CRITICAL', 'HIGH'].includes(insight?.priorityLevel)
      if (scanFilter === 'INTEGRITY') {
        return ['PASS_WITH_WARNINGS', 'REVIEW_REQUIRED', 'FAIL'].includes(integrity?.status)
      }
      if (scanFilter === 'COUNTER') return Array.isArray(integrity?.counterEvidence) && integrity.counterEvidence.length > 0
      return true
    })
    .sort((left, right) => {
      if (sortBy === 'priority') {
        const priorityDifference = compareDescendingNullable(
          left.insight.priorityScore,
          right.insight.priorityScore,
        )
        if (priorityDifference) return priorityDifference
        const rankDifference = compareRankNullable(left.insight.rank, right.insight.rank)
        if (rankDifference) return rankDifference
      }
      if (sortBy === 'importance') {
        const difference = compareDescendingNullable(left.insight.importance, right.insight.importance)
        if (difference) return difference
      }
      if (sortBy === 'confidence') {
        const difference = compareDescendingNullable(left.insight.confidence, right.insight.confidence)
        if (difference) return difference
      }
      return sortBy === 'backend' ? compareBackendOrder(left, right) : left.index - right.index
    })
    .map(({ insight }) => insight), [activeType, featuredIds, integrityByInsightId, insights, scanFilter, sortBy])
  const selectedInsight = selectedInsightId
    ? insights.find((insight) => insight?.id === selectedInsightId) || null
    : null
  const resetFilters = () => {
    setActiveType('ALL')
    setScanFilter('ALL')
    setSortBy('backend')
  }

  if (!analysis) {
    return (
      <section className="empty-state" aria-labelledby="insight-no-analysis-title">
        <p className="empty-state-kicker">{copy.eyebrow}</p>
        <h2 id="insight-no-analysis-title">{copy.noAnalysisTitle}</h2>
        <p>{copy.noAnalysisDescription}</p>
        <div className="empty-state-actions">
          <button type="button" className="secondary-button" onClick={onStartAnalysis}>{copy.startAnalysis}</button>
          <button type="button" className="secondary-button" onClick={onOpenHistory}>{copy.openHistory}</button>
        </div>
      </section>
    )
  }

  if (insights.length === 0) {
    return (
      <section className="empty-state" aria-labelledby="insight-empty-title">
        <p className="empty-state-kicker">{copy.eyebrow}</p>
        <h2 id="insight-empty-title">{copy.emptyTitle}</h2>
        <p>{copy.emptyDescription}</p>
      </section>
    )
  }

  return (
    <section className="insight-explorer" aria-labelledby="insight-explorer-title">
      <header className="insight-explorer-header">
        <div>
          <h2 id="insight-explorer-title" className="visually-hidden">{copy.title}</h2>
          <p>{copy.findingCount.replace('{count}', insights.length)}</p>
        </div>
      </header>

      <dl className="insight-summary-strip" aria-label={copy.summaryLabel}>
        <div><dt>{copy.totalInsights}</dt><dd>{insights.length}</dd></div>
        <div><dt>{copy.criticalInsights}</dt><dd>{summary.critical}</dd></div>
        <div><dt>{copy.integrityAttention}</dt><dd>{summary.integrityAttention}</dd></div>
        <div><dt>{copy.counterEvidenceCount}</dt><dd>{summary.counterEvidence}</dd></div>
      </dl>

      {featuredInsights.length > 0 && (
        <section className="featured-insights" aria-labelledby="featured-insights-title">
          <div className="insight-list-heading">
            <h3 id="featured-insights-title">{copy.topInsights}</h3>
            <span>{featuredInsights.length}</span>
          </div>
          <div className="featured-insight-grid">
            {featuredInsights.map((insight) => (
              <InsightCard
                insight={insight}
                language={language}
                copy={copy}
                featured
                selected={selectedInsightId === insight.id}
                key={insight.id}
                onSelect={setSelectedInsightId}
              />
            ))}
          </div>
        </section>
      )}

      <InsightFilters
        activeType={activeType}
        scanFilter={scanFilter}
        scanCounts={summary}
        sortBy={sortBy}
        copy={copy}
        onTypeChange={setActiveType}
        onScanFilterChange={setScanFilter}
        onSortChange={setSortBy}
        onReset={resetFilters}
      />

      <section className="remaining-insights" aria-labelledby="remaining-insights-title">
        <div className="insight-list-heading">
          <h3 id="remaining-insights-title">{copy.allInsights}</h3>
          <span>{visibleInsights.length}</span>
        </div>
        {visibleInsights.length === 0 ? (
          <div className="overview-inline-empty" role="status">
            <h2>{copy.noMatchesTitle}</h2>
            <p>{copy.noMatchesDescription}</p>
            <button type="button" className="secondary-button" onClick={resetFilters}>
              {copy.resetFilters}
            </button>
          </div>
        ) : (
          <div className="insight-explorer-list">
            {visibleInsights.map((insight) => (
              <InsightCard
                insight={insight}
                language={language}
                copy={copy}
                selected={selectedInsightId === insight.id}
                key={insight.id}
                onSelect={setSelectedInsightId}
              />
            ))}
          </div>
        )}
      </section>

      {selectedInsightId && (
        <InsightDetailDrawer
          insight={selectedInsight}
          insights={insights}
          relationships={Array.isArray(analysis?.relationships) ? analysis.relationships : EMPTY_INSIGHTS}
          integrityEvaluations={Array.isArray(analysis?.insightIntegrity) ? analysis.insightIntegrity : EMPTY_INSIGHTS}
          causalityEvaluations={Array.isArray(analysis?.causalityEvaluations) ? analysis.causalityEvaluations : EMPTY_INSIGHTS}
          missingContextEvaluations={Array.isArray(analysis?.missingContextEvaluations) ? analysis.missingContextEvaluations : EMPTY_INSIGHTS}
          language={language}
          copy={copy.drawer}
          onClose={() => setSelectedInsightId(null)}
        />
      )}
    </section>
  )
}

export default InsightExplorer
