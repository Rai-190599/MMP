import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { eventsApi, volunteerApi } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import styles from './VolunteerApply.module.css'

const ROLES = [
  {
    key: 'registration_desk',
    label: 'Registration Desk',
    description: 'Check in runners at the start, collect BIB confirmations',
  },
  {
    key: 'finish_line',
    label: 'Finish Line',
    description: 'Record finish times, scan BIBs as runners cross the line',
  },
  {
    key: 'general',
    label: 'General Support',
    description: 'Water stations, route marshalling, general event support',
  },
]

export default function VolunteerApply() {
  const { eventId } = useParams()

  const [event, setEvent] = useState(null)
  const [slots, setSlots] = useState([])
  const [existingApp, setExistingApp] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [selectedRole, setSelectedRole] = useState(null)
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  useEffect(() => {
    Promise.allSettled([
      eventsApi.getEventDetail(eventId),
      volunteerApi.getEventSlots(eventId),
      volunteerApi.getMyApplications({ event_id: eventId }),
    ]).then(([eventRes, slotsRes, appsRes]) => {
      if (eventRes.status === 'fulfilled') setEvent(eventRes.value)
      if (slotsRes.status === 'fulfilled') setSlots(slotsRes.value.slots ?? [])
      if (appsRes.status === 'fulfilled') {
        const apps = appsRes.value ?? []
        if (apps.length > 0) setExistingApp(apps[0])
      }
    }).finally(() => setLoading(false))
  }, [eventId])

  function getSlot(roleKey) {
    return slots.find((s) => s.role === roleKey) ?? { cap: 0, filled: 0, remaining: 0, is_open: false }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!selectedRole) return
    setSubmitError(null)
    setSubmitting(true)
    try {
      await volunteerApi.apply({
        event_id: eventId,
        desired_role: selectedRole,
        note: note.trim() || null,
      })
      setSubmitted(true)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setSubmitError(typeof detail === 'string' ? detail : 'Application failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <LoadingSpinner text="Loading…" />

  if (error) {
    return (
      <div className="page-container">
        <p className="error-msg">{error}</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>{event?.name ?? 'Volunteer Application'}</h1>
      <p className={styles.subheading}>
        {event
          ? `📅 ${new Date(event.event_date).toLocaleDateString(undefined, { dateStyle: 'long' })}`
          : ''}
      </p>

      {/* Already applied — show status */}
      {existingApp && !submitted && (
        <div className={styles.statusCard}>
          <p>
            {existingApp.status === 'pending' && '⏳ Your volunteer application is pending review.'}
            {existingApp.status === 'approved' &&
              `✅ You're volunteering as ${existingApp.desired_role.replace(/_/g, ' ')}`}
            {existingApp.status === 'rejected' &&
              '❌ Your volunteer application was not approved this time.'}
          </p>
        </div>
      )}

      {/* Submitted confirmation */}
      {submitted && (
        <div className={styles.statusCard}>
          <p>✅ Application submitted! The organizer will review it.</p>
        </div>
      )}

      {/* Application form — only show if no existing app and not just submitted */}
      {!existingApp && !submitted && (
        <form onSubmit={handleSubmit} noValidate>
          <p className={styles.sectionTitle}>Select a role</p>

          <div className={styles.rolesGrid}>
            {ROLES.map((role) => {
              const slot = getSlot(role.key)
              const isFull = !slot.is_open
              const isSelected = selectedRole === role.key

              return (
                <div
                  key={role.key}
                  className={[
                    styles.roleCard,
                    isSelected ? styles.roleCardSelected : '',
                    isFull ? styles.roleCardDisabled : '',
                  ].join(' ')}
                  onClick={() => !isFull && setSelectedRole(role.key)}
                  role="button"
                  tabIndex={isFull ? -1 : 0}
                  onKeyDown={(e) => e.key === 'Enter' && !isFull && setSelectedRole(role.key)}
                  aria-pressed={isSelected}
                  aria-disabled={isFull}
                >
                  <div className={styles.roleName}>{role.label}</div>
                  <div className={styles.roleDesc}>{role.description}</div>
                  <div className={`${styles.roleSlots} ${isFull ? styles.slotsFull : styles.slotsOpen}`}>
                    {isFull
                      ? 'Full'
                      : `${slot.remaining} of ${slot.cap} spot${slot.cap !== 1 ? 's' : ''} available`}
                  </div>
                  <button
                    type="button"
                    className={`${styles.selectBtn} ${isSelected ? styles.selectBtnActive : ''}`}
                    disabled={isFull}
                    onClick={(e) => {
                      e.stopPropagation()
                      if (!isFull) setSelectedRole(role.key)
                    }}
                    aria-label={`Select ${role.label}`}
                  >
                    {isSelected ? 'Selected ✓' : isFull ? 'Full' : 'Select'}
                  </button>
                </div>
              )
            })}
          </div>

          {/* Note */}
          <div className="form-group">
            <label htmlFor="note">
              Why do you want to volunteer?{' '}
              <span style={{ color: '#9ca3af', fontWeight: 400 }}>(optional, max 200 chars)</span>
            </label>
            <textarea
              id="note"
              value={note}
              onChange={(e) => setNote(e.target.value.slice(0, 200))}
              rows={3}
              style={{
                width: '100%',
                padding: '0.55rem 0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '0.95rem',
                resize: 'vertical',
              }}
              placeholder="Tell the organizer a bit about yourself…"
            />
            <p style={{ fontSize: '0.78rem', color: '#9ca3af', textAlign: 'right' }}>
              {note.length}/200
            </p>
          </div>

          {submitError && (
            <p className="error-msg" role="alert">{submitError}</p>
          )}

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%' }}
            disabled={!selectedRole || submitting}
            data-testid="volunteer-apply-submit"
          >
            {submitting ? 'Submitting…' : 'Apply to volunteer'}
          </button>
        </form>
      )}

      <div className={styles.links}>
        <Link to={`/browse`}>← Back to events</Link>
        <Link to={`/status?event_id=${eventId}`}>View my registration</Link>
      </div>
    </div>
  )
}
