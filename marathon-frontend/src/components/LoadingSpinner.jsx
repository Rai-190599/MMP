import styles from './LoadingSpinner.module.css'

export default function LoadingSpinner({ text = 'Loading…' }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.skeletonBar} />
      <div className={styles.skeletonBarShort} />
      <span className={styles.text}>{text}</span>
    </div>
  )
}
