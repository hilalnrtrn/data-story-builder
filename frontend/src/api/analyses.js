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

export async function uploadAnalysis(file, language) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('language', language)

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

export async function getAnalysisHypotheses(analysisId) {
  const normalizedId = getNonEmptyString(analysisId)
  if (!normalizedId) throw new AnalysisApiError('')

  let response
  try {
    response = await fetch(`${getApiBaseUrl()}/api/analyses/${encodeURIComponent(normalizedId)}/hypotheses`)
  } catch {
    throw new AnalysisApiError('', { analysisId: normalizedId })
  }

  if (!response.ok) {
    const error = await createResponseError(response)
    error.analysisId ||= normalizedId
    throw error
  }

  const body = await readJson(response)
  if (!Array.isArray(body)) {
    throw new AnalysisApiError('', { status: response.status, analysisId: normalizedId })
  }
  return body
}

export async function updateHypothesisStatus(analysisId, hypothesisId, status) {
  const normalizedAnalysisId = getNonEmptyString(analysisId)
  const normalizedHypothesisId = getNonEmptyString(hypothesisId)
  const normalizedStatus = getNonEmptyString(status)
  if (!normalizedAnalysisId || !normalizedHypothesisId || !normalizedStatus) {
    throw new AnalysisApiError('', { analysisId: normalizedAnalysisId })
  }

  let response
  try {
    response = await fetch(`${getApiBaseUrl()}/api/analyses/${encodeURIComponent(normalizedAnalysisId)}/hypotheses/${encodeURIComponent(normalizedHypothesisId)}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: normalizedStatus }),
    })
  } catch {
    throw new AnalysisApiError('', { analysisId: normalizedAnalysisId })
  }

  if (!response.ok) {
    const error = await createResponseError(response)
    error.analysisId ||= normalizedAnalysisId
    throw error
  }

  const body = await readJson(response)
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw new AnalysisApiError('', { status: response.status, analysisId: normalizedAnalysisId })
  }
  return body
}
