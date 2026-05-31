import axios from 'axios'

const TOKEN_KEY = 'marathon_token'

// In Docker (nginx proxy): VITE_API_URL is "" → same-origin requests, nginx proxies to api.
// In local dev: VITE_API_URL is "http://localhost:8000" → direct to backend.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach Bearer token if present
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor — on 401, clear auth and redirect to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('marathon_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const authApi = {
  register: (data) => client.post('/auth/register', data).then((r) => r.data),
  signup: (data) => client.post('/auth/signup', data).then((r) => r.data),
  login: (data) => client.post('/auth/login', data).then((r) => r.data),
}

export const eventsApi = {
  getEvent: (eventId) => client.get(`/events/${eventId}`).then((r) => r.data),
  getEventDetail: (eventId) => client.get(`/events/${eventId}/detail`).then((r) => r.data),
  listEvents: (params) => client.get('/events', { params }).then((r) => r.data),
}

export const registrationsApi = {
  create: (data) => client.post('/registrations/', data).then((r) => r.data),
  join: (data) => client.post('/registrations/join', data).then((r) => r.data),
  getMyStatus: (eventId) =>
    client.get('/registrations/me', { params: { event_id: eventId } }).then((r) => r.data),
  confirm: (eventId) =>
    client.post('/registrations/me/confirm', { event_id: eventId }).then((r) => r.data),
  cancel: (eventId) =>
    client.delete('/registrations/me', { params: { event_id: eventId } }),
  getQrUrl: (registrationId) =>
    client.get(`/registrations/${registrationId}/qr`).then((r) => r.data),
  getCertificate: (registrationId) =>
    client.get(`/certificates/${registrationId}`, { validateStatus: (s) => s < 500 }).then((r) => ({
      status: r.status,
      ...r.data,
    })),
}

export const organizerApi = {
  listRegistrations: (params) =>
    client.get('/organizer/registrations', { params }).then((r) => r.data),
  approve: (registrationId, bibNumber) =>
    client
      .patch(`/organizer/registrations/${registrationId}/approve`, { bib_number: bibNumber ?? null })
      .then((r) => r.data),
  setFinishTime: (registrationId, finishTime) =>
    client
      .patch(`/organizer/registrations/${registrationId}/finish-time`, { finish_time: finishTime })
      .then((r) => r.data),
  getSummary: (eventId) =>
    client
      .get('/organizer/registrations/summary', { params: { event_id: eventId } })
      .then((r) => r.data),
  uploadFinishTimes: (eventId, file) => {
    const form = new FormData()
    form.append('event_id', eventId)
    form.append('file', file)
    return client
      .post('/organizer/registrations/upload-finish-times', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  listVolunteerApplications: (params) =>
    client.get('/organizer/volunteer-applications', { params }).then((r) => r.data),
  reviewVolunteerApplication: (applicationId, data) =>
    client
      .patch(`/organizer/volunteer-applications/${applicationId}`, data)
      .then((r) => r.data),
}

export const eventsManagementApi = {
  listEvents: () => client.get('/manage/events/').then((r) => r.data),
  createEvent: (data) => client.post('/manage/events/', data).then((r) => r.data),
  updateEvent: (eventId, data) =>
    client.patch(`/manage/events/${eventId}`, data).then((r) => r.data),
  uploadBanner: (eventId, file) => {
    const form = new FormData()
    form.append('file', file)
    return client
      .post(`/manage/events/${eventId}/banners`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  deleteBanner: (eventId, index) =>
    client.delete(`/manage/events/${eventId}/banners/${index}`).then((r) => r.data),
}

export const volunteerApi = {
  apply: (data) => client.post('/volunteer-applications/', data).then((r) => r.data),
  getMyApplications: (params) =>
    client.get('/volunteer-applications/me', { params }).then((r) => r.data),
  withdraw: (applicationId) =>
    client.delete(`/volunteer-applications/${applicationId}`),
  getEventSlots: (eventId) =>
    client.get(`/volunteer-applications/event/${eventId}/slots`).then((r) => r.data),
}

export const tasksApi = {
  list: (params) => client.get('/tasks/', { params }).then((r) => r.data),
  create: (data) => client.post('/tasks/', data).then((r) => r.data),
  update: (taskId, data) => client.patch(`/tasks/${taskId}`, data).then((r) => r.data),
  remove: (taskId) => client.delete(`/tasks/${taskId}`),
  updateChecklist: (taskId, index, done) =>
    client.patch(`/tasks/${taskId}/checklist`, { index, done }).then((r) => r.data),
}

export const notificationsApi = {
  broadcast: (data) => client.post('/notifications/broadcast', data).then((r) => r.data),
  history: (params) => client.get('/notifications/history', { params }).then((r) => r.data),
}

export const volunteersApi = {
  scan: (qrCodeData) =>
    client.post('/volunteers/scan', { qr_code_data: qrCodeData }).then((r) => r.data),
  finish: (qrCodeData, finishTime) =>
    client.post('/volunteers/finish', {
      qr_code_data: qrCodeData,
      finish_time: finishTime || null,
    }).then((r) => r.data),
  getMyAssignment: () => client.get('/volunteers/me/assignment').then((r) => r.data),
}

export default client
