import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { eventsApi, registrationsApi } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import styles from './EventRegister.module.css'

const TSHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

export default function EventRegister() {
  const { eventId } = useParams()
  const navigate = useNavigate()

  const [event, setEvent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [serverError, setServerError] = useState(null)

  const [form, setForm] = useState({
    distance: '',
    tshirt_size: '',
    emergency_contact: '',
  })

  useEffect(() => {
    eventsApi
      .getEventDetail(eventId)
      .then((detail) => {
        if (detail.user_registration) {
          navigate(`/status?event_id=${eventId}`, { replace: true })
          return
        }
        setEvent(detail)
      })
      .catch(() => setEvent(null))
      .finally(() => setLoading(false))
  }, [eventId, navigate])

  function handleChange(e) {
    const { name, value } = e.target
    setForm((f) => ({ ...f, [name]: value }))
    setFieldErrors((fe) => ({ ...fe, [name]: undefined }))
  }

  function validate() {
    const errs = {}
    if (!form.distance) errs.distance = 'Please select a distance'
    if (!form.tshirt_size) errs.tshirt_size = 'Please select a t-shirt size'
    if (!form.emergency_contact.trim())
      errs.emergency_contact = 'Emergency contact is required'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setServerError(null)
    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }

    setSubmitting(true)
    try {
      await registrationsApi.join({
        event_id: eventId,
        distance: form.distance,
        tshirt_size: form.tshirt_size,
        emergency_contact: form.emergency_contact.trim(),
      })
      navigate(`/status?event_id=${eventId}`, {
        state: { toast: "You're registered! The organizer will review your application." },
      })
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409) {
        navigate(`/status?event_id=${eventId}`, { replace: true })
      } else {
        setServerError(typeof detail === 'string' ? detail : 'Registration failed. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <LoadingSpinner text="Loading event details…" />

  if (!event) {
    return (
      <div className="page-container">
        <p className="error-msg">Event not found.</p>
      </div>
    )
  }

  const distances = event.distances ?? []

  return (
    <div className={styles.page}>
      <div className={styles.formCard}>
        {/* Event details summary */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 className={styles.heading}>{event.name}</h1>
          <p className={styles.subheading}>
            📅 {new Date(event.event_date).toLocaleDateString(undefined, { dateStyle: 'long' })}
            {event.location && <> · 📍 {event.location}</>}
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {/* Distance Option */}
          <div className="form-group">
            <label htmlFor="distance">Choose Your Distance</label>
            <select
              id="distance"
              name="distance"
              value={form.distance}
              onChange={handleChange}
              data-testid="register-distance-select"
            >
              <option value="">— Select distance category —</option>
              {distances.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            {fieldErrors.distance && <p className="error-msg">{fieldErrors.distance}</p>}
          </div>

          {/* T-Shirt Size */}
          <div className="form-group">
            <label htmlFor="tshirt_size">Athletic T-Shirt Size</label>
            <select
              id="tshirt_size"
              name="tshirt_size"
              value={form.tshirt_size}
              onChange={handleChange}
            >
              <option value="">— Select size —</option>
              {TSHIRT_SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            {fieldErrors.tshirt_size && <p className="error-msg">{fieldErrors.tshirt_size}</p>}
          </div>

          {/* Emergency Contact */}
          <div className="form-group">
            <label htmlFor="emergency_contact">Emergency Contact Phone</label>
            <input
              id="emergency_contact"
              name="emergency_contact"
              type="tel"
              placeholder="Name — phone number"
              value={form.emergency_contact}
              onChange={handleChange}
            />
            {fieldErrors.emergency_contact && (
              <p className="error-msg">{fieldErrors.emergency_contact}</p>
            )}
          </div>

          {serverError && <p className="error-msg" role="alert">{serverError}</p>}

          <button
            type="submit"
            className="btn-primary press-effect"
            style={{ width: '100%', marginTop: '1rem' }}
            disabled={submitting}
            data-testid="event-register-submit"
          >
            {submitting ? 'Registering…' : `Confirm Registration`}
          </button>
        </form>

        <p className={styles.footerLink}>
          <Link to="/browse">← Back to events list</Link>
        </p>
      </div>
    </div>
  )
}
