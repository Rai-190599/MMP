import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext.jsx'
import Navbar from './components/Navbar.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'

import EventLanding from './pages/EventLanding.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Signup from './pages/Signup.jsx'
import Landing from './pages/Landing.jsx'
import EventBrowser from './pages/EventBrowser.jsx'
import EventRegister from './pages/EventRegister.jsx'
import VolunteerApply from './pages/VolunteerApply.jsx'
import ParticipantStatus from './pages/ParticipantStatus.jsx'
import AcceptInvite from './pages/AcceptInvite.jsx'
import Dashboard from './pages/organizer/Dashboard.jsx'
import Registrations from './pages/organizer/Registrations.jsx'
import TaskBoard from './pages/organizer/TaskBoard.jsx'
import NotificationCenter from './pages/organizer/NotificationCenter.jsx'
import OrganizerEvents from './pages/organizer/Events.jsx'
import VolunteerApplications from './pages/organizer/VolunteerApplications.jsx'
import AdminDashboard from './pages/admin/Dashboard.jsx'
import Scanner from './pages/volunteer/Scanner.jsx'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <Routes>
          {/* Public */}
          <Route path="/" element={<Landing />} />
          <Route path="/event/:eventId" element={<EventLanding />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/accept-invite" element={<AcceptInvite />} />

          {/* Participant */}
          <Route
            path="/browse"
            element={
              <ProtectedRoute>
                <EventBrowser />
              </ProtectedRoute>
            }
          />
          <Route
            path="/events/:eventId/register"
            element={
              <ProtectedRoute role="participant">
                <EventRegister />
              </ProtectedRoute>
            }
          />
          <Route
            path="/events/:eventId/volunteer"
            element={
              <ProtectedRoute role="participant">
                <VolunteerApply />
              </ProtectedRoute>
            }
          />
          <Route
            path="/status"
            element={
              <ProtectedRoute role="participant">
                <ParticipantStatus />
              </ProtectedRoute>
            }
          />

          {/* Organizer */}
          <Route
            path="/organizer"
            element={
              <ProtectedRoute role="organizer">
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/events"
            element={
              <ProtectedRoute role="organizer">
                <OrganizerEvents />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/regs"
            element={
              <ProtectedRoute role="organizer">
                <Registrations />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/tasks"
            element={
              <ProtectedRoute role="organizer">
                <TaskBoard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/notifications"
            element={
              <ProtectedRoute role="organizer">
                <NotificationCenter />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizer/vol-apps"
            element={
              <ProtectedRoute role="organizer">
                <VolunteerApplications />
              </ProtectedRoute>
            }
          />

          {/* Admin */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute role="admin">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Volunteer scanner — accessible to participants with assignment */}
          <Route
            path="/volunteer/scanner"
            element={
              <ProtectedRoute role="participant">
                <Scanner />
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
