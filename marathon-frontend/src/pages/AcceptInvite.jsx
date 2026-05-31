import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import client from '../api/client.js'
import styles from './AcceptInvite.module.css'

export default function AcceptInvite() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const navigate = useNavigate()
  const { login } = useAuth()

  const [form, setForm] = useState({ name: '', password: '', confirm: '' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
    setError(null)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    if (!form.name.trim()) { setError('Full name is required'); return }
    if (form.password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (form.password !== form.confirm) { setError('Passwords do not match'); return }

    setLoading(true)
    try {
      const data = await client.post('/auth/accept-invite', {
        token,
        name: form.name.trim(),
        password: form.password,
      }).then((r) => r.data)
      login(data.access_token, data.user)
      setSuccess(true)
      setTimeout(() => navigate('/organizer/events', { replace: true }), 1500)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to accept invite')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>

      {/* Left panel — branding */}
      <div className={styles.left}>
        <div className={styles.leftInner}>
          <div className={styles.brand}>🏃 Marathon Platform</div>
          <h2 className={styles.leftTitle}>You're invited to be an organizer</h2>
          <p className={styles.leftSub}>
            Create your account to start managing events, approving registrations,
            and running world-class races.
          </p>
          <div className={styles.perks}>
            {[
              { icon: '📋', text: 'Manage registrations & BIB assignment' },
              { icon: '📣', text: 'Broadcast notifications to participants' },
              { icon: '⏱', text: 'Upload finish times & generate certificates' },
              { icon: '🙋', text: 'Approve volunteer applications' },
            ].map((p) => (
              <div key={p.text} className={styles.perk}>
                <span className={styles.perkIcon}>{p.icon}</span>
                <span className={styles.perkText}>{p.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className={styles.right}>
        <div className={styles.formBox}>

          {!token ? (
            <div className={styles.errorState}>
              <span className={styles.errorIcon}>⚠️</span>
              <h3>Invalid invite link</h3>
              <p>This link is missing the invite token. Please use the exact link from your invitation email.</p>
            </div>
          ) : success ? (
            <div className={styles.successState}>
              <span className={styles.successIcon}>✅</span>
              <h3>Account created!</h3>
              <p>Redirecting you to the organizer dashboard…</p>
            </div>
          ) : (
            <>
              <div className={styles.formHeader}>
                <h1 className={styles.formTitle}>Create your account</h1>
                <p className={styles.formSub}>Set up your organizer profile to get started.</p>
              </div>

              <form onSubmit={handleSubmit} noValidate className={styles.form}>
                <div className="form-group">
                  <label htmlFor="name">Full name</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    autoComplete="name"
                    required
                    placeholder="Your full name"
                    value={form.name}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="password">Password</label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    placeholder="Min. 8 characters"
                    value={form.password}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="confirm">Confirm password</label>
                  <input
                    id="confirm"
                    name="confirm"
                    type="password"
                    autoComplete="new-password"
                    required
                    placeholder="Repeat your password"
                    value={form.confirm}
                    onChange={handleChange}
                  />
                </div>

                {error && (
                  <div className={styles.errorBanner} role="alert">
                    ⚠️ {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="btn-primary"
                  style={{ width: '100%', marginTop: '0.5rem' }}
                  disabled={loading}
                >
                  {loading ? 'Creating account…' : 'Create organizer account →'}
                </button>
              </form>

              <p className={styles.footNote}>
                Already have an account?{' '}
                <button
                  className="btn-ghost btn-sm"
                  style={{ padding: '0 0.25rem' }}
                  onClick={() => navigate('/login')}
                >
                  Sign in
                </button>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
