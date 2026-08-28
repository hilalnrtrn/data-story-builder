const isObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value)

const asStringOrNull = (value) =>
  typeof value === 'string' && value.trim() ? value : null

const asNumberOrNull = (value) =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

const asObjectOrNull = (value) => (isObject(value) ? value : null)
const asArray = (value) => (Array.isArray(value) ? value : [])

/**
 * Normalizes the persisted GET analysis detail contract without deriving facts.
 * Missing numerical values remain null; missing collections become empty arrays.
 */
export function mapAnalysisDetail(payload) {
  if (!isObject(payload)) {
    throw new TypeError('Analysis detail payload must be an object.')
  }

  const id = asStringOrNull(payload.id)

  if (!id) {
    throw new TypeError('Analysis detail payload must contain an id.')
  }

  return {
    id,
    fileName: asStringOrNull(payload.fileName),
    fileType: asStringOrNull(payload.fileType),
    status: asStringOrNull(payload.status),
    failureReason: asStringOrNull(payload.failureReason),
    createdAt: asStringOrNull(payload.createdAt),
    completedAt: asStringOrNull(payload.completedAt),
    rowCount: asNumberOrNull(payload.rowCount),
    columnCount: asNumberOrNull(payload.columnCount),
    dataQualityScore: asNumberOrNull(payload.dataQualityScore),
    profile: asObjectOrNull(payload.profile),
    quality: asObjectOrNull(payload.quality),
    insights: asArray(payload.insights),
    relationships: asArray(payload.relationships),
    insightClusters: asArray(payload.insightClusters),
    insightIntegrity: asArray(payload.insightIntegrity),
    causalityEvaluations: asArray(payload.causalityEvaluations),
    missingContextEvaluations: asArray(payload.missingContextEvaluations),
    hypotheses: asArray(payload.hypotheses),
    storyPlan: asObjectOrNull(payload.storyPlan),
    storyGeneration: asObjectOrNull(payload.storyGeneration),
    generatedStory: asObjectOrNull(payload.generatedStory),
    storyAudit: asObjectOrNull(payload.storyAudit),
    fullStoryAudit: asObjectOrNull(payload.fullStoryAudit),
  }
}
