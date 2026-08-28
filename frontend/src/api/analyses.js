const getApiBaseUrl = () => (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class AnalysisApiError extends Error {
  constructor(message, { status = null, analysisId = null, isNotFound = false } = {}) {
    super(message || '')
    this.name = 'AnalysisApiError'
    this.status = status
    this.analysisId = analysisId
    this.isNotFound = isNotFound
  }
}

const readJson = async (response) => {
  try {
    return await response.json()
  } catch {
    return null
  }
}

const getNonEmptyString = (value) =>
  typeof value === 'string' && value.trim() ? value.trim() : null

const createResponseError = async (response) => {
  const body = await readJson(response)
  const message = getNonEmptyString(body?.error) || getNonEmptyString(body?.detail)
  const analysisId = getNonEmptyString(body?.analysisId)

  return new AnalysisApiError(message, {
    status: response.status,
    analysisId,
    isNotFound: response.status === 404,
  })
}

export async function uploadAnalysis(file) {
  const formData = new FormData()
  formData.append('file', file)

  let response

  try {
    response = await fetch(`${getApiBaseUrl()}/api/analyses`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new AnalysisApiError('')
  }

  if (!response.ok) {
    throw await createResponseError(response)
  }

  const body = await readJson(response)
  const analysisId = getNonEmptyString(body?.analysisId)

  if (!analysisId) {
    throw new AnalysisApiError('', { status: response.status })
  }

  return analysisId
}

export async function getAnalysisDetail(analysisId) {
  const normalizedId = getNonEmptyString(analysisId)

  if (!normalizedId) {
    throw new AnalysisApiError('')
  }

  let response

  try {
    response = await fetch(
      `${getApiBaseUrl()}/api/analyses/${encodeURIComponent(normalizedId)}`,
    )
  } catch {
    throw new AnalysisApiError('', { analysisId: normalizedId })
  }

  if (!response.ok) {
    const error = await createResponseError(response)

    if (!error.analysisId) {
      error.analysisId = normalizedId
    }

    throw error
  }

  const body = await readJson(response)

  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw new AnalysisApiError('', {
      status: response.status,
      analysisId: normalizedId,
    })
  }

  return body
}

export async function getAnalysisHistory() {
  let response

  try {
    response = await fetch(`${getApiBaseUrl()}/api/analyses`)
  } catch {
    throw new AnalysisApiError('')
  }

  if (!response.ok) {
    throw await createResponseError(response)
  }

  const body = await readJson(response)

  if (!Array.isArray(body)) {
    throw new AnalysisApiError('', { status: response.status })
  }

  return body
}
