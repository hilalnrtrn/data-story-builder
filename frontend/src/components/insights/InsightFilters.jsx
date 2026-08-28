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
}) {
  return (
    <div className="insight-explorer-toolbar">
      <div className="insight-filter-groups">
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

      <label className="insight-sort-control">
        <span className="visually-hidden">{copy.sortLabel}</span>
        <select value={sortBy} onChange={(event) => onSortChange(event.target.value)}>
          <option value="backend">{copy.sortOptions.backend}</option>
          <option value="priority">{copy.sortOptions.priority}</option>
          <option value="importance">{copy.sortOptions.importance}</option>
          <option value="confidence">{copy.sortOptions.confidence}</option>
        </select>
      </label>
    </div>
  )
}

export default InsightFilters
