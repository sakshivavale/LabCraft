/*
  src/pages/TeacherSubmissionsPage.jsx — Teacher review dashboard for assignment submissions.

  Who can access this page?
    Approved teachers who own the classroom for this assignment.
    The backend endpoint `TeacherSubmissionListView` verifies:
      assignment.classroom.teacher == request.user
    Students attempting to call this endpoint receive 403 Forbidden.

  Features:
    1. Fetches and lists all student submissions for an assignment.
    2. Displays student identity, submission timestamp, language, and grading status.
    3. Filter submissions by specific student.
    4. Code inspector: opens any student's submitted code in a read-only Monaco Editor modal.
    5. Summarises submission statistics (total attempts, pending count, accepted count).
*/

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Editor from '@monaco-editor/react';

import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { getTeacherSubmissions, getTeacherStudentSubmissions, getAssignment } from '../services/api';
import { MONACO_LANGUAGE, LANGUAGE_DISPLAY } from '../utils/languageMap';
import { isTeacher } from '../utils/auth';

function TeacherSubmissionsPage() {
  const { assignmentId } = useParams();

  // Submissions list from GET /api/submissions/assignment/<id>/all/
  const [submissions, setSubmissions] = useState([]);
  const [assignment, setAssignment] = useState(null);

  // Loading and error states
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // Selected submission for code preview modal
  const [inspectingSubmission, setInspectingSubmission] = useState(null);

  // Student filter dropdown state
  const [selectedStudentId, setSelectedStudentId] = useState('');

  // ---------------------------------------------------------------------------
  // Load submissions and assignment details
  // ---------------------------------------------------------------------------
  const fetchSubmissions = async (studentIdFilter = '') => {
    setLoading(true);
    setErrorMessage('');

    try {
      let response;
      if (studentIdFilter) {
        // Teacher filters by one student
        response = await getTeacherStudentSubmissions(assignmentId, studentIdFilter);
      } else {
        // Teacher views all submissions
        response = await getTeacherSubmissions(assignmentId);
      }
      setSubmissions(response.data);

      // Fetch assignment title
      try {
        const assignResponse = await getAssignment(assignmentId);
        setAssignment(assignResponse.data);
      } catch {
        // Assignment fetch is best-effort for title
      }
    } catch (err) {
      const errorText =
        err.response?.data?.detail ||
        'Failed to load submissions. Only the teacher who owns this classroom can access this page.';
      setErrorMessage(errorText);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions(selectedStudentId);
  }, [assignmentId, selectedStudentId]);

  // Extract unique list of students from submissions for the filter dropdown
  const uniqueStudents = Array.from(
    new Map(
      submissions
        .filter((sub) => sub.student)
        .map((sub) => [sub.student.id, sub.student])
    ).values()
  );

  // Compute summary stats
  const totalSubmissions = submissions.length;
  const acceptedCount = submissions.filter((s) => s.status === 'accepted').length;
  const pendingCount = submissions.filter((s) => s.status === 'pending').length;

  return (
    <>
      <Navbar />

      <main className="container" style={{ marginTop: '24px' }}>
        {/* Header card */}
        <section className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1>Student Submissions</h1>
              <p className="subtitle" style={{ margin: 0 }}>
                {assignment ? (
                  <>
                    Reviewing: <strong>{assignment.title}</strong>
                  </>
                ) : (
                  `Assignment #${assignmentId}`
                )}
              </p>
            </div>

            {/* Quick stats pills */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <div style={{ background: '#0f172a', padding: '6px 14px', borderRadius: '8px', border: '1px solid #334155', fontSize: '13px' }}>
                Total: <strong>{totalSubmissions}</strong>
              </div>
              <div style={{ background: '#052e16', padding: '6px 14px', borderRadius: '8px', border: '1px solid #166534', fontSize: '13px', color: '#86efac' }}>
                Accepted: <strong>{acceptedCount}</strong>
              </div>
              <div style={{ background: '#451a03', padding: '6px 14px', borderRadius: '8px', border: '1px solid #9a3412', fontSize: '13px', color: '#fed7aa' }}>
                Pending: <strong>{pendingCount}</strong>
              </div>
            </div>
          </div>
        </section>

        {/* Filter bar */}
        <div className="card" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label htmlFor="studentFilter" style={{ margin: 0, fontSize: '13px' }}>
              Filter by Student:
            </label>
            <select
              id="studentFilter"
              value={selectedStudentId}
              onChange={(e) => setSelectedStudentId(e.target.value)}
              style={{ width: 'auto', margin: 0, padding: '6px 12px', fontSize: '13px' }}
            >
              <option value="">All Students ({uniqueStudents.length})</option>
              {uniqueStudents.map((st) => (
                <option key={st.id} value={st.id}>
                  {st.username} {st.first_name ? `(${st.first_name} ${st.last_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          {selectedStudentId && (
            <button
              onClick={() => setSelectedStudentId('')}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '4px 10px' }}
            >
              Clear Filter
            </button>
          )}
        </div>

        {/* Loading state */}
        {loading && <LoadingSpinner message="Fetching classroom submissions..." />}

        {/* Error message */}
        {errorMessage && <div className="error-msg">❌ {errorMessage}</div>}

        {/* Submissions table */}
        {!loading && !errorMessage && (
          <div className="card">
            {submissions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>📂</div>
                <h3>No submissions found</h3>
                <p style={{ fontSize: '13px' }}>
                  {selectedStudentId
                    ? 'This student has not submitted code for this assignment yet.'
                    : 'No students have submitted solutions for this assignment yet.'}
                </p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Student</th>
                      <th>Language</th>
                      <th>Status</th>
                      <th>Submitted At</th>
                      <th>Timing</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((sub, idx) => (
                      <tr key={sub.id}>
                        <td>
                          <strong>#{sub.id}</strong>
                        </td>
                        <td>
                          <div style={{ fontWeight: '600', color: '#f1f5f9' }}>
                            {sub.student?.username || 'Unknown Student'}
                          </div>
                          {sub.student?.email && (
                            <div className="text-muted" style={{ fontSize: '12px' }}>
                              {sub.student.email}
                            </div>
                          )}
                        </td>
                        <td>
                          <span style={{ fontFamily: 'monospace', fontSize: '13px' }}>
                            {LANGUAGE_DISPLAY[sub.language] || sub.language}
                          </span>
                        </td>
                        <td>
                          <StatusBadge status={sub.status} />
                        </td>
                        <td style={{ fontSize: '13px' }}>
                          {new Date(sub.submitted_at).toLocaleString('en-IN', {
                            dateStyle: 'medium',
                            timeStyle: 'short',
                          })}
                        </td>
                        <td>
                          {sub.is_late ? (
                            <span className="late-badge">⚠️ Late</span>
                          ) : (
                            <span style={{ color: '#10b981', fontSize: '12px', fontWeight: '600' }}>
                              On time
                            </span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            type="button"
                            onClick={() => setInspectingSubmission(sub)}
                            className="btn btn-primary"
                            style={{ padding: '6px 12px', fontSize: '12px' }}
                          >
                            🔍 Inspect Code
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Modal dialog for inspecting student's source code */}
        {inspectingSubmission && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.75)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '20px',
              zIndex: 1000,
            }}
            onClick={() => setInspectingSubmission(null)}
          >
            <div
              style={{
                backgroundColor: '#1e293b',
                borderRadius: '12px',
                width: '100%',
                maxWidth: '900px',
                maxHeight: '90vh',
                overflow: 'auto',
                padding: '24px',
                border: '1px solid #334155',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
              }}
              onClick={(e) => e.stopPropagation()} // Don't close modal when clicking inside
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h2 style={{ margin: 0 }}>
                    Submission #{inspectingSubmission.id} — {inspectingSubmission.student?.username}
                  </h2>
                  <p className="text-muted" style={{ fontSize: '13px', margin: 0 }}>
                    {LANGUAGE_DISPLAY[inspectingSubmission.language] || inspectingSubmission.language} •{' '}
                    Submitted at {new Date(inspectingSubmission.submitted_at).toLocaleString()}
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <StatusBadge status={inspectingSubmission.status} />
                  <button
                    type="button"
                    onClick={() => setInspectingSubmission(null)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '14px' }}
                  >
                    ✕ Close
                  </button>
                </div>
              </div>

              {/* Read-only Monaco code viewer */}
              <div className="editor-wrapper">
                <Editor
                  height="450px"
                  language={MONACO_LANGUAGE[inspectingSubmission.language] || 'plaintext'}
                  theme="vs-dark"
                  value={inspectingSubmission.source_code}
                  options={{
                    readOnly: true,
                    fontSize: 14,
                    lineNumbers: 'on',
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    wordWrap: 'on',
                  }}
                />
              </div>

              {/* Feedback if any */}
              {inspectingSubmission.feedback && (
                <div style={{ marginTop: '16px', background: '#0f172a', padding: '12px', borderRadius: '8px' }}>
                  <h4 style={{ color: '#93c5fd', marginBottom: '6px' }}>Grader Output:</h4>
                  <pre style={{ fontSize: '12px', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                    {inspectingSubmission.feedback}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </>
  );
}

export default TeacherSubmissionsPage;
