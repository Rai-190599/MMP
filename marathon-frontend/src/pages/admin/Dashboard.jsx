import { useEffect, useState } from 'react'
import client from '../../api/client.js'

const TABS = ['Users', 'Invites', 'Events']
const ROLE_COLORS = { admin: '#7c3aed', organizer: '#2563eb', participant: '#16a34a', volunteer: '#d97706' }
const STATUS_COLORS = { pending: '#d97706', accepted: '#16a34a', expired: '#6b7280' }

export default function AdminDashboard() {
  const [tab, setTab] = useState('Users')

  // Users
  const [users, setUsers] = useState([])
  const [usersTotal, setUsersTotal] = useState(0)
  const [usersPage, setUsersPage] = useState(1)
  const [roleFilter, setRoleFilter] = useState('')
  const [usersError, setUsersError] = useState(null)

  // Invites
  const [invites, setInvites] = useState([])
  const [invitesError, setInvitesError] = useState(null)
  const [inviteForm, setInviteForm] = useState({ email: '', name: '' })
  const [inviteSending, setInviteSending] = useState(false)
  const [inviteFormError, setInviteFormError] = useState(null)

  // Events
  const [adminEvents, setAdminEvents] = useState([])
  const [eventsError, setEventsError] = useState(null)

  async function fetchUsers(page = 1, role = '') {
    setUsersError(null)
    try {
      const params = { page, page_size: 20 }
      if (role) params.role = role
      const data = await client.get('/admin/users', { params }).then((r) => r.data)
      setUsers(data.items)
      setUsersTotal(data.total)
    } catch (err) {
      setUsersError(err?.response?.data?.detail || 'Failed to load users')
    }
  }

  async function fetchInvites() {
    setInvitesError(null)
    try {
      const data = await client.get('/admin/invites').then((r) => r.data)
      setInvites(data)
    } catch (err) {
      setInvitesError(err?.response?.data?.detail || 'Failed to load invites')
    }
  }

  async function fetchAdminEvents() {
    setEventsError(null)
    try {
      const data = await client.get('/admin/events').then((r) => r.data)
      setAdminEvents(data)
    } catch (err) {
      setEventsError(err?.response?.data?.detail || 'Failed to load events')
    }
  }

  useEffect(() => {
    if (tab === 'Users') fetchUsers(usersPage, roleFilter)
    else if (tab === 'Invites') fetchInvites()
    else if (tab === 'Events') fetchAdminEvents()
  }, [tab])

  useEffect(() => { fetchUsers(usersPage, roleFilter) }, [usersPage, roleFilter])

  async function sendInvite(e) {
    e.preventDefault()
    setInviteFormError(null)
    setInviteSending(true)
    try {
      const data = await client.post('/admin/invites', inviteForm).then((r) => r.data)
      setInvites((prev) => [data, ...prev])
      setInviteForm({ email: '', name: '' })
    } catch (err) {
      setInviteFormError(err?.response?.data?.detail || 'Failed to send invite')
    } finally {
      setInviteSending(false)
    }
  }

  const totalPages = Math.ceil(usersTotal / 20)

  return (
    <div style={{ padding: '2rem', maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ marginBottom: '1.5rem' }}>Admin Dashboard</h1>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '2px solid #e5e7eb' }}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '0.5rem 1.25rem',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontWeight: tab === t ? 700 : 400,
              borderBottom: tab === t ? '2px solid #2563eb' : '2px solid transparent',
              marginBottom: -2,
              color: tab === t ? '#2563eb' : '#374151',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Users Tab */}
      {tab === 'Users' && (
        <div>
          <div style={{ marginBottom: '1rem' }}>
            <label>Filter by role: </label>
            <select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setUsersPage(1) }} style={{ marginLeft: '0.5rem', padding: '0.25rem 0.5rem' }}>
              <option value="">All</option>
              {['admin', 'organizer', 'participant', 'volunteer'].map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          {usersError && <p className="error-msg">{usersError}</p>}
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb', textAlign: 'left' }}>
                {['Name', 'Email', 'Role', 'Joined'].map((h) => (
                  <th key={h} style={{ padding: '0.75rem', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '0.75rem' }}>{u.name}</td>
                  <td style={{ padding: '0.75rem' }}>{u.email}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ background: ROLE_COLORS[u.role] || '#6b7280', color: '#fff', borderRadius: 4, padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', color: '#6b7280', fontSize: '0.9rem' }}>
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', alignItems: 'center' }}>
              <button disabled={usersPage === 1} onClick={() => setUsersPage((p) => p - 1)} style={{ padding: '0.25rem 0.75rem' }}>←</button>
              <span>Page {usersPage} of {totalPages}</span>
              <button disabled={usersPage === totalPages} onClick={() => setUsersPage((p) => p + 1)} style={{ padding: '0.25rem 0.75rem' }}>→</button>
            </div>
          )}
        </div>
      )}

      {/* Invites Tab */}
      {tab === 'Invites' && (
        <div>
          <form onSubmit={sendInvite} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div className="form-group" style={{ margin: 0, flex: 1, minWidth: 180 }}>
              <label>Email</label>
              <input type="email" required value={inviteForm.email} onChange={(e) => setInviteForm((f) => ({ ...f, email: e.target.value }))} />
            </div>
            <div className="form-group" style={{ margin: 0, flex: 1, minWidth: 150 }}>
              <label>Name</label>
              <input type="text" required value={inviteForm.name} onChange={(e) => setInviteForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <button type="submit" className="btn-primary" disabled={inviteSending} style={{ whiteSpace: 'nowrap' }}>
              {inviteSending ? 'Sending…' : 'Send invite'}
            </button>
          </form>
          {inviteFormError && <p className="error-msg">{inviteFormError}</p>}
          {invitesError && <p className="error-msg">{invitesError}</p>}
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb', textAlign: 'left' }}>
                {['Email', 'Status', 'Expires', 'Invite link'].map((h) => (
                  <th key={h} style={{ padding: '0.75rem', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invites.map((inv) => {
                const link = `${window.location.origin}/accept-invite?token=${inv.token}`
                const isPending = inv.status === 'pending'
                return (
                  <tr key={inv.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '0.75rem' }}>{inv.email}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{ background: STATUS_COLORS[inv.status] || '#6b7280', color: '#fff', borderRadius: 4, padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}>
                        {inv.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#6b7280', fontSize: '0.9rem' }}>
                      {new Date(inv.expires_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {isPending ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <code style={{ fontSize: '0.78rem', background: '#f3f4f6', padding: '0.2rem 0.4rem', borderRadius: 4, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>
                            {link}
                          </code>
                          <button
                            className="btn-secondary btn-sm"
                            onClick={() => {
                              navigator.clipboard.writeText(link)
                                .then(() => alert('Link copied to clipboard'))
                                .catch(() => alert(link))
                            }}
                            title="Copy invite link"
                          >
                            Copy
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Events Tab */}
      {tab === 'Events' && (
        <div>
          {eventsError && <p className="error-msg">{eventsError}</p>}
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb', textAlign: 'left' }}>
                {['Event name', 'Date', 'Location', 'Organizers'].map((h) => (
                  <th key={h} style={{ padding: '0.75rem', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {adminEvents.map((ev) => (
                <tr key={ev.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '0.75rem' }}>{ev.name}</td>
                  <td style={{ padding: '0.75rem', color: '#6b7280' }}>{ev.event_date}</td>
                  <td style={{ padding: '0.75rem', color: '#6b7280' }}>{ev.location || '—'}</td>
                  <td style={{ padding: '0.75rem', color: '#6b7280', fontSize: '0.9rem' }}>
                    {(ev.organizers || []).map((o) => o.name).join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
