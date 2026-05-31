import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import styles from './Landing.module.css'

const FEATURES = [
  {
    icon: '🏁',
    title: 'Event Registration',
    desc: 'Participants browse upcoming races, register in seconds, and track their status through every stage.',
  },
  {
    icon: '📋',
    title: 'Organizer Dashboard',
    desc: 'Approve registrations, auto-assign BIB numbers, manage tasks, and broadcast notifications — all in one place.',
  },
  {
    icon: '📷',
    title: 'QR-Based Check-in',
    desc: 'Volunteers scan participant QR codes at the registration desk to mark BIB collection instantly.',
  },
  {
    icon: '⏱',
    title: 'Finish Line Timing',
    desc: 'Finish-line volunteers record times by scanning QR codes. Certificates are generated and emailed automatically.',
  },
  {
    icon: '🙋',
    title: 'Volunteer Management',
    desc: 'Participants apply to volunteer for specific roles. Organizers approve with slot-cap enforcement.',
  },
  {
    icon: '🏅',
    title: 'Digital Certificates',
    desc: 'Completion certificates are auto-generated as PDFs and emailed with the finish time as an attachment.',
  },
]

const FLOW = [
  { step: '01', label: 'Sign Up', desc: 'Create your account in under a minute.' },
  { step: '02', label: 'Browse Events', desc: 'Find upcoming races and register for your distance.' },
  { step: '03', label: 'Get Approved', desc: 'Organizer reviews and assigns your BIB number.' },
  { step: '04', label: 'Confirm & Show Up', desc: 'Confirm participation, show your QR at the desk.' },
  { step: '05', label: 'Run & Finish', desc: 'Cross the line — your time is recorded on the spot.' },
  { step: '06', label: 'Get Your Certificate', desc: 'PDF certificate lands in your inbox automatically.' },
]

export default function Landing() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuth()

  function handleCta() {
    if (isAuthenticated) {
      if (user?.role === 'organizer') navigate('/organizer')
      else if (user?.role === 'admin') navigate('/admin')
      else navigate('/browse')
    } else {
      navigate('/signup')
    }
  }

  return (
    <div className={styles.page}>

      {/* ── Hero ── */}
      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <div className={styles.heroTag}>🏃 Marathon Management Platform</div>
          <h1 className={styles.heroTitle}>
            Run the race.<br />
            <span className={styles.heroAccent}>We handle the rest.</span>
          </h1>
          <p className={styles.heroSub}>
            End-to-end marathon management — from registration and BIB assignment
            to finish-line timing and digital certificates.
          </p>
          <div className={styles.heroCta}>
            <button className="btn-primary btn-lg press-effect" onClick={handleCta}>
              {isAuthenticated ? 'Go to Dashboard →' : 'Get Started Free →'}
            </button>
            <button
              className="btn-secondary btn-lg press-effect"
              onClick={() => navigate('/browse')}
            >
              Browse Events
            </button>
          </div>
        </div>

        {/* Decorative stat pills */}
        <div className={styles.heroStats}>
          {[
            { n: '5', label: 'Stages' },
            { n: '∞', label: 'Events' },
            { n: '100%', label: 'Automated' },
          ].map((s) => (
            <div key={s.label} className={styles.statPill}>
              <span className={styles.statNum}>{s.n}</span>
              <span className={styles.statLabel}>{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className={styles.section}>
        <div className={styles.sectionHead}>
          <h2>Everything you need to run a great race</h2>
          <p>Built for organizers, participants, and volunteers — all in one platform.</p>
        </div>
        <div className={styles.featureGrid}>
          {FEATURES.map((f) => (
            <div key={f.title} className={`card ${styles.featureCard}`}>
              <span className={styles.featureIcon}>{f.icon}</span>
              <h3 className={styles.featureTitle}>{f.title}</h3>
              <p className={styles.featureDesc}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className={`${styles.section} ${styles.sectionAlt}`}>
        <div className={styles.sectionHead}>
          <h2>How it works</h2>
          <p>Six steps from sign-up to certificate — fully automated.</p>
        </div>
        <div className={styles.flowGrid}>
          {FLOW.map((f, i) => (
            <div key={f.step} className={styles.flowStep}>
              <div className={styles.flowNum}>{f.step}</div>
              {i < FLOW.length - 1 && <div className={styles.flowLine} />}
              <div className={styles.flowContent}>
                <h4 className={styles.flowLabel}>{f.label}</h4>
                <p className={styles.flowDesc}>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Roles ── */}
      <section className={styles.section}>
        <div className={styles.sectionHead}>
          <h2>Built for every role</h2>
          <p>One platform, three perspectives.</p>
        </div>
        <div className={styles.rolesGrid}>
          {[
            {
              role: 'Participant',
              icon: '🏃',
              color: '#4f46e5',
              points: [
                'Register for any event in seconds',
                'Track your status through 5 stages',
                'View your QR code and BIB number',
                'Confirm participation and get your certificate',
              ],
              cta: 'Sign up as participant',
              action: () => navigate('/signup'),
            },
            {
              role: 'Organizer',
              icon: '📋',
              color: '#e8450a',
              points: [
                'Create and manage events',
                'Approve registrations & auto-assign BIBs',
                'Manage tasks and broadcast notifications',
                'Upload finish times via CSV or inline',
              ],
              cta: 'Request organizer access',
              action: () => navigate('/login'),
            },
            {
              role: 'Volunteer',
              icon: '🙋',
              color: '#16a34a',
              points: [
                'Apply to volunteer for specific roles',
                'Scan QR codes at the registration desk',
                'Record finish times at the finish line',
                'View your event assignment',
              ],
              cta: 'Apply to volunteer',
              action: () => navigate('/browse'),
            },
          ].map((r) => (
            <div key={r.role} className={`card ${styles.roleCard}`} style={{ borderTop: `4px solid ${r.color}` }}>
              <div className={styles.roleHeader}>
                <span className={styles.roleIcon}>{r.icon}</span>
                <h3 className={styles.roleTitle}>{r.role}</h3>
              </div>
              <ul className={styles.rolePoints}>
                {r.points.map((p) => (
                  <li key={p} className={styles.rolePoint}>
                    <span style={{ color: r.color }}>✓</span> {p}
                  </li>
                ))}
              </ul>
              <button
                className="btn-secondary btn-sm"
                style={{ marginTop: '1rem', width: '100%' }}
                onClick={r.action}
              >
                {r.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className={styles.bottomCta}>
        <div className={styles.bottomCtaInner}>
          <h2>Ready to organise your next race?</h2>
          <p>Join the platform that handles everything from registration to certificates.</p>
          <div className={styles.heroCta} style={{ justifyContent: 'center' }}>
            <button className="btn-primary btn-lg press-effect" onClick={handleCta}>
              {isAuthenticated ? 'Go to Dashboard →' : 'Get Started Free →'}
            </button>
            <button className="btn-secondary btn-lg press-effect" onClick={() => navigate('/browse')}>
              View Events
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <p>© {new Date().getFullYear()} Marathon Management Platform · Built with ❤️ for runners</p>
      </footer>
    </div>
  )
}
