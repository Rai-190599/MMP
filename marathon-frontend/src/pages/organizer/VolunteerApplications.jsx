import { useEffect, useState } from 'react'
import { eventsManagementApi, organizerApi, volunteerApi } from '../../api/client.js'
import LoadingSpinner from '../../components/LoadingSpinner.jsx'

const TABS = ['pending', 'approved', 'rejected']

const TAB_LABELS = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
}

function SlotSummary({ eventId }) {
  const [slots, setSlots] = useState([])

  useEffect(() => {
    if (!eventId) return
    volunteerApi
      .getEventSlots(eventId)
      .then((data) => setSlots(data.slots ?? []))
      .catch(() => {})
  }, [eventId])

  if (!slots.length) return null

  return (
    <div
      style={{
        display: 'flex',
        gap: '1.5rem',
        flexWrap: 'wrap',
        marginBottom: '1.25rem',
        padding: '0.75rem 1rem',
        background: '#f9fafb',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        fontSize: '0.88rem',
      }}
    >
      {slots.map((s) => (
        <span key={s.role}>
          <strong>{s.role.replace(/_/g, ' ')}</strong>:{' '}
          <span style={{ color: s.remaining === 0 ? '#dc2626' : '#16a34a' }}>
            {s.filled}/{s.cap} filled
          </span>
        </span>
      ))}
    </div>
  )
}

export default function VolunteerApplications() {
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [activeTab, setActiveTab] = useState('pending')
  const [applications, setApplications] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(null) // application id being actioned

  // Load organizer's events for the selector
  useEffect(() => {
    eventsManagementApi
      .listEvents()
      .then((data) => {
        setEvents(data)
        if (data.length > 0) setSelectedEventId(data[0].id)
      })
      .catch(() => {})
  }, [])

  // Load applications when event or tab changes
  useEffect(() => {
    if (!selectedEventId) return
    setLoading(true)
    organizerApi
      .listVolunteerApplications({ event_id: selectedEventId, status: activeTab })
      .then((data) => {
        setApplications(data.items ?? [])
        setTotal(data.total ?? 0)
      })
      .catch(() => {
        setApplications([])
        setTotal(0)
      })
      .finally(() => setLoading(false))
  }, [selectedEventId, activeTab])

  async function handleReview(applicationId, newStatus) {
    setActionLoading(applicationId)
    try {
      await organizerApi.reviewVolunteerApplication(applicationId, { status: newStatus })
      // Remove from current tab list
      setApplications((prev) => prev.filter((a) => a.id !== applicationId))
      setTotal((t) => Math.max(t - 1, 0))
    } catch (err) {
      const detail = err?.response?.data?.detail
      alert(detail ?? 'Action failed. Please try again.')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="page-container">
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>
        Volunteer Applications
      </h1>

      {/* Event selector */}
      <div className="form-group" style={{ maxWidth: 360, marginBottom: '1.25rem' }}>
        <label htmlFor="event-select">Event</label>
        <select
          id="event-select"
          value={selectedEventId}
          onChange={(e) => setSelectedEventId(e.target.value)}
        >
          {events.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.name}
            </option>
          ))}
        </select>
      </div>

      {/* Slot summary */}
      {selectedEventId && <SlotSummary eventId={selectedEventId} />}

      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          gap: '0.25rem',
          marginBottom: '1.25rem',
          borderBottom: '2px solid #e5e7eb',
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.5rem 1.1rem',
              borderRadius: '6px 6px 0 0',
              border: 'none',
              background: activeTab === tab ? '#4f46e5' : 'transparent',
              color: activeTab === tab ? '#fff' : '#6b7280',
              fontWeight: activeTab === tab ? 600 : 400,
              fontSize: '0.9rem',
              cursor: 'pointer',
            }}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner text="Loading applications…" />
      ) : applications.length === 0 ? (
        <p style={{ color: '#6b7280', padding: '2rem 0' }}>
          No {activeTab} applications.
        </p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Role</th>
                <th>Note</th>
                <th>Applied</th>
                {activeTab === 'pending' && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => (
                <tr key={app.id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{app.user_name}</div>
                    <div style={{ fontSize: '0.82rem', color: '#6b7280' }}>{app.user_email}</div>
                  </td>
                  <td>
                    <span className="badge badge-approved" style={{ textTransform: 'none' }}>
                      {app.desired_role.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={{ maxWidth: 200, fontSize: '0.85rem', color: '#374151' }}>
                    {app.note ?? <span style={{ color: '#9ca3af' }}>—</span>}
                  </td>
                  <td style={{ fontSize: '0.85rem', color: '#6b7280', whiteSpace: 'nowrap' }}>
                    {new Date(app.applied_at).toLocaleDateString()}
                  </td>
                  {activeTab === 'pending' && (
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn-success btn-sm"
                          disabled={actionLoading === app.id}
                          onClick={() => handleReview(app.id, 'approved')}
                        >
                          Approve
                        </button>
                        <button
                          className="btn-danger btn-sm"
                          disabled={actionLoading === app.id}
                          onClick={() => handleReview(app.id, 'rejected')}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ marginTop: '1.5rem', fontSize: '0.88rem' }}>
        <a href="/organizer" style={{ color: '#4f46e5' }}>← Back to dashboard</a>
      </p>
    </div>
  )
}
