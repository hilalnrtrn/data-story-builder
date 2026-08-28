import ClaimEvidence from './ClaimEvidence.jsx'

const humanize = (value) => (
  typeof value === 'string' && value.trim()
    ? value.trim().toLowerCase().replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
    : null
)

function StorySection({ section, planById, auditById, insightById, copy }) {
  const sectionLabel = copy.sectionTypes[section.type] || humanize(section.type) || copy.unknownSection

  return (
    <section className="executive-story-section" aria-labelledby={`story-section-${section.order}`}>
      <header>
        <span className="story-section-order">{String(section.order).padStart(2, '0')}</span>
        <div>
          <p>{copy.section}</p>
          <h3 id={`story-section-${section.order}`}>{sectionLabel}</h3>
        </div>
      </header>

      <div className="story-item-list">
        {section.items.map((item, index) => {
          const planItem = planById.get(item.sourceItemId) || null
          const itemAudit = auditById.get(item.sourceItemId) || null
          const insightId = itemAudit?.insightId || planItem?.insightId
          const insight = insightById.get(insightId) || null
          const evidenceCodes = Array.isArray(planItem?.evidenceCodes)
            ? new Set(planItem.evidenceCodes)
            : null
          const fallbackEvidence = evidenceCodes && Array.isArray(insight?.evidence)
            ? insight.evidence.filter((evidence) => evidenceCodes.has(evidence?.code))
            : []
          const role = copy.roles[planItem?.role]
            || humanize(planItem?.role)

          return (
            <article className="executive-story-item" key={item.sourceItemId || index}>
              <div className="story-item-heading">
                {role && <span className="story-role-badge">{role}</span>}
                {planItem?.requiresQualification === true && (
                  <span className="story-qualification-badge">{copy.requiresQualification}</span>
                )}
              </div>
              <p className="story-item-text">{item.text}</p>
              <ClaimEvidence
                sourceItemId={item.sourceItemId}
                planItem={planItem}
                itemAudit={itemAudit}
                fallbackEvidence={fallbackEvidence}
                copy={copy}
              />
            </article>
          )
        })}
      </div>
    </section>
  )
}

export default StorySection
