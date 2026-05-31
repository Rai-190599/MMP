import { createContext, useCallback, useEffect, useState } from 'react'
import { jwtDecode } from 'jwt-decode'

export const AuthContext = createContext(null)

const TOKEN_KEY = 'marathon_token'

function decodeUser(token) {
  try {
    const payload = jwtDecode(token)
    return { id: payload.sub, role: payload.role }
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(() => {
    const t = localStorage.getItem(TOKEN_KEY)
    return t ? decodeUser(t) : null
  })

  // Keep user name from the register/login response
  const [userProfile, setUserProfile] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('marathon_user') || 'null')
    } catch {
      return null
    }
  })

  const login = useCallback((newToken, profile) => {
    localStorage.setItem(TOKEN_KEY, newToken)
    if (profile) localStorage.setItem('marathon_user', JSON.stringify(profile))
    setToken(newToken)
    setUser(decodeUser(newToken))
    setUserProfile(profile || null)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('marathon_user')
    setToken(null)
    setUser(null)
    setUserProfile(null)
  }, [])

  // Merge JWT claims with profile name
  const fullUser = user
    ? { ...user, name: userProfile?.name ?? user.role }
    : null

  return (
    <AuthContext.Provider
      value={{
        token,
        user: fullUser,
        isAuthenticated: !!token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
