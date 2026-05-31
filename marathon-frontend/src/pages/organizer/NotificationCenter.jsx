import { useEffect, useState } from 'react'
import { notificationsApi, organizerApi } from '../../api/client.js'
import LoadingSpinner from '../../components/LoadingSpinner.jsx'
import { useOrganizerEvents } from '../../hooks/useOrganizerEvents.js'
import styles from './NotificationCenter.module.css'

const STATUSES = [
  'registered',
  'approved',
  'participation_confirmed',
  'bib_collected',
  'finished_certified',
]

const CHANNELS = ['email', 'whatsapp']

export default function NotificationCenter() {
  const { events, selectedId, setSelectedId } = useOrganizerEvents()

  return (
    <div className="page-container">
      <h1 className={styles.heading}>Notification Center</h1>

      {/* Event selector */}
      <div className="form-group" style={{ maxWidth: 360, marginBottom: '1.25rem' }}>
        <label htmlFor="event-select">Event</label>
        <select
          id="event-select"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {events.map((ev) => (
            <option key={ev.id} value={ev.id}>{ev.name}</option>
          ))}
        </select>
      </div>

      <BroadcastSection eventId={selectedId} />
      <HistorySection eventId={selectedId} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Compose & Broadcast
// ---------------------------------------------------------------------------
function BroadcastSection({ eventId }) {
  const [channel, setChannel] = useState('email')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [previewCount, setPreviewCount] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handlePreview() {
    if (!eventId) return
    setPreviewLoading(true)
    setPreviewCount(null)
    try {
      const summary = await organizerApi.getSummary(eventId)
      setPreviewCount(filterStatus ? (summary[filterStatus] ?? 0) : (summary.total ?? 0))
    } catch {
      setPreviewCount('?')
    } finally {
      setPreviewLoading(false)
    }
  }

  async function handleSend() {
    if (!message.trim()) { setError('Message is required'); return }
    if (channel === 'email' && !subject.trim()) { setError('Subject is required for email'); return }
    setSending(true)
    setError(null)
    setResult(null)
    try {
      const payload = {
        event_id: eventId,
        channel,
        subject,
        message,
        filter_status: filterStatus || null,
      }
      const data = await notificationsApi.broadcast(payload)
      setResult(data)
      setMessage('')
      setSubject('')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Broadcast failed')
    } finally {
      setSending(false)
    }
  }

  const whatsappOver = channel === 'whatsapp' && message.length > 250

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>Compose & Broadcast</h2>

      {/* Channel selector */}
      <div className={styles.channelRow}>
        {CHANNELS.map((ch) => (
          <label key={ch} className={styles.channelLabel}>
            <input
              type="radio"
              name="channel"
              value={ch}
              checked={channel === ch}
              onChange={() => setChannel(ch)}
            />
            {ch === 'email' ? '📧 Email' : '💬 WhatsApp'}
          </label>
        ))}
      </div>

      {/* Subject (email only) */}
      {channel === 'email' && (
        <div className={styles.field}>
          <label className={styles.label}>Subject</label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className={styles.input}
            placeholder="Email subject…"
            data-testid="broadcast-subject"
          />
        </div>
      )}

      {/* Message */}
      <div className={styles.field}>
        <label className={styles.label}>
          Message
          {channel === 'whatsapp' && (
            <span className={whatsappOver ? styles.charOver : styles.charCount}>
              {' '}{message.length}/250
            </span>
          )}
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className={styles.textarea}
          rows={5}
          placeholder="Your message…"
          maxLength={channel === 'whatsapp' ? 250 : undefined}
          data-testid="broadcast-message"
        />
      </div>

      {/* Audience filter */}
      <div className={styles.field}>
        <label className={styles.label}>Audience</label>
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPreviewCount(null) }}
          className={styles.select}
          data-testid="broadcast-filter-status"
        >
          <option value="">All participants</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {/* Preview */}
      <div className={styles.previewRow}>
        <button
          className="btn-secondary"
          onClick={handlePreview}
          disabled={previewLoading}
          data-testid="preview-recipients-btn"
        >
          {previewLoading ? 'Loading…' : 'Preview recipients'}
        </button>
        {previewCount !== null && (
          <span className={styles.previewCount}>
            ~{previewCount} recipient{previewCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}
      {result && (
        <p className="success-msg" data-testid="broadcast-result">
          ✅ {result.message}
        </p>
      )}

      <button
        className="btn-primary"
        onClick={handleSend}
        disabled={sending || whatsappOver}
        data-testid="send-broadcast-btn"
        style={{ marginTop: '0.5rem' }}
      >
        {sending ? 'Sending…' : '📣 Send Broadcast'}
      </button>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Notification History
// ---------------------------------------------------------------------------
const PAGE_SIZE = 50

function HistorySection({ eventId }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [channelFilter, setChannelFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (eventId) loadHistory(1, true)
  }, [channelFilter, eventId])

  async function loadHistory(p, reset = false) {
    if (!eventId) return
    setLoading(true)
    setError(null)
    try {
      const params = { event_id: eventId, page: p, page_size: PAGE_SIZE }
      if (channelFilter) params.channel = channelFilter
      const data = await notificationsApi.history(params)
      setTotal(data.total)
      setPage(p)
      setItems(reset ? data.items : (prev) => [...prev, ...data.items])
    } catch {
      setError('Failed to load notification history.')
    } finally {
      setLoading(false)
    }
  }

  const hasMore = items.length < total

  return (
    <section className={styles.section}>
      <div className={styles.historyHeader}>
        <h2 className={styles.sectionTitle}>Notification History</h2>
        <select
          value={channelFilter}
          onChange={(e) => setChannelFilter(e.target.value)}
          className={styles.select}
          style={{ width: 'auto' }}
          data-testid="history-channel-filter"
        >
          <option value="">All channels</option>
          <option value="email">Email</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="sms">SMS</option>
        </select>
      </div>

      {loading && items.length === 0 && <LoadingSpinner text="Loading history…" />}
      {error && <p className="error-msg">{error}</p>}

      {items.length > 0 && (
        <div className={styles.tableWrapper}>
          <table>
            <thead>
              <tr>
                <th>Recipient</th>
                <th>Channel</th>
                <th>Type</th>
                <th>Sent?</th>
                <th>Sent at</th>
                <th>Message preview</th>
              </tr>
            </thead>
            <tbody>
              {items.map((n) => (
                <tr key={n.id}>
                  <td>
                    <div>{n.recipient_name ?? '—'}</div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{n.recipient_email ?? ''}</div>
                  </td>
                  <td>
                    <span className={`badge badge-${n.channel}`}>{n.channel}</span>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                    {n.trigger_type === 'manual_broadcast' ? 'manual' : 'auto'}
                  </td>
                  <td>
                    {n.sent
                      ? <span style={{ color: '#059669' }}>✓</span>
                      : <span style={{ color: '#dc2626' }}>✗</span>}
                  </td>
                  <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                    {n.sent_at ? new Date(n.sent_at).toLocaleString() : '—'}
                  </td>
                  <td className={styles.msgPreview}>
                    {(n.content || '').slice(0, 80)}{(n.content || '').length > 80 ? '…' : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && items.length === 0 && !error && (
        <p style={{ color: '#9ca3af', textAlign: 'center', padding: '2rem' }}>No notifications yet.</p>
      )}

      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button
            className="btn-secondary"
            onClick={() => loadHistory(page + 1)}
            disabled={loading}
            data-testid="load-more-history"
          >
            {loading ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </section>
  )
}
