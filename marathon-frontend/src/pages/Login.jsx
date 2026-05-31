import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client.js'
import { useAuth } from '../hooks/useAuth.js'
import styles from './AuthForm.module.css'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await authApi.login(form)
      login(data.access_token, data.user)
      const role = data.user?.role
      if (role === 'admin') navigate('/admin')
      else if (role === 'organizer') navigate('/organizer/events')
      else navigate('/browse')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      {/* Left panel (40% width, hidden on mobile) */}
      <div className={styles.leftPanel}>
        <div className={styles.leftContent}>
          <h1 className={styles.visualTitle}>
            Run Your<br />Race.
          </h1>
          <p className={styles.visualSub}>
            Track your journey from registration to the finish line.
          </p>
        </div>
        <div className={styles.statsBar}>
          <div className={styles.statItem}>
            <span className={styles.statNum}>2,400+</span>
            <span className={styles.statLabel}>runners</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statNum}>12</span>
            <span className={styles.statLabel}>events</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statNum}>98%</span>
            <span className={styles.statLabel}>completion rate</span>
          </div>
        </div>
      </div>

      {/* Right panel (60% width) */}
      <div className={styles.rightPanel}>
        <div className={styles.formCard}>
          <div className={styles.logoHeader} onClick={() => navigate('/')}>
            Marathon <span className={styles.logoDot} />
          </div>

          <div className={styles.titleArea}>
            <h2 className={styles.heading}>Welcome back</h2>
            <p className={styles.headingSub}>Sign in to your runner profile to continue</p>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@example.com"
                value={form.email}
                onChange={handleChange}
                data-testid="login-email-input"
              />
            </div>

            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                placeholder="Enter password"
                value={form.password}
                onChange={handleChange}
                data-testid="login-password-input"
              />
            </div>

            {error && (
              <div className={styles.animatedField}>
                <p className="error-msg" role="alert">{error}</p>
              </div>
            )}

            <div className={styles.animatedField} style={{ marginTop: '1.5rem' }}>
              <button
                type="submit"
                className="btn-primary press-effect"
                style={{ width: '100%' }}
                disabled={loading}
                data-testid="login-submit-button"
              >
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </div>
          </form>

          <p className={styles.footer}>
            No account? <Link to="/signup">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
