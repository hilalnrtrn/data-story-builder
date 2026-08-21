import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

        const response = await fetch(`${apiBaseUrl}/api/health`)

        if (!response.ok) {
          throw new Error('System health request failed.')
        }

        const data = await response.json()
        setSystemStatus(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchSystemStatus()
  }, [])

  const renderStatus = (status) => {
    if (status === 'healthy') {
      return <span className="status healthy">✓ Healthy</span>
    }

    return <span className="status unhealthy">✕ Unhealthy</span>
  }

  return (
    <main className="page">
      <section className="status-card">
        <p className="eyebrow">DATA STORY BUILDER</p>

        <h1>System Status</h1>

        <p className="description">
          Technical services required by Data Story Builder.
        </p>

        {loading && <p className="message">Checking services...</p>}

        {error && (
          <p className="message error">
            Unable to reach backend: {error}
          </p>
        )}

        {systemStatus && (
          <div className="services">
            <div className="service-row">
              <span>Backend API</span>
              {renderStatus(systemStatus.backend?.status)}
            </div>

            <div className="service-row">
              <span>Analytics Service</span>
              {renderStatus(systemStatus.analytics?.status)}
            </div>

            <div className="service-row">
              <span>PostgreSQL</span>
              {renderStatus(systemStatus.database?.status)}
            </div>
          </div>
        )}

        {systemStatus && (
          <div className="overall">
            Overall system: {renderStatus(systemStatus.status)}
          </div>
        )}
      </section>
    </main>
  )
}

export default App