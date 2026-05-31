import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

/**
 * Wraps a route that requires authentication.
 * Optionally restricts to a specific role.
 * AC-7: redirects to /login if no token.
 * AC-8: token persists across refresh via localStorage.
 */
export default function ProtectedRoute({ children, role }) {
  const { isAuthenticated, user } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const allowed = Array.isArray(role) ? role : [role]
  if (role && !allowed.includes(user?.role)) {
    return <Navigate to="/login" replace />
  }

  return children
}
