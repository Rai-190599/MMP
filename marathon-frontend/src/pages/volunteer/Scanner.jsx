import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import { volunteersApi } from '../../api/client.js'
import LoadingSpinner from '../../components/LoadingSpinner.jsx'
import styles from './Scanner.module.css'

const SCANNER_ELEMENT_ID = 'qr-reader'
const RESET_DELAY_MS = 4000
const MAX_HISTORY = 5

export default function Scanner() {
  const [assignment, setAssignment] = useState(null)
  const [assignmentLoading, setAssignmentLoading] = useState(true)
  const [assignmentError, setAssignmentError] = useState(null)

  const [scanResult, setScanResult] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [history, setHistory] = useState([])

  // Finish-line mode: manual time input
  const [finishTimeInput, setFinishTimeInput] = useState('')
  const [manualInput, setManualInput] = useState('')
  const [manualLoading, setManualLoading] = useState(false)

  const scannerRef = useRef(null)
  const processingRef = useRef(false)

  const isFinishLine = assignment?.role_type === 'finish_line'

  useEffect(() => {
    // Default finish time to now
    const now = new Date()
    now.setSeconds(0, 0)
    setFinishTimeInput(now.toISOString().slice(0, 16))

    volunteersApi
      .getMyAssignment()
      .then(setAssignment)
      .catch(() => setAssignmentError('No volunteer assignment found for your account.'))
      .finally(() => setAssignmentLoading(false))
  }, [])

  useEffect(() => {
    if (assignmentLoading || assignmentError || !assignment) return

    const html5QrCode = new Html5Qrcode(SCANNER_ELEMENT_ID)
    scannerRef.current = html5QrCode
    setScanning(true)

    html5QrCode
      .start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        onScanSuccess,
        () => {}
      )
      .catch(() => setScanning(false))

    return () => {
      html5QrCode.isScanning && html5QrCode.stop().catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assignmentLoading, assignmentError, assignment])

  async function processQrData(decodedText) {
    if (processingRef.current) return
    processingRef.current = true
    setScanResult(null)

    try {
      let result
      if (isFinishLine) {
        // Use the finish time input (convert local datetime to ISO)
        const isoTime = finishTimeInput ? new Date(finishTimeInput).toISOString() : null
        result = await volunteersApi.finish(decodedText, isoTime)
      } else {
        result = await volunteersApi.scan(decodedText)
      }

      setScanResult({ ...result, error: null })
      setHistory((h) => [{
        id: decodedText,
        name: result.participant_name,
        bib: result.bib_number,
        time_recorded: isFinishLine ? result.scanned_at : null,
        success: true,
        time: new Date().toLocaleTimeString(),
      }, ...h].slice(0, MAX_HISTORY))

      // Advance finish time by 1 minute for the next runner
      if (isFinishLine && finishTimeInput) {
        const next = new Date(finishTimeInput)
        next.setMinutes(next.getMinutes() + 1)
        setFinishTimeInput(next.toISOString().slice(0, 16))
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Scan failed'
      setScanResult({ success: false, error: msg })
      setHistory((h) => [{
        id: decodedText, name: '—', bib: '—', success: false, error: msg,
        time: new Date().toLocaleTimeString(),
      }, ...h].slice(0, MAX_HISTORY))
    }

    setTimeout(() => {
      setScanResult(null)
      processingRef.current = false
      setScanning(true)
      scannerRef.current
        ?.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 250, height: 250 } },
          onScanSuccess,
          () => {}
        )
        .catch(() => {})
    }, RESET_DELAY_MS)
  }

  async function onScanSuccess(decodedText) {
    setScanning(false)
    await processQrData(decodedText)
  }

  async function handleManualSubmit(e) {
    e.preventDefault()
    if (!manualInput.trim()) return
    setManualLoading(true)
    await processQrData(manualInput.trim())
    setManualInput('')
    setManualLoading(false)
  }

  if (assignmentLoading) return <LoadingSpinner text="Loading assignment…" />

  return (
    <div className="page-container">
      <h1 className={styles.heading}>
        {isFinishLine ? '🏁 Finish Line Scanner' : '📷 QR Scanner'}
      </h1>

      {/* No assignment */}
      {assignmentError && (
        <div className="card" style={{ background: '#fef2f2', border: '1px solid #fca5a5', marginBottom: '1.5rem' }}>
          <p style={{ color: '#dc2626', fontWeight: 600, marginBottom: '0.5rem' }}>
            No volunteer assignment found
          </p>
          <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            Apply to volunteer via the Events page and wait for organizer approval.
          </p>
        </div>
      )}

      {/* Assignment info */}
      {assignment && (
        <div className={`card ${styles.assignmentCard}`}>
          <div>
            <span className={styles.assignLabel}>Event</span>
            <span className={styles.assignValue}>{assignment.event.name}</span>
          </div>
          <div>
            <span className={styles.assignLabel}>Role</span>
            <span className={styles.assignValue}>{assignment.role_type.replace(/_/g, ' ')}</span>
          </div>
        </div>
      )}

      {assignment && (
        <>
          {/* Finish time input — only for finish_line role */}
          {isFinishLine && (
            <div className="card" style={{ marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem' }}>
                ⏱ Finish time to record
              </p>
              <p style={{ fontSize: '0.82rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                Set the time before scanning each runner. Auto-advances by 1 min after each scan.
              </p>
              <input
                type="datetime-local"
                value={finishTimeInput}
                onChange={(e) => setFinishTimeInput(e.target.value)}
                style={{ width: '100%', maxWidth: 240 }}
              />
              <button
                className="btn-secondary btn-sm"
                style={{ marginLeft: '0.5rem' }}
                onClick={() => {
                  const now = new Date()
                  now.setSeconds(0, 0)
                  setFinishTimeInput(now.toISOString().slice(0, 16))
                }}
              >
                Now
              </button>
            </div>
          )}

          {/* Camera scanner */}
          <div className={`card ${styles.scannerCard}`}>
            <div
              id={SCANNER_ELEMENT_ID}
              className={styles.scannerViewport}
              aria-label="QR code scanner"
            />
            {!scanning && !scanResult && (
              <p className={styles.scannerHint}>Initialising camera…</p>
            )}
            {scanning && !scanResult && (
              <p className={styles.scannerHint}>
                {isFinishLine
                  ? 'Scan runner QR to record finish time'
                  : 'Point camera at participant QR code'}
              </p>
            )}
          </div>

          {/* Manual entry fallback */}
          <div className="card" style={{ marginTop: '1rem' }}>
            <p style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: 500 }}>
              Manual entry (paste registration ID)
            </p>
            <form onSubmit={handleManualSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder="Paste registration UUID…"
                style={{ flex: 1, fontSize: '0.85rem' }}
              />
              <button
                type="submit"
                className="btn-primary btn-sm"
                disabled={!manualInput.trim() || manualLoading}
              >
                {manualLoading ? '…' : isFinishLine ? 'Record' : 'Scan'}
              </button>
            </form>
          </div>
        </>
      )}

      {/* Scan result */}
      {scanResult && (
        <div
          className={`card ${scanResult.success ? styles.resultSuccess : styles.resultError}`}
          role="status"
          aria-live="polite"
          style={{ marginTop: '1rem' }}
        >
          {scanResult.success ? (
            <>
              <span className={styles.resultIcon}>✓</span>
              <div>
                <p className={styles.resultName}>{scanResult.participant_name}</p>
                <p className={styles.resultBib}>BIB #{scanResult.bib_number}</p>
                <p className={styles.resultStatus}>{scanResult.status?.replace(/_/g, ' ')}</p>
                {isFinishLine && scanResult.scanned_at && (
                  <p style={{ fontSize: '0.85rem', color: '#065f46', marginTop: '0.25rem' }}>
                    ⏱ {new Date(scanResult.scanned_at).toLocaleTimeString()}
                  </p>
                )}
              </div>
            </>
          ) : (
            <>
              <span className={styles.resultIcon}>✗</span>
              <p>{scanResult.error}</p>
            </>
          )}
          <p className={styles.resetHint}>Resetting in {RESET_DELAY_MS / 1000}s…</p>
        </div>
      )}

      {/* Scan history */}
      {history.length > 0 && (
        <div className={`card ${styles.historyCard}`} style={{ marginTop: '1rem' }}>
          <h2 className={styles.historyTitle}>Recent Scans</h2>
          <ul className={styles.historyList}>
            {history.map((h, i) => (
              <li key={i} className={`${styles.historyItem} ${h.success ? styles.historyOk : styles.historyFail}`}>
                <span>{h.success ? '✓' : '✗'}</span>
                <span className={styles.historyName}>{h.name}</span>
                {h.success && <span className={styles.historyBib}>BIB #{h.bib}</span>}
                {h.success && h.time_recorded && (
                  <span style={{ fontSize: '0.78rem', color: '#065f46' }}>
                    ⏱ {new Date(h.time_recorded).toLocaleTimeString()}
                  </span>
                )}
                {!h.success && <span className={styles.historyErr}>{h.error}</span>}
                <span className={styles.historyTime}>{h.time}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
