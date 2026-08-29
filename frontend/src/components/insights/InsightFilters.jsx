const FILTER_TYPES = ['ALL', 'CHANGE', 'TREND', 'ANOMALY', 'CONTRIBUTION', 'CONTRAST']
const SCAN_FILTERS = [
  { key: 'PRIORITY', countKey: 'priorityAttention' },
  { key: 'INTEGRITY', countKey: 'integrityAttention' },
  { key: 'COUNTER', countKey: 'counterEvidenceInsights' },
]

function InsightFilters({
  activeType,
  scanFilter,
  scanCounts,
  sortBy,
  copy,
  onTypeChange,
  onScanFilterChange,
  onSortChange,
  onReset,
}) {
  const isDefault = activeType === 'ALL' && scanFilter === 'ALL' && sortBy === 'backend'

  return (
    <div className="insight-explorer-toolbar">
      <div className="insight-filter-groups">
        <span className="insight-toolbar-label">{copy.typeFilterTitle}</span>
        <div className="insight-type-filters" role="group" aria-label={copy.filterLabel}>
          {FILTER_TYPES.map((type) => (
            <button
              type="button"
              className="insight-filter-button"
              aria-pressed={activeType === type}
              key={type}
              onClick={() => onTypeChange(type)}
            >
              {copy.types[type] || type}
            </button>
          ))}
        </div>
        <span className="insight-toolbar-label">{copy.attentionFilterTitle}</span>
        <div className="insight-scan-filters" role="group" aria-label={copy.scanFilterLabel}>
          <button
            type="button"
            className="insight-scan-filter"
            aria-pressed={scanFilter === 'ALL'}
            onClick={() => onScanFilterChange('ALL')}
          >
            {copy.scanFilters.ALL}
          </button>
          {SCAN_FILTERS.filter(({ countKey }) => scanCounts?.[countKey] > 0).map(({ key, countKey }) => (
            <button
              type="button"
              className="insight-scan-filter"
              aria-pressed={scanFilter === key}
              key={key}
              onClick={() => onScanFilterChange(key)}
            >
              {copy.scanFilters[key]} <span>{scanCounts[countKey]}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="insight-toolbar-actions">
        <label className="insight-sort-control">
          <span>{copy.sortLabel}</span>
          <select value={sortBy} onChange={(event) => onSortChange(event.target.value)}>
            <option value="backend">{copy.sortOptions.backend}</option>
            <option value="priority">{copy.sortOptions.priority}</option>
            <option value="importance">{copy.sortOptions.importance}</option>
            <option value="confidence">{copy.sortOptions.confidence}</option>
          </select>
        </label>
        {!isDefault && <button type="button" className="insight-reset-button" onClick={onReset}>{copy.resetFilters}</button>}
      </div>
    </div>
  )
}

export default InsightFilters
