import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { registrationsApi, volunteerApi } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import StatusTracker from '../components/StatusTracker.jsx'
import { useAuth } from '../hooks/useAuth.js'
import styles from './ParticipantStatus.module.css'

const EVENT_ID = import.meta.env.VITE_EVENT_ID
const CERT_POLL_INTERVAL_MS = 5000

// Statuses eligible to volunteer
const VOLUNTEER_ELIGIBLE_STATUSES = [
  'approved',
  'participation_confirmed',
  'bib_collected',
  'finished_certified',
]

export default function ParticipantStatus() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const eventId = searchParams.get('event_id') || EVENT_ID

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [confirmMsg, setConfirmMsg] = useState(null)

  // Certificate state
  const [certUrl, setCertUrl] = useState(null)
  const [certGenerating, setCertGenerating] = useState(false)
  const pollRef = useRef(null)

  // Volunteer application state
  const [volunteerApp, setVolunteerApp] = useState(undefined)

  useEffect(() => {
    registrationsApi
      .getMyStatus(eventId)
      .then((d) => {
        setData(d)
        if (d.status === 'finished_certified') {
          fetchCertificate(d.id)
        }
      })
      .catch(() => setError('Could not load registration status.'))
      .finally(() => setLoading(false))

    return () => clearInterval(pollRef.current)
  }, [eventId])

  useEffect(() => {
    if (!data || !eventId) return
    if (!VOLUNTEER_ELIGIBLE_STATUSES.includes(data.status)) {
      setVolunteerApp(null)
      return
    }
    volunteerApi
      .getMyApplications({ event_id: eventId })
      .then((apps) => setVolunteerApp(apps?.[0] ?? null))
      .catch(() => setVolunteerApp(null))
  }, [data, eventId])

  function fetchCertificate(registrationId) {
    registrationsApi
      .getCertificate(registrationId)
      .then((res) => {
        if (res.status === 200 && res.download_url) {
          setCertUrl(res.download_url)
          setCertGenerating(false)
          clearInterval(pollRef.current)
          pollRef.current = null
        } else {
          setCertGenerating(true)
          if (!pollRef.current) {
            pollRef.current = setInterval(
              () => fetchCertificate(registrationId),
              CERT_POLL_INTERVAL_MS
            )
          }
        }
      })
      .catch(() => {
        setCertGenerating(false)
        clearInterval(pollRef.current)
        pollRef.current = null
      })
  }

  async function handleConfirm() {
    setConfirming(true)
    setConfirmMsg(null)
    try {
      const updated = await registrationsApi.confirm(eventId)
      setData(updated)
      setConfirmMsg('Participation confirmed! Check your WhatsApp for the group invite.')
    } catch (err) {
      setConfirmMsg(err?.response?.data?.detail || 'Confirmation failed.')
    } finally {
      setConfirming(false)
    }
  }

  if (loading) return <LoadingSpinner text="Loading registration status…" />
  if (error) return <div className={styles.page}><p className="error-msg">{error}</p></div>
  if (!data) return null

  const regStatus = data.status
  const isApproved = regStatus === 'approved'
  const isCertified = regStatus === 'finished_certified'
  const hasBib = VOLUNTEER_ELIGIBLE_STATUSES.includes(regStatus)
  const greetingName = user?.name ? user.name.split(' ')[0] : 'Runner'

  return (
    <div className={styles.page}>
      {/* Top Greeting Section */}
      <div className={styles.greetingBox}>
        <h1 className={styles.greeting}>Hey, {greetingName} 👋</h1>
        <p className={styles.subGreeting}>Track your registration details and event status below.</p>
      </div>

      {/* Stage Tracker card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className={styles.stageHeader}>
          <span className={styles.stageLabel}>YOUR PROGRESS</span>
          <span className={`badge badge-${regStatus}`}>{regStatus.replace(/_/g, ' ')}</span>
        </div>
        <StatusTracker currentStage={data.current_stage} stages={data.stages} />
      </div>

      {/* BIB Card designed like a physical Bib */}
      {hasBib && data.bib_number && (
        <div className={styles.bibCard}>
          {/* Top orange strip */}
          <div className={styles.bibTopStrip} />
          <div className={styles.bibInner}>
            <span className={styles.bibEventLabel}>MARATHON BIB</span>
            <div className={styles.bibNumber} data-testid="bib-number">
              {data.bib_number}
            </div>
            <span className={styles.bibRunnerName}>{user?.name || 'ATHLETE'}</span>

            {/* Perforation line */}
            <div className={styles.bibPerforation} />

            {data.id && <QrSection registrationId={data.id} />}
          </div>
        </div>
      )}

      {/* Confirm participation banner (Stage 2) */}
      {isApproved && (
        <div className={`card ${styles.actionCard} card-accent-primary`}>
          <h3 className={styles.detailsTitle}>Participation Confirmation Required</h3>
          <p className={styles.actionMessage}>
            Congratulations! Your registration has been approved. Please confirm your participation now to lock in your race slot and receive WhatsApp updates.
          </p>
          <button
            className="btn-primary press-effect"
            style={{ width: '100%' }}
            onClick={handleConfirm}
            disabled={confirming}
            data-testid="confirm-participation-button"
          >
            {confirming ? 'Confirming Spot…' : 'Confirm Participation'}
          </button>
          {confirmMsg && (
            <p className={confirmMsg.includes('failed') ? 'error-msg' : 'success-msg'}>
              {confirmMsg}
            </p>
          )}
        </div>
      )}

      {/* Finisher certificate download banner (Stage 5) */}
      {isCertified && (
        <div className={`card ${styles.actionCard} card-accent-success`}>
          <h3 className={styles.detailsTitle}>🎉 Finisher Certificate Ready!</h3>
          <p className={styles.actionMessage}>
            Incredible job finishing the marathon! You can download your official finisher certificate below.
          </p>

          {certGenerating && (
            <div className={styles.progressContainer}>
              <div className={styles.progressBar}>
                <div className={styles.progressFill} />
              </div>
              <p className={styles.progressText}>Generating your finisher certificate...</p>
            </div>
          )}

          {certUrl && (
            <a
              href={certUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-success press-effect"
              style={{ display: 'flex', textDecoration: 'none', justifyContent: 'center' }}
              data-testid="download-certificate-button"
            >
              Download Finisher Certificate 📥
            </a>
          )}
        </div>
      )}

      {/* Details list card */}
      <div className={`card ${styles.detailsCard}`}>
        <h3 className={styles.detailsTitle}>Registration Details</h3>
        <dl className={styles.dl}>
          <dt>Status</dt>
          <dd>
            <span className={`badge badge-${regStatus}`}>{regStatus.replace(/_/g, ' ')}</span>
          </dd>
          {data.distance && (
            <>
              <dt>Distance</dt>
              <dd>{data.distance}</dd>
            </>
          )}
          {data.tshirt_size && (
            <>
              <dt>T-Shirt Size</dt>
              <dd>{data.tshirt_size.toUpperCase()}</dd>
            </>
          )}
          {data.finish_time && (
            <>
              <dt>Finish Time</dt>
              <dd style={{ fontFamily: 'var(--font-mono)' }}>
                {new Date(data.finish_time).toLocaleString()}
              </dd>
            </>
          )}
        </dl>
      </div>

      {/* Volunteer application footer action */}
      {VOLUNTEER_ELIGIBLE_STATUSES.includes(regStatus) && (
        <div className={`card ${styles.volunteerCard}`}>
          <h3 className={styles.volunteerTitle}>Want to give back?</h3>
          <p className={styles.volunteerSubtext}>
            Volunteer at this event and help fellow runners reach their milestone.
          </p>

          {volunteerApp === undefined && <p style={{ fontSize: '0.875rem' }}>Checking application…</p>}

          {volunteerApp === null && (
            <Link
              to={`/events/${eventId}/volunteer`}
              className="btn-ghost press-effect"
              style={{ display: 'inline-flex', padding: 0 }}
            >
              Apply to volunteer →
            </Link>
          )}

          {volunteerApp?.status === 'pending' && (
            <span className="badge badge-bib-collected badge-dot">
              Volunteer application pending review
            </span>
          )}

          {volunteerApp?.status === 'approved' && (
            <span className="badge badge-certified badge-dot">
              Assigned Volunteer Role: {volunteerApp.desired_role.replace(/_/g, ' ')}
            </span>
          )}

          {volunteerApp?.status === 'rejected' && (
            <span className="badge badge-registered">
              Volunteer application completed
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function QrSection({ registrationId }) {
  const [qrUrl, setQrUrl] = useState(null)

  useEffect(() => {
    registrationsApi
      .getQrUrl(registrationId)
      .then(({ qr_url }) => setQrUrl(qr_url))
      .catch(() => {})
  }, [registrationId])

  if (!qrUrl) return null

  return (
    <div className={styles.qrContainer}>
      <p className={styles.qrSubtext}>Show this at the registration desk on race day</p>
      <img
        src={qrUrl}
        alt="Registration QR Code"
        className={styles.qrImage}
        data-testid="qr-code-image"
      />
      <a href={qrUrl} download="race-bib-qr.png" className={styles.qrLink}>
        Download QR
      </a>
    </div>
  )
}
