import React, { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { organizerApi, registrationsApi } from '../../api/client.js'
import LoadingSpinner from '../../components/LoadingSpinner.jsx'
import { useOrganizerEvents } from '../../hooks/useOrganizerEvents.js'
import styles from './Registrations.module.css'

const PAGE_SIZE = 20

const ALL_STATUSES = [
  'registered',
  'approved',
  'participation_confirmed',
  'bib_collected',
  'finished_certified',
]

const STAT_LABELS = {
  registered: 'Registered',
  approved: 'Approved',
  participation_confirmed: 'Confirmed',
  bib_collected: 'BIB Collected',
  finished_certified: 'Certified',
}

export default function Registrations() {
  const { events, selectedId, setSelectedId } = useOrganizerEvents()
  const [searchParams] = useSearchParams()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Inline action state: { [registrationId]: 'approve' | 'finish' | null }
  const [inlineAction, setInlineAction] = useState({})
  const [bibInput, setBibInput] = useState('')
  const [timeInput, setTimeInput] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState(null)

  // QR URL cache
  const [qrUrls, setQrUrls] = useState({})

  const fetchData = useCallback(async () => {
    if (!selectedId) return
    setLoading(true)
    setError(null)
    try {
      const params = { event_id: selectedId, page, page_size: PAGE_SIZE }
      if (statusFilter) params.status = statusFilter
      if (search) params.search = search
      const result = await organizerApi.listRegistrations(params)
      setItems(result.items)
      setTotal(result.total)
    } catch {
      setError('Failed to load registrations.')
    } finally {
      setLoading(false)
    }
  }, [selectedId, page, statusFilter, search])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  function handleSearchSubmit(e) {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  function openApprove(id) {
    setInlineAction({ [id]: 'approve' })
    setBibInput('')
    setActionError(null)
  }

  function openFinish(id) {
    setInlineAction({ [id]: 'finish' })
    const now = new Date()
    now.setSeconds(0, 0)
    setTimeInput(now.toISOString().slice(0, 16))
    setActionError(null)
  }

  function closeInline() {
    setInlineAction({})
    setActionError(null)
  }

  async function submitApprove(id) {
    const bib = bibInput.trim() || null
    setActionLoading(true)
    setActionError(null)
    try {
      const updated = await organizerApi.approve(id, bib)
      setItems((prev) => prev.map((r) => (r.id === id ? { ...r, ...updated } : r)))
      closeInline()
      try {
        const { qr_url } = await registrationsApi.getQrUrl(id)
        setQrUrls((prev) => ({ ...prev, [id]: qr_url }))
      } catch {
        // QR URL loading non-fatal
      }
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Approval failed')
    } finally {
      setActionLoading(false)
    }
  }

  async function submitFinish(id) {
    if (!timeInput) {
      setActionError('Finish time is required')
      return
    }
    setActionLoading(true)
    setActionError(null)
    try {
      const isoTime = new Date(timeInput).toISOString()
      const updated = await organizerApi.setFinishTime(id, isoTime)
      setItems((prev) => prev.map((r) => (r.id === id ? { ...r, ...updated } : r)))
      closeInline()
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Failed to set finish time')
    } finally {
      setActionLoading(false)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="page-container">
      <h1 className={styles.heading}>Registrations</h1>

      {/* Event Selector */}
      {events.length > 1 && (
        <div className="form-group" style={{ maxWidth: 360, marginBottom: '1.5rem' }}>
          <label htmlFor="event-select">Event</label>
          <select
            id="event-select"
            value={selectedId}
            onChange={(e) => {
              setSelectedId(e.target.value)
              setPage(1)
            }}
          >
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Search & Filter Row */}
      <div className={styles.searchFilterRow}>
        <div className={styles.leftControls}>
          <form onSubmit={handleSearchSubmit} className={styles.searchWrapper}>
            <svg className={styles.searchIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="search"
              placeholder="Search name or email…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className={styles.searchInput}
              data-testid="search-input"
            />
          </form>

          <div className={styles.statusPills}>
            <button
              className={`${styles.statusPillBtn} ${statusFilter === '' ? styles.statusPillBtnActive : ''}`}
              onClick={() => {
                setStatusFilter('')
                setPage(1)
              }}
            >
              All
            </button>
            {ALL_STATUSES.map((s) => (
              <button
                key={s}
                className={`${styles.statusPillBtn} ${statusFilter === s ? styles.statusPillBtnActive : ''}`}
                onClick={() => {
                  setStatusFilter(s)
                  setPage(1)
                }}
              >
                {STAT_LABELS[s]}
              </button>
            ))}
          </div>
        </div>

        <span className={styles.resultsCount}>
          Showing {items.length} of {total} runners
        </span>
      </div>

      {loading && <LoadingSpinner text="Loading runners list…" />}
      {error && <p className="error-msg">{error}</p>}

      {!loading && !error && (
        <>
          <div className={styles.tableWrapper}>
            <table className={styles.regTable}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Distance</th>
                  <th>T-shirt</th>
                  <th>BIB</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', color: 'var(--color-text-tertiary)', padding: '2rem' }}>
                      No registrations found matching this selection.
                    </td>
                  </tr>
                )}
                {items.map((reg) => {
                  const isActionOpen = inlineAction[reg.id] != null
                  const actionType = inlineAction[reg.id]

                  return (
                    <React.Fragment key={reg.id}>
                      <tr data-testid={`reg-row-${reg.id}`}>
                        <td>{reg.user?.name ?? '—'}</td>
                        <td>{reg.user?.email ?? '—'}</td>
                        <td>{reg.distance ?? '—'}</td>
                        <td>{reg.tshirt_size?.toUpperCase() ?? '—'}</td>
                        <td className={styles.monoCol} data-testid={`bib-${reg.id}`}>
                          {reg.bib_number ?? '—'}
                          {qrUrls[reg.id] && (
                            <div style={{ marginTop: '0.4rem' }}>
                              <img
                                src={qrUrls[reg.id]}
                                alt={`QR for BIB ${reg.bib_number}`}
                                style={{ width: 64, height: 64, display: 'block', borderRadius: 4, border: '1px solid var(--color-border)' }}
                                data-testid={`qr-img-${reg.id}`}
                              />
                            </div>
                          )}
                        </td>
                        <td>
                          <span className={`badge badge-${reg.status}`}>
                            {reg.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td>
                          {reg.status === 'registered' && !isActionOpen && (
                            <button
                              className="btn-primary btn-sm press-effect"
                              onClick={() => openApprove(reg.id)}
                              data-testid={`approve-btn-${reg.id}`}
                            >
                              Approve
                            </button>
                          )}
                          {reg.status === 'bib_collected' && !isActionOpen && (
                            <button
                              className="btn-success btn-sm press-effect"
                              onClick={() => openFinish(reg.id)}
                              data-testid={`finish-btn-${reg.id}`}
                            >
                              ⏱ Enter Finish Time
                            </button>
                          )}
                          {isActionOpen && (
                            <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                              Editing...
                            </span>
                          )}
                        </td>
                      </tr>

                      {/* Smooth inline expand row */}
                      {isActionOpen && (
                        <tr className={styles.inlineApproveRow}>
                          <td colSpan={7} className={styles.inlineApproveCell}>
                            <div className={styles.inlineForm}>
                              {actionType === 'approve' ? (
                                <>
                                  <input
                                    type="text"
                                    placeholder="BIB (leave blank to auto-generate)"
                                    value={bibInput}
                                    onChange={(e) => setBibInput(e.target.value)}
                                    data-testid={`bib-input-${reg.id}`}
                                  />
                                  <button
                                    className="btn-success btn-sm press-effect"
                                    onClick={() => submitApprove(reg.id)}
                                    disabled={actionLoading}
                                    data-testid={`bib-confirm-btn-${reg.id}`}
                                  >
                                    {actionLoading ? '…' : 'Approve runner'}
                                  </button>
                                </>
                              ) : (
                                <>
                                  <input
                                    type="datetime-local"
                                    value={timeInput}
                                    onChange={(e) => setTimeInput(e.target.value)}
                                  />
                                  <button
                                    className="btn-success btn-sm press-effect"
                                    onClick={() => submitFinish(reg.id)}
                                    disabled={actionLoading}
                                  >
                                    {actionLoading ? '…' : 'Save finish time'}
                                  </button>
                                </>
                              )}
                              <button className="btn-secondary btn-sm press-effect" onClick={closeInline}>
                                Cancel
                              </button>
                              {actionError && <span className="error-msg">{actionError}</span>}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className="btn-secondary btn-sm press-effect"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                data-testid="prev-page-button"
              >
                ← Prev
              </button>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages}
              </span>
              <button
                className="btn-secondary btn-sm press-effect"
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                data-testid="next-page-button"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
