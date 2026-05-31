/**
 * /register is deprecated — all new account creation goes through /signup.
 * This component just redirects so any old bookmarks or links still work.
 */
import { Navigate } from 'react-router-dom'

export default function Register() {
  return <Navigate to="/signup" replace />
}
