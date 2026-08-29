import { useState } from 'react'
import HypothesisCard from './HypothesisCard.jsx'
import HypothesisDetail from './HypothesisDetail.jsx'
import '../../Hypotheses.css'

function HypothesisExplorer({ analysis, language, copy, onStatusUpdate, onStartAnalysis, onOpenHistory }) {
  const [selectedId, setSelectedId] = useState(() => analysis?.hypotheses?.[0]?.id || null)
  const hypotheses = Array.isArray(analysis?.hypotheses) ? analysis.hypotheses : []
  const selected = selectedId ? hypotheses.find((item) => item?.id === selectedId) || null : null
  const statusCounts = ['OPEN', 'SUPPORTED', 'CONFIRMED', 'REJECTED'].map((status) => ({
    status,
    count: hypotheses.filter((item) => item?.status === status).length,
  }))

  if (!analysis) {
    return <section className="empty-state" aria-labelledby="hypothesis-no-analysis-title"><p className="empty-state-kicker">{copy.eyebrow}</p><h2 id="hypothesis-no-analysis-title">{copy.noAnalysisTitle}</h2><p>{copy.noAnalysisDescription}</p><div className="empty-state-actions"><button type="button" className="secondary-button" onClick={onStartAnalysis}>{copy.startAnalysis}</button><button type="button" className="secondary-button" onClick={onOpenHistory}>{copy.openHistory}</button></div></section>
  }

  if (hypotheses.length === 0) {
    return <section className="empty-state" role="status" aria-labelledby="hypothesis-empty-title"><p className="empty-state-kicker">{copy.eyebrow}</p><h2 id="hypothesis-empty-title">{copy.emptyTitle}</h2><p>{copy.emptyDescription}</p></section>
  }

  return (
    <section className="hypothesis-explorer" aria-labelledby="hypothesis-explorer-title">
      <header className="hypothesis-explorer-header"><div><p className="eyebrow">{copy.eyebrow}</p><h2 id="hypothesis-explorer-title">{copy.investigationTitle}</h2><p>{copy.description}</p></div></header>
      <aside className="hypothesis-epistemic-guide" aria-label={copy.epistemicGuideLabel}>
        <div><strong>{copy.guide.fact.title}</strong><span>{copy.guide.fact.description}</span></div>
        <div><strong>{copy.guide.insight.title}</strong><span>{copy.guide.insight.description}</span></div>
        <div className="is-hypothesis"><strong>{copy.guide.hypothesis.title}</strong><span>{copy.guide.hypothesis.description}</span></div>
        <p>{copy.epistemicDescription}</p>
      </aside>
      <dl className="hypothesis-summary" aria-label={copy.summaryLabel}>
        <div><dt>{copy.total}</dt><dd>{hypotheses.length}</dd></div>
        {statusCounts.map(({ status, count }) => <div key={status}><dt>{copy.statuses[status]}</dt><dd>{count}</dd></div>)}
      </dl>
      <div className={`hypothesis-workspace${selected ? ' has-detail' : ''}${hypotheses.length === 1 ? ' is-single' : ''}`}>
        <div className="hypothesis-list">{hypotheses.map((hypothesis) => <HypothesisCard key={hypothesis.id} hypothesis={hypothesis} language={language} copy={copy} selected={selectedId === hypothesis.id} onSelect={setSelectedId} />)}</div>
        {selected && <HypothesisDetail key={selected.id} hypothesis={selected} insights={analysis.insights} relationships={analysis.relationships} language={language} copy={copy} onStatusUpdate={onStatusUpdate} onClose={() => setSelectedId(null)} />}
      </div>
    </section>
  )
}

export default HypothesisExplorer
