import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { organizerApi } from '../../api/client.js'
import LoadingSpinner from '../../components/LoadingSpinner.jsx'
import { useOrganizerEvents } from '../../hooks/useOrganizerEvents.js'
import { useAuth } from '../../hooks/useAuth.js'
import styles from './Dashboard.module.css'

const REFRESH_INTERVAL_MS = 30_000

const STATUS_LABELS = {
  registered: 'Registered',
  approved: 'Approved',
  participation_confirmed: 'Confirmed',
  bib_collected: 'BIB Collected',
  finished_certified: 'Certified',
}

const STATUS_ACCENTS = {
  registered: 'var(--stage-1)',
  approved: 'var(--stage-2)',
  participation_confirmed: 'var(--stage-3)',
  bib_collected: 'var(--stage-4)',
  finished_certified: 'var(--stage-5)',
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { events, selectedId, setSelectedId, loading: eventsLoading } = useOrganizerEvents()
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const intervalRef = useRef(null)

  function fetchSummary(id, isInitial = false) {
    if (!id) return
    if (isInitial) setLoading(true)
    organizerApi
      .getSummary(id)
      .then(setSummary)
      .catch(() => setError('Could not load summary.'))
      .finally(() => {
        if (isInitial) setLoading(false)
      })
  }

  useEffect(() => {
    if (!selectedId) return
    fetchSummary(selectedId, true)
    clearInterval(intervalRef.current)
    intervalRef.current = setInterval(() => fetchSummary(selectedId, false), REFRESH_INTERVAL_MS)
    return () => clearInterval(intervalRef.current)
  }, [selectedId])

  function handleSignOut() {
    logout()
    navigate('/login')
  }

  if (eventsLoading) return <LoadingSpinner text="Loading dashboard…" />
  if (error) return <div className="page-container"><p className="error-msg">{error}</p></div>

  const statuses = Object.keys(STATUS_LABELS)
  const totalCount = summary?.total || 1

  return (
    <div className={styles.pageWrapper}>
      {/* LEFT PANEL SIDEBAR (240px fixed) */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop}>
          <div className={styles.sidebarUser}>
            <div className={styles.userAvatar}>
              {user?.name ? user.name.split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase() : 'O'}
            </div>
            <div className={styles.userNameGroup}>
              <span className={styles.userName}>{user?.name || 'Organizer'}</span>
              <span className={styles.userRole}>Event Manager</span>
            </div>
          </div>

          <nav className={styles.sidebarNav}>
            <button
              className={`${styles.navItem} ${styles.navItemActive}`}
              onClick={() => navigate('/organizer')}
            >
              <svg className={styles.navIcon} viewBox="0 0 24 24" strokeWidth="2">
                <rect x="3" y="3" width="7" height="9" rx="1" />
                <rect x="14" y="3" width="7" height="5" rx="1" />
                <rect x="14" y="12" width="7" height="9" rx="1" />
                <rect x="3" y="16" width="7" height="5" rx="1" />
              </svg>
              Overview
            </button>
            <button
              className={styles.navItem}
              onClick={() => navigate('/organizer/regs')}
            >
              <svg className={styles.navIcon} viewBox="0 0 24 24" strokeWidth="2">
                <path d="M12 20h9M3 20h4M3 12h18M3 4h18" strokeLinecap="round" />
              </svg>
              Registrations
            </button>
            <button
              className={styles.navItem}
              onClick={() => navigate('/organizer/tasks')}
            >
              <svg className={styles.navIcon} viewBox="0 0 24 24" strokeWidth="2">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" strokeLinecap="round" />
              </svg>
              Task Board
            </button>
            <button
              className={styles.navItem}
              onClick={() => navigate('/organizer/vol-apps')}
            >
              <svg className={styles.navIcon} viewBox="0 0 24 24" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 7a4 4 0 11-4-4 4 4 0 014 4z" strokeLinecap="round" />
              </svg>
              Volunteers
            </button>
            <button
              className={styles.navItem}
              onClick={() => navigate('/organizer/events')}
            >
              <svg className={styles.navIcon} viewBox="0 0 24 24" strokeWidth="2">
                <rect x="3" y="4" width="18" height="16" rx="2" />
                <path d="M16 2v4M8 2v4M3 10h18" strokeLinecap="round" />
              </svg>
              Events
            </button>
          </nav>
        </div>

        <div className={styles.sidebarBottom}>
          <button className={styles.signOutLink} onClick={handleSignOut}>
            <svg className={styles.navIcon} viewBox="0 0 24 24" strokeWidth="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" strokeLinecap="round" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* RIGHT MAIN CONTENT AREA */}
      <main className={styles.mainContent}>
        <div className={styles.header}>
          <h1 className={styles.heading}>Overview</h1>

          {/* Event selector */}
          {events.length > 1 && (
            <div style={{ minWidth: 220 }}>
              <select
                id="event-select"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                style={{ padding: '6px 12px', fontSize: '0.875rem' }}
              >
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {events.length === 0 && (
          <p style={{ color: 'var(--color-text-secondary)' }}>
            No active events.{' '}
            <Link to="/organizer/events" style={{ color: 'var(--color-primary)' }}>
              Create an event →
            </Link>
          </p>
        )}

        {/* Summary metric cards (4-across) */}
        <div className={styles.cards}>
          {statuses.map((s) => {
            const count = summary?.[s] ?? 0
            const pct = Math.round((count / totalCount) * 100)
            return (
              <div
                key={s}
                className={styles.statCard}
                style={{ borderLeft: `3px solid ${STATUS_ACCENTS[s]}` }}
                onClick={() => navigate(`/organizer/regs?status=${s}`)}
                title={`View ${STATUS_LABELS[s]} registrations`}
                data-testid={`summary-card-${s}`}
              >
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className={styles.label}>{STATUS_LABELS[s]}</span>
                  <span className={styles.statValue} style={{ color: STATUS_ACCENTS[s] }}>
                    {count}
                  </span>
                </div>
                <div style={{ marginTop: 'auto' }}>
                  <span className={`${styles.trendText} ${styles.trendNeutral}`}>
                    {pct}% of total
                  </span>
                  <div className={styles.miniProgressBar}>
                    <div
                      className={styles.miniProgressFill}
                      style={{ width: `${pct}%`, background: STATUS_ACCENTS[s] }}
                    />
                  </div>
                </div>
              </div>
            )
          })}

          {/* Total card */}
          <div
            className={styles.statCard}
            style={{ borderLeft: '3px solid var(--color-border-strong)' }}
            onClick={() => navigate('/organizer/regs')}
            data-testid="summary-card-total"
          >
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className={styles.label}>Total Runners</span>
              <span className={styles.statValue}>{summary?.total ?? 0}</span>
            </div>
            <div style={{ marginTop: 'auto' }}>
              <span className={`${styles.trendText} ${styles.trendPositive}`}>+100% active</span>
              <div className={styles.miniProgressBar}>
                <div
                  className={styles.miniProgressFill}
                  style={{ width: '100%', background: 'var(--color-border-strong)' }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Needs approval callout */}
        {(summary?.registered ?? 0) > 0 && (
          <div
            className={styles.pendingCallout}
            onClick={() => navigate(`/organizer/regs?status=registered`)}
          >
            <span className={styles.calloutText}>
              🔔 {summary.registered} registration{summary.registered !== 1 ? 's' : ''} waiting for your approval
            </span>
            <span className={styles.calloutAction}>Review now →</span>
          </div>
        )}

        {/* Quick actions */}
        <div className={styles.actionsSection}>
          <h2 className={styles.actionsTitle}>Quick Actions</h2>
          <div className={styles.actions}>
            <button
              className="btn-primary press-effect"
              onClick={() => navigate('/organizer/vol-apps')}
            >
              🙋 Volunteers
            </button>
            <button
              className="btn-primary press-effect"
              onClick={() => navigate('/organizer/regs')}
              data-testid="view-registrations-button"
            >
              📋 Registrations
            </button>
            <button
              className="btn-primary press-effect"
              onClick={() => navigate('/organizer/tasks')}
              data-testid="go-to-taskboard-button"
            >
              ✅ Task Board
            </button>
            <button
              className="btn-secondary press-effect"
              onClick={() => setShowUploadModal(true)}
              data-testid="upload-finish-times-button"
            >
              ⏱ Finish Times CSV
            </button>
          </div>
        </div>
      </main>

      {/* CSV Upload Modal */}
      {showUploadModal && (
        <UploadModal eventId={selectedId} onClose={() => setShowUploadModal(false)} />
      )}
    </div>
  )
}

function UploadModal({ eventId, onClose }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) {
      setError('Please select a CSV file')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await organizerApi.uploadFinishTimes(eventId, file)
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>Upload Finish Times</h2>
          <button className={styles.modalClose} onClick={onClose}>
            ×
          </button>
        </div>

        <p className={styles.modalHint}>
          CSV format: <code>bib_number,finish_time</code>
          <br />
          Example row: <code>001,01:23:45</code>
          <br />
          Header row is required. Max 1000 rows.
        </p>

        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files[0])}
            data-testid="csv-file-input"
            style={{ padding: '8px', border: '1px solid var(--color-border)' }}
          />
          {error && <p className="error-msg">{error}</p>}
          <button
            type="submit"
            className="btn-primary press-effect"
            disabled={loading}
            data-testid="csv-upload-submit"
          >
            {loading ? 'Uploading…' : 'Upload'}
          </button>
        </form>

        {result && (
          <div className={styles.uploadResult}>
            <p className="success-msg">
              Processed: {result.processed} &nbsp;|&nbsp; Skipped: {result.skipped}
            </p>
            {result.warnings?.length > 0 && (
              <ul className={styles.warnList}>
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
            {result.errors?.length > 0 && (
              <ul className={styles.errorList}>
                {result.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
