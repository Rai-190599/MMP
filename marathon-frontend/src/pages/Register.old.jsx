import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client.js'
import { useAuth } from '../hooks/useAuth.js'
import styles from './AuthForm.module.css'

const DISTANCES = ['5K', '10K', '21K', '42K']
const TSHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const EVENT_ID = import.meta.env.VITE_EVENT_ID

export default function Register() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
    role: 'participant',
    distance: '',
    tshirt_size: '',
    emergency_contact: '',
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
    if (!form.name.trim()) errs.name = 'Name is required'
    if (!form.email.trim()) errs.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Invalid email'
    if (!form.password) errs.password = 'Password is required'
    else if (form.password.length < 6) errs.password = 'Minimum 6 characters'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setServerError(null)
    const errs = validate()
    if (Object.keys(errs).length) { setFieldErrors(errs); return }

    setLoading(true)
    try {
      const payload = {
        name: form.name,
        email: form.email,
        phone: form.phone || undefined,
        password: form.password,
        role: form.role,
      }
      if (form.role === 'participant') {
        if (form.distance) payload.distance = form.distance
        if (form.tshirt_size) payload.tshirt_size = form.tshirt_size
        if (form.emergency_contact) payload.emergency_contact = form.emergency_contact
        if (EVENT_ID) payload.event_id = EVENT_ID
      }

      const data = await authApi.register(payload)
      login(data.access_token, data.user)
      const role = data.user?.role
      if (role === 'organizer') navigate('/organizer')
      else if (role === 'volunteer') navigate('/volunteer/scanner')
      else navigate('/status')
    } catch (err) {
      const detail = err?.response?.data?.detail
      setServerError(typeof detail === 'string' ? detail : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const isParticipant = form.role === 'participant'

  return (
    <div className={styles.page}>
      <div className={`card ${styles.formCard}`}>
        <h1 className={styles.heading}>Create account</h1>

        <form onSubmit={handleSubmit} noValidate>
          {/* Role */}
          <div className="form-group">
            <label>I am a</label>
            <div className={styles.radioGroup}>
              {['participant', 'volunteer'].map((r) => (
                <label key={r} className={styles.radioLabel}>
                  <input
                    type="radio"
                    name="role"
                    value={r}
                    checked={form.role === r}
                    onChange={handleChange}
                    data-testid={`role-${r}`}
                  />
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </label>
              ))}
            </div>
          </div>

          {/* Name */}
          <div className="form-group">
            <label htmlFor="name">Full name</label>
            <input id="name" name="name" value={form.name} onChange={handleChange} data-testid="register-name-input" />
            {fieldErrors.name && <p className="error-msg">{fieldErrors.name}</p>}
          </div>

          {/* Email */}
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" value={form.email} onChange={handleChange} data-testid="register-email-input" />
            {fieldErrors.email && <p className="error-msg">{fieldErrors.email}</p>}
          </div>

          {/* Phone */}
          <div className="form-group">
            <label htmlFor="phone">Phone <span style={{ color: '#9ca3af' }}>(optional)</span></label>
            <input id="phone" name="phone" type="tel" value={form.phone} onChange={handleChange} />
          </div>

          {/* Password */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" name="password" type="password" value={form.password} onChange={handleChange} data-testid="register-password-input" />
            {fieldErrors.password && <p className="error-msg">{fieldErrors.password}</p>}
          </div>

          {/* Participant-only fields */}
          {isParticipant && (
            <>
              <div className="form-group">
                <label htmlFor="distance">Distance</label>
                <select id="distance" name="distance" value={form.distance} onChange={handleChange} data-testid="register-distance-select">
                  <option value="">— Select distance —</option>
                  {DISTANCES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="tshirt_size">T-shirt size</label>
                <select id="tshirt_size" name="tshirt_size" value={form.tshirt_size} onChange={handleChange}>
                  <option value="">— Select size —</option>
                  {TSHIRT_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="emergency_contact">Emergency contact <span style={{ color: '#9ca3af' }}>(optional)</span></label>
                <input id="emergency_contact" name="emergency_contact" value={form.emergency_contact} onChange={handleChange} placeholder="Name — phone number" />
              </div>
            </>
          )}

          {serverError && <p className="error-msg" role="alert">{serverError}</p>}

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', marginTop: '0.5rem' }}
            disabled={loading}
            data-testid="register-submit-button"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className={styles.footer}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
