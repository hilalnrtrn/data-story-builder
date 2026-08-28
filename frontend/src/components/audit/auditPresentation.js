export const AUDIT_DECISIONS = {
  0: 'pass',
  1: 'passWithWarnings',
  2: 'regenerate',
  3: 'block',
}

export const DIFF_STATUSES = {
  0: 'pass',
  1: 'fail',
}

export const EVIDENCE_STRENGTHS = {
  0: 'strong',
  1: 'none',
  2: 'notApplicable',
}

export const BIAS_STATUSES = {
  0: 'pass',
  1: 'warning',
  2: 'fail',
}

export const BIAS_RISKS = {
  0: 'none',
  1: 'low',
  2: 'medium',
  3: 'high',
}

export const BIAS_CATEGORIES = {
  0: 'positiveFraming',
  1: 'negativeFraming',
  2: 'selectiveEmphasis',
  3: 'certaintyInflation',
  4: 'causalFraming',
  5: 'missingContextOmission',
}

export const semanticClass = (key) => {
  if (key === 'pass' || key === 'strong') return 'is-positive'
  if (key === 'passWithWarnings' || key === 'warning' || key === 'low' || key === 'medium' || key === 'regenerate') return 'is-caution'
  if (key === 'fail' || key === 'high' || key === 'block') return 'is-risk'
  return 'is-neutral'
}

export const asArrayOrNull = (value) => Array.isArray(value) ? value : null

export const formatScore = (value, locale, unavailable) => (
  typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat(locale, {
      style: 'percent',
      maximumFractionDigits: 1,
    }).format(value)
    : unavailable
)

export const displayValue = (value, unavailable) => {
  if (value === null || value === undefined) return unavailable
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return unavailable
}
