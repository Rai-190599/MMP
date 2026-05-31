import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { eventsApi } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import styles from './EventLanding.module.css'

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID

export default function EventLanding() {
  const { eventId: paramEventId } = useParams()
  const eventId = paramEventId || DEFAULT_EVENT_ID
  const navigate = useNavigate()

  const [event, setEvent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [openFaq, setOpenFaq] = useState(null)

  useEffect(() => {
    if (!eventId) {
      setError('No event ID configured.')
      setLoading(false)
      return
    }
    eventsApi
      .getEvent(eventId)
      .then(setEvent)
      .catch(() => setError('Event not found.'))
      .finally(() => setLoading(false))
  }, [eventId])

  if (loading) return <LoadingSpinner text="Loading event details…" />
  if (error) return <div className="page-container"><p className="error-msg">{error}</p></div>

  const faqItems = Array.isArray(event.faq) ? event.faq : []
  const distances = Array.isArray(event.distances) ? event.distances : []
  const sponsors = event.sponsor_tiers ? Object.entries(event.sponsor_tiers) : []

  const eventDate = new Date(event.event_date)
  const daysUntil = Math.ceil((eventDate - new Date()) / (1000 * 60 * 60 * 24))

  return (
    <div className={styles.page}>
      {/* Clean kinetic typography hero */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <div className={styles.heroTag}>
            <span>🏃</span> UPCOMING RACE
          </div>
          <h1 className={styles.title}>{event.name}</h1>
          <div className={styles.heroMeta}>
            <div className={styles.metaItem}>
              <span className={styles.metaIcon}>📅</span>
              <span>
                {eventDate.toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </span>
            </div>
            {event.location && (
              <div className={styles.metaItem}>
                <span className={styles.metaIcon}>📍</span>
                <span>{event.location}</span>
              </div>
            )}
          </div>

          {daysUntil > 0 && (
            <div className={styles.countdown}>
              <div className={styles.countdownItem}>
                <span className={styles.countdownNumber}>{daysUntil}</span>
                <span className={styles.countdownLabel}>days to go</span>
              </div>
            </div>
          )}

          <div className={styles.heroCta}>
            <button
              className="btn-primary press-effect"
              onClick={() => navigate('/register')}
              data-testid="register-cta-button"
            >
              Register Now →
            </button>
            <button
              className="btn-secondary press-effect"
              onClick={() => {
                document.getElementById('distances')?.scrollIntoView({ behavior: 'smooth' })
              }}
            >
              Learn More ↓
            </button>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className={styles.statsBar}>
        {distances.length > 0 && (
          <div className={styles.stat}>
            <span className={styles.statNumber}>{distances.length}</span>
            <span className={styles.statLabel}>Distance Options</span>
          </div>
        )}
        <div className={styles.stat}>
          <span className={styles.statNumber}>
            {sponsors.length > 0
              ? sponsors.reduce((acc, [, v]) => acc + (Array.isArray(v) ? v.length : 1), 0)
              : '12'}
          </span>
          <span className={styles.statLabel}>Sponsors</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statNumber}>2,400+</span>
          <span className={styles.statLabel}>Expected Runners</span>
        </div>
      </section>

      {/* Distances */}
      {distances.length > 0 && (
        <section id="distances" className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Choose Your Challenge</h2>
            <p className={styles.sectionSub}>Find the perfect challenge for your running goals</p>
          </div>
          <div className={styles.distanceGrid}>
            {distances.map((d) => (
              <div key={d} className={styles.distanceCard}>
                <span className={styles.distanceEmoji}>
                  {d.includes('5')
                    ? '🏃'
                    : d.includes('10')
                      ? '🏃‍♂️'
                      : d.includes('21') || d.includes('half')
                        ? '⚡'
                        : d.includes('42') || d.includes('full')
                          ? '🏆'
                          : '🏁'}
                </span>
                <span className={styles.distanceValue}>{d}</span>
                <span className={styles.distanceLabel}>
                  {d.includes('5')
                    ? 'Fun Run'
                    : d.includes('10')
                      ? '10K Challenge'
                      : d.includes('21')
                        ? 'Half Marathon'
                        : d.includes('42')
                          ? 'Full Marathon'
                          : 'Official Distance'}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Sponsors */}
      {sponsors.length > 0 && (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Event Partners</h2>
            <p className={styles.sectionSub}>Proudly supported by top athletic brands</p>
          </div>
          <div className={styles.sponsorList}>
            {sponsors.map(([tier, names]) => (
              <div key={tier} className={styles.sponsorTier}>
                <span className={styles.tierLabel}>{tier}</span>
                <div className={styles.tierNames}>
                  {(Array.isArray(names) ? names : [String(names)]).map((name, i) => (
                    <span key={i} className={styles.sponsorName}>
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* FAQ */}
      {faqItems.length > 0 && (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Frequently Asked Questions</h2>
            <p className={styles.sectionSub}>Everything you need to know about the race day</p>
          </div>
          <div className={styles.faqList}>
            {faqItems.map((item, i) => (
              <div
                key={i}
                className={`${styles.faqItem} ${openFaq === i ? styles.faqItemOpen : ''}`}
              >
                <button
                  className={styles.faqQuestion}
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  aria-expanded={openFaq === i}
                  data-testid={`faq-item-${i}`}
                >
                  <span>{item.question || item.q}</span>
                  <span className={styles.faqChevron}>{openFaq === i ? '−' : '+'}</span>
                </button>
                <div
                  className={styles.faqAnswerWrap}
                  style={{
                    maxHeight: openFaq === i ? '300px' : '0',
                    opacity: openFaq === i ? 1 : 0,
                  }}
                >
                  <p className={styles.faqAnswer}>{item.answer || item.a}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Bottom CTA */}
      <section className={styles.bottomCta}>
        <div className={styles.bottomCtaContent}>
          <h2 className={styles.bottomCtaTitle}>Ready to Run?</h2>
          <p className={styles.bottomCtaSub}>
            Join thousands of runners in one of the premier athletic events of the year.
          </p>
          <button
            className="btn-primary press-effect"
            onClick={() => navigate('/register')}
          >
            Register Now →
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>© {new Date().getFullYear()} Marathon Platform. All rights reserved.</p>
      </footer>
    </div>
  )
}
