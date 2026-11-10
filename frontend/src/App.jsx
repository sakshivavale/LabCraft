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

function App() {
  return (
    // Routes is the container; only the first matching Route is rendered
    <Routes>
      {/* Root path — redirect immediately to /login so there is no blank page */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Authentication page — accessible before the user logs in */}
      <Route path="/login" element={<LoginPage />} />

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
