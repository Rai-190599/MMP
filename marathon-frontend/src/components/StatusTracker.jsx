import styles from './StatusTracker.module.css'

export default function StatusTracker({ currentStage, stages }) {
  return (
    <div className={styles.tracker} role="list" aria-label="Registration progress">
      {stages.map((s, idx) => {
        const isCurrent = s.stage === currentStage
        const isDone = s.completed && s.stage < currentStage

        return (
          <div key={s.stage} className={styles.step} role="listitem">
            {/* Connector line before each step except the first */}
            {idx > 0 && (
              <div
                className={`${styles.line} ${stages[idx - 1].completed ? styles.lineDone : ''}`}
                aria-hidden="true"
              />
            )}

            <div className={styles.circleWrapper}>
              <div
                className={`${styles.circle} ${
                  isDone ? styles.done : isCurrent ? styles.current : styles.future
                }`}
                aria-label={`Stage ${s.stage}: ${s.label} — ${
                  isDone ? 'completed' : isCurrent ? 'current' : 'upcoming'
                }`}
              >
                {isDone ? '✓' : s.stage}
              </div>
            </div>

            <div className={styles.label}>{s.label}</div>
            {s.timestamp && (
              <div className={styles.timestamp}>
                {new Date(s.timestamp).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
