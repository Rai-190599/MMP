import { useEffect, useRef, useState } from 'react'
import client from '../../api/client.js'
import { eventsManagementApi } from '../../api/client.js'

const EMPTY_FORM = { name: '', event_date: '', location: '', distances: '', is_active: true }

export default function OrganizerEvents() {
  const [events, setEvents] = useState([])
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState(null)

  // Banner state per event: { [eventId]: { uploading, error } }
  const [bannerState, setBannerState] = useState({})
  const fileInputRefs = useRef({})

  async function fetchEvents() {
    try {
      const data = await client.get('/manage/events/').then((r) => r.data)
      setEvents(data)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load events')
    }
  }

  useEffect(() => { fetchEvents() }, [])

  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setShowModal(true)
  }

  function openEdit(ev) {
    setEditing(ev)
    setForm({
      name: ev.name,
      event_date: ev.event_date,
      location: ev.location || '',
      distances: (ev.distances || []).join(', '),
      is_active: ev.is_active,
    })
    setFormError(null)
    setShowModal(true)
  }

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError(null)
    setSaving(true)
    const payload = {
      name: form.name,
      event_date: form.event_date,
      location: form.location,
      distances: form.distances.split(',').map((d) => d.trim()).filter(Boolean),
      is_active: form.is_active,
    }
    try {
      if (editing) {
        await client.patch(`/manage/events/${editing.id}`, payload)
      } else {
        await client.post('/manage/events/', payload)
      }
      setShowModal(false)
      fetchEvents()
    } catch (err) {
      setFormError(err?.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleBannerUpload(eventId, file) {
    if (!file) return
    setBannerState((s) => ({ ...s, [eventId]: { uploading: true, error: null } }))
    try {
      await eventsManagementApi.uploadBanner(eventId, file)
      await fetchEvents()
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Upload failed'
      setBannerState((s) => ({ ...s, [eventId]: { uploading: false, error: msg } }))
      return
    }
    setBannerState((s) => ({ ...s, [eventId]: { uploading: false, error: null } }))
    // Reset file input
    if (fileInputRefs.current[eventId]) fileInputRefs.current[eventId].value = ''
  }

  async function handleBannerDelete(eventId, index) {
    setBannerState((s) => ({ ...s, [eventId]: { uploading: true, error: null } }))
    try {
      await eventsManagementApi.deleteBanner(eventId, index)
      await fetchEvents()
    } catch (err) {
      setBannerState((s) => ({ ...s, [eventId]: { uploading: false, error: err?.response?.data?.detail || 'Delete failed' } }))
      return
    }
    setBannerState((s) => ({ ...s, [eventId]: { uploading: false, error: null } }))
  }

  return (
    <div style={{ padding: '2rem', maxWidth: 900, margin: '0 auto', minHeight: 'calc(100vh - 56px)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>My Events</h1>
        <button className="btn-primary" onClick={openCreate}>+ Create event</button>
      </div>

      {error && <p className="error-msg">{error}</p>}
      {events.length === 0 && !error && <p>No events yet. Create your first event.</p>}

      <div style={{ display: 'grid', gap: '1.5rem' }}>
        {events.map((ev) => {
          const bs = bannerState[ev.id] || {}
          const banners = ev.banner_images || []
          return (
            <div key={ev.id} className="card" style={{ padding: '1.25rem' }}>
              {/* Event header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div>
                  <strong style={{ fontSize: '1.05rem' }}>{ev.name}</strong>
                  <p style={{ margin: '0.25rem 0', color: '#666', fontSize: '0.9rem' }}>{ev.event_date} · {ev.location}</p>
                  <p style={{ margin: 0, fontSize: '0.85rem' }}>
                    Distances: {(ev.distances || []).join(', ') || '—'} ·{' '}
                    <span style={{ color: ev.is_active ? 'green' : 'gray' }}>
                      {ev.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                </div>
                <button className="btn-primary btn-sm" onClick={() => openEdit(ev)}>Edit</button>
              </div>

              {/* Banner images section */}
              <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: '1rem' }}>
                <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '0.75rem' }}>
                  🖼 Banner Images ({banners.length}/5)
                </p>

                {/* Existing banners */}
                {banners.length > 0 && (
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    {banners.map((url, i) => (
                      <div key={i} style={{ position: 'relative' }}>
                        <img
                          src={url}
                          alt={`Banner ${i + 1}`}
                          style={{ width: 120, height: 80, objectFit: 'cover', borderRadius: 6, border: '1px solid #e5e7eb' }}
                        />
                        <button
                          onClick={() => handleBannerDelete(ev.id, i)}
                          disabled={bs.uploading}
                          style={{
                            position: 'absolute', top: 2, right: 2,
                            background: 'rgba(220,38,38,0.85)', color: '#fff',
                            border: 'none', borderRadius: '50%',
                            width: 20, height: 20, fontSize: '0.7rem',
                            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                          }}
                          title="Remove banner"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Upload new banner */}
                {banners.length < 5 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      ref={(el) => { fileInputRefs.current[ev.id] = el }}
                      onChange={(e) => handleBannerUpload(ev.id, e.target.files[0])}
                      disabled={bs.uploading}
                      style={{ fontSize: '0.85rem' }}
                    />
                    {bs.uploading && <span style={{ fontSize: '0.82rem', color: '#6b7280' }}>Uploading…</span>}
                  </div>
                )}
                {bs.error && <p className="error-msg" style={{ marginTop: '0.25rem' }}>{bs.error}</p>}
              </div>
            </div>
          )
        })}
      </div>

      {/* Create/Edit modal */}
      {showModal && (
        <div
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
            zIndex: 1000,
            overflowY: 'auto',
            padding: '80px 1rem 2rem',   /* 80px clears the sticky navbar */
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false) }}
        >
          <div className="card" style={{ width: '100%', maxWidth: 480, padding: '2rem', flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0 }}>{editing ? 'Edit event' : 'Create event'}</h2>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#6b7280', lineHeight: 1, padding: '0 0.25rem' }}
                aria-label="Close"
              >×</button>
            </div>
            <form onSubmit={handleSubmit} noValidate>
              <div className="form-group">
                <label>Event name</label>
                <input name="name" required value={form.name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Date</label>
                <input name="event_date" type="date" required value={form.event_date} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Location</label>
                <input name="location" required value={form.location} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Distances (comma-separated, e.g. 5K, 10K)</label>
                <input name="distances" value={form.distances} onChange={handleChange} placeholder="5K, 10K, 21K" />
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input id="is_active" name="is_active" type="checkbox" checked={form.is_active} onChange={handleChange} style={{ width: 'auto' }} />
                <label htmlFor="is_active" style={{ margin: 0 }}>Active</label>
              </div>
              {formError && <p className="error-msg">{formError}</p>}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
