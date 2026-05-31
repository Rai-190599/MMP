import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client.js'
import { useAuth } from '../hooks/useAuth.js'
import styles from './AuthForm.module.css'

export default function Signup() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [serverError, setServerError] = useState(null)
  const [loading, setLoading] = useState(false)

  function handleChange(e) {
    const { name, value } = e.target
    setForm((f) => ({ ...f, [name]: value }))
    setFieldErrors((fe) => ({ ...fe, [name]: undefined }))
  }

  function validate() {
    const errs = {}
    if (!form.name.trim() || form.name.trim().length < 3)
      errs.name = 'Name must be at least 3 characters'
    if (!form.email.trim()) errs.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Invalid email address'
    if (!form.phone.trim() || form.phone.replace(/\D/g, '').length < 10)
      errs.phone = 'Phone must be at least 10 digits'
    if (!form.password) errs.password = 'Password is required'
    else if (form.password.length < 8) errs.password = 'Password must be at least 8 characters'
    if (!form.confirmPassword) errs.confirmPassword = 'Please confirm your password'
    else if (form.password !== form.confirmPassword) errs.confirmPassword = 'Passwords do not match'
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

    setLoading(true)
    try {
      const data = await authApi.signup({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        password: form.password,
      })
      login(data.access_token, data.user)
      navigate('/browse', {
        state: { toast: 'Account created! Browse events below.' },
      })
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409) {
        setFieldErrors((fe) => ({ ...fe, email: 'This email is already registered' }))
      } else {
        setServerError(typeof detail === 'string' ? detail : 'Sign up failed. Please try again.')
      }
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
            <h2 className={styles.heading}>Create your account</h2>
            <p className={styles.headingSub}>Join thousands of runners pushing their limits</p>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="name">Full name</label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                placeholder="Enter full name"
                value={form.name}
                onChange={handleChange}
                className={fieldErrors.name ? 'error' : ''}
                data-testid="signup-name-input"
              />
              {fieldErrors.name && <p className="error-msg">{fieldErrors.name}</p>}
            </div>

            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={handleChange}
                className={fieldErrors.email ? 'error' : ''}
                data-testid="signup-email-input"
              />
              {fieldErrors.email && <p className="error-msg">{fieldErrors.email}</p>}
            </div>

            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="phone">Phone number</label>
              <input
                id="phone"
                name="phone"
                type="tel"
                autoComplete="tel"
                placeholder="Enter phone number"
                value={form.phone}
                onChange={handleChange}
                className={fieldErrors.phone ? 'error' : ''}
                data-testid="signup-phone-input"
              />
              {fieldErrors.phone && <p className="error-msg">{fieldErrors.phone}</p>}
            </div>

            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                placeholder="At least 8 characters"
                value={form.password}
                onChange={handleChange}
                className={fieldErrors.password ? 'error' : ''}
                data-testid="signup-password-input"
              />
              {fieldErrors.password && <p className="error-msg">{fieldErrors.password}</p>}
            </div>

            <div className={`${styles.animatedField} form-group`}>
              <label htmlFor="confirmPassword">Confirm password</label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                placeholder="Confirm password"
                value={form.confirmPassword}
                onChange={handleChange}
                className={fieldErrors.confirmPassword ? 'error' : ''}
                data-testid="signup-confirm-password-input"
              />
              {fieldErrors.confirmPassword && (
                <p className="error-msg">{fieldErrors.confirmPassword}</p>
              )}
            </div>

            {serverError && (
              <div className={styles.animatedField}>
                <p className="error-msg" role="alert">{serverError}</p>
              </div>
            )}

            <div className={styles.animatedField} style={{ marginTop: '1.5rem' }}>
              <button
                type="submit"
                className="btn-primary press-effect"
                style={{ width: '100%' }}
                disabled={loading}
                data-testid="signup-submit-button"
              >
                {loading ? 'Creating profile…' : 'Create account'}
              </button>
            </div>
          </form>

          <p className={styles.footer}>
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
