import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import DashboardLayout from '../components/Layout/DashboardLayout';
import LoadingScreen from '../components/LoadingScreen';
import AuthGuard from './AuthGuard';

const Login = lazy(() => import('../pages/Login/Login'));
const Register = lazy(() => import('../pages/Register/Register'));
const ForgotPassword = lazy(() => import('../pages/ForgotPassword'));
const ResetPassword = lazy(() => import('../pages/ResetPassword'));
const VerifyEmail = lazy(() => import('../pages/VerifyEmail'));

const StudentDashboard = lazy(() => import('../pages/StudentDashboard/StudentDashboard'));
const StudentAcademics = lazy(() => import('../pages/StudentPages/Academics'));
const StudentAttendance = lazy(() => import('../pages/StudentPages/Attendance'));
const StudentWellbeing = lazy(() => import('../pages/StudentPages/Wellbeing'));
const StudentRecommendations = lazy(() => import('../pages/StudentPages/Recommendations'));
const StudentProfile = lazy(() => import('../pages/StudentPages/Profile'));
const StudentSettings = lazy(() => import('../pages/StudentPages/Settings'));
const AccessibilitySettings = lazy(() => import('../pages/AccessibilitySettings'));

const LecturerDashboard = lazy(() => import('../pages/LecturerDashboard/LecturerDashboard'));
const LecturerStudents = lazy(() => import('../pages/LecturerPages/Students'));
const LecturerStudentReview = lazy(() => import('../pages/LecturerPages/StudentReview'));
const LecturerAnalytics = lazy(() => import('../pages/LecturerPages/Analytics'));

const AdvisorDashboard = lazy(() => import('../pages/AdvisorDashboard/AdvisorDashboard'));
const AdvisorCases = lazy(() => import('../pages/AdvisorPages/Cases'));
const AdvisorCaseReview = lazy(() => import('../pages/AdvisorPages/CaseReview'));
const AdvisorInterventions = lazy(() => import('../pages/AdvisorPages/Interventions'));

const AdminDashboard = lazy(() => import('../pages/AdminDashboard/AdminDashboard'));
const AdminAnalytics = lazy(() => import('../pages/AdminPages/Analytics'));
const AdminUsers = lazy(() => import('../pages/AdminPages/Users'));
const AdminSettings = lazy(() => import('../pages/AdminPages/Settings'));
const AdminCsvData = lazy(() => import('../pages/AdminPages/CsvData'));

const NotFound = lazy(() => import('../pages/NotFound'));

const withSuspense = (node: React.ReactNode) => <Suspense fallback={<LoadingScreen />}>{node}</Suspense>;

export const router = createBrowserRouter([
  {
    path: '/login',
    element: withSuspense(<Login />)
  },
  {
    path: '/register',
    element: withSuspense(<Register />)
  },
  {
    path: '/forgot-password',
    element: withSuspense(<ForgotPassword />)
  },
  {
    path: '/reset-password',
    element: withSuspense(<ResetPassword />)
  },
  {
    path: '/verify-email',
    element: withSuspense(<VerifyEmail />)
  },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <DashboardLayout allowedRoles={['student']} />,
        children: [
          { path: '/student/dashboard', element: withSuspense(<StudentDashboard />) },
          { path: '/student/academics', element: withSuspense(<StudentAcademics />) },
          { path: '/student/attendance', element: withSuspense(<StudentAttendance />) },
          { path: '/student/wellbeing', element: withSuspense(<StudentWellbeing />) },
          { path: '/student/recommendations', element: withSuspense(<StudentRecommendations />) },
          { path: '/student/profile', element: withSuspense(<StudentProfile />) },
          { path: '/student/settings', element: withSuspense(<StudentSettings />) },
          { path: '/student/preferences', element: withSuspense(<AccessibilitySettings />) }
        ]
      },
      {
        element: <DashboardLayout allowedRoles={['lecturer']} />,
        children: [
          { path: '/lecturer/dashboard', element: withSuspense(<LecturerDashboard />) },
          { path: '/lecturer/students', element: withSuspense(<LecturerStudents />) },
          { path: '/lecturer/students/:studentId', element: withSuspense(<LecturerStudentReview />) },
          { path: '/lecturer/analytics', element: withSuspense(<LecturerAnalytics />) },
          { path: '/lecturer/preferences', element: withSuspense(<AccessibilitySettings />) }
        ]
      },
      {
        element: <DashboardLayout allowedRoles={['advisor']} />,
        children: [
          { path: '/advisor/dashboard', element: withSuspense(<AdvisorDashboard />) },
          { path: '/advisor/cases', element: withSuspense(<AdvisorCases />) },
          { path: '/advisor/cases/:referralId', element: withSuspense(<AdvisorCaseReview />) },
          { path: '/advisor/interventions', element: withSuspense(<AdvisorInterventions />) },
          { path: '/advisor/preferences', element: withSuspense(<AccessibilitySettings />) }
        ]
      },
      {
        element: <DashboardLayout allowedRoles={['admin']} />,
        children: [
          { path: '/admin/dashboard', element: withSuspense(<AdminDashboard />) },
          { path: '/admin/analytics', element: withSuspense(<AdminAnalytics />) },
          { path: '/admin/users', element: withSuspense(<AdminUsers />) },
          { path: '/admin/students/:studentId', element: withSuspense(<LecturerStudentReview />) },
          { path: '/admin/settings', element: withSuspense(<AdminSettings />) },
          { path: '/admin/csv-data', element: withSuspense(<AdminCsvData />) },
          { path: '/admin/preferences', element: withSuspense(<AccessibilitySettings />) }
        ]
      }
    ]
  },
  { path: '/', element: <Navigate to="/login" replace /> },
  { path: '*', element: withSuspense(<NotFound />) }
]);
