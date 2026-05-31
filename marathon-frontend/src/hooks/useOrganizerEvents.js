import { useEffect, useState } from 'react'
import { eventsManagementApi } from '../api/client.js'

/**
 * Fetches the organizer's own events and manages a selected event ID.
 * Falls back to VITE_EVENT_ID if set, otherwise picks the first event.
 */
export function useOrganizerEvents() {
  const [events, setEvents] = useState([])
  const [selectedId, setSelectedId] = useState(import.meta.env.VITE_EVENT_ID || '')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    eventsManagementApi
      .listEvents()
      .then((data) => {
        setEvents(data)
        if (data.length > 0) {
          const ids = data.map((e) => e.id)
          // Use VITE_EVENT_ID if it matches a real event, otherwise always pick first
          setSelectedId((prev) => (prev && ids.includes(prev) ? prev : data[0].id))
        }
      })
      .catch(() => setError('Could not load events'))
      .finally(() => setLoading(false))
  }, [])

  return { events, selectedId, setSelectedId, loading, error }
}
