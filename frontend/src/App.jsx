// src/App.jsx — Root routing component for LabCraft
// React Router maps URL paths to page components
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Page components — each lives in its own file under src/pages/
import LoginPage from './pages/LoginPage';
import CodeEditorPage from './pages/CodeEditorPage';
import SubmissionHistoryPage from './pages/SubmissionHistoryPage';
import SubmissionDetailPage from './pages/SubmissionDetailPage';
import TeacherSubmissionsPage from './pages/TeacherSubmissionsPage';
import StudentDashboardPage from './pages/StudentDashboardPage';
import TeacherDashboardPage from './pages/TeacherDashboardPage';
import { getUser } from './utils/auth';

function RootRedirect() {
  const user = getUser();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return user.role === 'teacher' ? (
    <Navigate to="/teacher/dashboard" replace />
  ) : (
    <Navigate to="/dashboard" replace />
  );
}

function App() {
  return (
    // Routes is the container; only the first matching Route is rendered
    <Routes>
      {/* Root path — dynamically redirect to role-specific dashboard or login */}
      <Route path="/" element={<RootRedirect />} />

      {/* Authentication page — accessible before the user logs in */}
      <Route path="/login" element={<LoginPage />} />

      {/* Analytics Dashboards (Module 6) */}
      <Route path="/dashboard" element={<StudentDashboardPage />} />
      <Route path="/teacher/dashboard" element={<TeacherDashboardPage />} />

      {/* Student: open the Monaco code editor for a specific assignment */}
      <Route path="/assignments/:assignmentId/submit" element={<CodeEditorPage />} />

      {/* Student: list all of their own submissions for an assignment */}
      <Route path="/assignments/:assignmentId/submissions" element={<SubmissionHistoryPage />} />

      {/* Alias for submission history */}
      <Route path="/submissions/assignment/:assignmentId/history" element={<SubmissionHistoryPage />} />

      {/* Student: view the full detail of one submission (read-only code + feedback) */}
      <Route path="/submissions/:submissionId" element={<SubmissionDetailPage />} />

      {/* Teacher: view every student's submission for an assignment */}
      <Route path="/teacher/assignments/:assignmentId/submissions" element={<TeacherSubmissionsPage />} />
    </Routes>
  );
}

export default App;
