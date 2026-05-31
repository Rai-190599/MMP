import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import styles from './Navbar.module.css'

const ORGANIZER_LINKS = [
  { label: 'Dashboard', path: '/organizer' },
  { label: 'Registrations', path: '/organizer/regs' },
  { label: 'Volunteers', path: '/organizer/vol-apps' },
  { label: 'Events', path: '/organizer/events' },
  { label: 'Tasks', path: '/organizer/tasks' },
  { label: 'Notifications', path: '/organizer/notifications' },
]

const PARTICIPANT_LINKS = [
  { label: 'Events', path: '/browse' },
  { label: 'Scanner', path: '/volunteer/scanner' },
]

const ADMIN_LINKS = [
  { label: 'Admin', path: '/admin' },
]

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const links =
    user?.role === 'organizer' ? ORGANIZER_LINKS
    : user?.role === 'participant' ? PARTICIPANT_LINKS
    : user?.role === 'admin' ? ADMIN_LINKS
    : []

  // Generate initials for avatar
  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'U'

  return (
    <nav className={styles.navbar}>
      <div className={styles['navbar-inner']}>
        <span className={styles['navbar-brand']} onClick={() => navigate('/')}>
          Marathon <span className={styles['navbar-brand-dot']} />
        </span>

        {isAuthenticated && links.length > 0 && (
          <div className={styles['navbar-nav']}>
            {links.map((link) => {
              const isActive = location.pathname === link.path
              return (
                <button
                  key={link.path}
                  className={`${styles['nav-link']} ${isActive ? styles['nav-link-active'] : ''}`}
                  onClick={() => navigate(link.path)}
                >
                  {link.label}
                </button>
              )
            })}
          </div>
        )}

        <div className={styles['navbar-user']}>
          {isAuthenticated && user ? (
            <>
              <div className={styles.avatar} title={`${user.name} (${user.role})`}>
                {initials}
              </div>
              <button className="btn-secondary btn-sm press-effect" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <button className="btn-primary btn-sm press-effect" onClick={() => navigate('/login')}>
              Login
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}
