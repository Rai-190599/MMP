import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { eventsApi, registrationsApi, volunteerApi } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import styles from './EventBrowser.module.css'

const PAGE_SIZE = 10

function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// ---------------------------------------------------------------------------
// Banner image with fallback gradient
// ---------------------------------------------------------------------------
function CoverPhoto({ images, accentIndex }) {
  const [current, setCurrent] = useState(0)
  const timerRef = useRef(null)

  const GRADIENTS = [
    'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
    'linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)',
    'linear-gradient(135deg, #7B3FA0 0%, #db2777 100%)',
    'linear-gradient(135deg, #16a34a 0%, #0d9488 100%)',
  ]

  useEffect(() => {
    if (!images || images.length <= 1) return
    timerRef.current = setInterval(() => setCurrent((c) => (c + 1) % images.length), 4000)
    return () => clearInterval(timerRef.current)
  }, [images?.length])

  if (!images || images.length === 0) {
    return (
      <div
        className={styles.coverPhoto}
        style={{ background: GRADIENTS[accentIndex % 4] }}
        aria-hidden="true"
      >
        <span className={styles.coverIcon}>🏃</span>
      </div>
    )
  }

  return (
    <div className={styles.coverPhoto}>
      {images.map((url, i) => (
        <img
          key={i}
          src={url}
          alt=""
          className={styles.coverImg}
          style={{ opacity: i === current ? 1 : 0 }}
        />
      ))}
      {images.length > 1 && (
        <div className={styles.coverDots}>
          {images.map((_, i) => (
            <button
              key={i}
              className={`${styles.coverDot} ${i === current ? styles.coverDotActive : ''}`}
              onClick={() => { setCurrent(i); clearInterval(timerRef.current) }}
              aria-label={`Banner ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Event Card — vertical layout
// ---------------------------------------------------------------------------
function EventCard({ event, detail, index, onDetailRefresh }) {
  const navigate = useNavigate()
  const userReg = detail?.user_registration ?? null
  const userVolApp = detail?.user_volunteer_application ?? null
  const regCount = detail?.registration_count ?? event.registration_count ?? 0
  const banners = detail?.banner_images ?? []

  const slotCaps = detail?.volunteer_slot_caps ?? {}
  const slotsFilled = detail?.volunteer_slots_filled ?? {}
  const totalSlots = Object.values(slotCaps).reduce((a, b) => a + b, 0)
  const totalFilled = Object.values(slotsFilled).reduce((a, b) => a + b, 0)
  const openSlots = Math.max(totalSlots - totalFilled, 0)

  const [cancelling, setCancelling] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const [actionError, setActionError] = useState(null)

  const lockedStatuses = ['bib_collected', 'finished_certified']
  const canCancelReg = userReg && !lockedStatuses.includes(userReg.status)
  const canWithdrawVol = userVolApp && userVolApp.status === 'pending'

  async function handleCancelRegistration() {
    if (!window.confirm('Cancel your registration for this event?')) return
    setCancelling(true)
    setActionError(null)
    try {
      await registrationsApi.cancel(event.id)
      onDetailRefresh(event.id)
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Could not cancel registration.')
    } finally {
      setCancelling(false)
    }
  }

  async function handleWithdrawVolunteer() {
    if (!window.confirm('Withdraw your volunteer application?')) return
    setWithdrawing(true)
    setActionError(null)
    try {
      await volunteerApi.withdraw(userVolApp.id)
      onDetailRefresh(event.id)
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Could not withdraw application.')
    } finally {
      setWithdrawing(false)
    }
  }

  const distances = event.distances ?? []
  const daysLeft = event.days_until_event

  const ACCENT_COLORS = ['#4f46e5', '#0ea5e9', '#7B3FA0', '#16a34a']
  const accentColor = ACCENT_COLORS[index % 4]

  return (
    <div className={`${styles.card} ${styles.eventCard}`}>
      {/* Cover photo / banner */}
      <CoverPhoto images={banners} accentIndex={index} />

      {/* Days-to-go badge overlaid on cover */}
      <div className={styles.daysChip} style={{ background: accentColor }}>
        <span className={styles.daysNum}>{daysLeft}</span>
        <span className={styles.daysLabel}>days</span>
      </div>

      {/* Card body */}
      <div className={styles.cardBody}>

        {/* Title + meta */}
        <div className={styles.cardMeta}>
          <h3 className={styles.eventName}>{event.name}</h3>
          <div className={styles.metaRow}>
            <span className={styles.metaChip}>📅 {formatDate(event.event_date)}</span>
            {event.location && <span className={styles.metaChip}>📍 {event.location}</span>}
          </div>
        </div>

        {/* Distance pills */}
        {distances.length > 0 && (
          <div className={styles.distanceRow}>
            {distances.map((d) => (
              <span key={d} className={styles.distancePill} style={{ borderColor: accentColor, color: accentColor }}>
                {d}
              </span>
            ))}
          </div>
        )}

        {/* Stats row */}
        <div className={styles.statsRow}>
          <div className={styles.stat}>
            <span className={styles.statVal}>{regCount}</span>
            <span className={styles.statLbl}>registered</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={styles.statVal} style={{ color: openSlots > 0 ? '#16a34a' : '#9ca3af' }}>
              {openSlots > 0 ? openSlots : '—'}
            </span>
            <span className={styles.statLbl}>vol. spots</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={styles.statVal}>{distances.length || '—'}</span>
            <span className={styles.statLbl}>distances</span>
          </div>
        </div>

        {/* Error */}
        {actionError && <p className={styles.cardError} role="alert">{actionError}</p>}

        {/* Action buttons */}
        <div className={styles.actions}>
          {/* Registration */}
          {userReg ? (
            <div className={styles.actionRow}>
              <button
                className={styles.statusBtn}
                style={{ '--accent': accentColor }}
                onClick={() => navigate(`/status?event_id=${event.id}`)}
              >
                ✓ Registered
                {userReg.status !== 'registered' && (
                  <span className={styles.statusSub}>
                    {userReg.status.replace(/_/g, ' ')}
                  </span>
                )}
              </button>
              {canCancelReg && (
                <button
                  className={styles.revokeBtn}
                  onClick={handleCancelRegistration}
                  disabled={cancelling}
                  title="Cancel registration"
                >
                  {cancelling ? '…' : 'Revoke'}
                </button>
              )}
            </div>
          ) : (
            <button
              className={styles.primaryBtn}
              style={{ '--accent': accentColor }}
              onClick={() => navigate(`/events/${event.id}/register`)}
            >
              Register →
            </button>
          )}

          {/* Volunteer */}
          {userVolApp ? (
            <div className={styles.actionRow}>
              <span className={`${styles.volBadge} ${styles[`vol_${userVolApp.status}`]}`}>
                {{
                  pending: '⏳ Applied',
                  approved: '✅ Volunteering',
                  rejected: '❌ Not approved',
                }[userVolApp.status] ?? '🙋 Applied'}
              </span>
              {canWithdrawVol && (
                <button
                  className={styles.revokeBtn}
                  onClick={handleWithdrawVolunteer}
                  disabled={withdrawing}
                  title="Withdraw volunteer application"
                >
                  {withdrawing ? '…' : 'Revoke'}
                </button>
              )}
            </div>
          ) : (
            <button
              className={styles.secondaryBtn}
              onClick={() => navigate(`/events/${event.id}/volunteer`)}
            >
              🙋 Volunteer{openSlots > 0 ? ` (${openSlots} spots)` : ''}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function EventBrowser() {
  const location = useLocation()
  const toast = location.state?.toast ?? null

  const [events, setEvents] = useState([])
  const [details, setDetails] = useState({})
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const [activeFilter, setActiveFilter] = useState('All')
  const detailsLoadedRef = useRef(new Set())

  async function loadDetails(eventList) {
    const toFetch = eventList.filter((e) => !detailsLoadedRef.current.has(e.id))
    if (!toFetch.length) return
    const results = await Promise.allSettled(toFetch.map((e) => eventsApi.getEventDetail(e.id)))
    const newDetails = {}
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        newDetails[toFetch[i].id] = r.value
        detailsLoadedRef.current.add(toFetch[i].id)
      }
    })
    setDetails((prev) => ({ ...prev, ...newDetails }))
  }

  async function refreshDetail(eventId) {
    detailsLoadedRef.current.delete(eventId)
    try {
      const fresh = await eventsApi.getEventDetail(eventId)
      detailsLoadedRef.current.add(eventId)
      setDetails((prev) => ({ ...prev, [eventId]: fresh }))
    } catch { /* silently ignore */ }
  }

  useEffect(() => {
    setLoading(true)
    eventsApi
      .listEvents({ upcoming: true, page: 1, page_size: PAGE_SIZE })
      .then(async (data) => {
        setEvents(data.items)
        setTotal(data.total)
        setPage(1)
        await loadDetails(data.items)
      })
      .catch(() => setError('Could not load events. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  async function handleLoadMore() {
    setLoadingMore(true)
    try {
      const data = await eventsApi.listEvents({ upcoming: true, page: page + 1, page_size: PAGE_SIZE })
      const newEvents = [...events, ...data.items]
      setEvents(newEvents)
      setPage(page + 1)
      await loadDetails(data.items)
    } catch { /* silently fail */ }
    finally { setLoadingMore(false) }
  }

  const filters = ['All', '5K', '10K', '21K', 'Half Marathon', 'Full Marathon']
  const filteredEvents = events.filter((e) => {
    if (activeFilter === 'All') return true
    return (e.distances ?? []).some((d) => d.toLowerCase().includes(activeFilter.toLowerCase()))
  })

  if (loading) return <LoadingSpinner text="Loading upcoming races…" />

  return (
    <div className={styles.page}>
      {toast && <div className={styles.toast}>✓ {toast}</div>}

      <div className={styles.headerSection}>
        <div className={styles.titleArea}>
          <h1 className={styles.heading}>Upcoming Races</h1>
          <p className={styles.headingSub}>Find your next challenge · {total} event{total !== 1 ? 's' : ''}</p>
        </div>
        <div className={styles.filterPills}>
          {filters.map((f) => (
            <button
              key={f}
              className={`${styles.filterPill} ${activeFilter === f ? styles.filterPillActive : ''}`}
              onClick={() => setActiveFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      {!error && filteredEvents.length === 0 && (
        <div className={styles.empty}>
          <span style={{ fontSize: '2.5rem' }}>🏁</span>
          <span className={styles.emptyTitle}>No matching races found</span>
          <span className={styles.emptySub}>Try another filter or check back soon!</span>
        </div>
      )}

      <div className={styles.grid}>
        {filteredEvents.map((event, i) => (
          <EventCard
            key={event.id}
            event={event}
            detail={details[event.id] ?? null}
            index={i}
            onDetailRefresh={refreshDetail}
          />
        ))}
      </div>

      {events.length < total && (
        <div className={styles.loadMoreContainer}>
          <button
            className={`btn-secondary ${styles.loadMoreBtn} press-effect`}
            onClick={handleLoadMore}
            disabled={loadingMore}
          >
            {loadingMore ? 'Loading…' : `Load more events ↓`}
          </button>
        </div>
      )}
    </div>
  )
}
