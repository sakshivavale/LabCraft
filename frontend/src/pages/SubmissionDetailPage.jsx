/*
  src/pages/SubmissionDetailPage.jsx — Detailed view for a single code submission.

  What this page displays:
    1. Submission metadata: Assignment title, classroom, student username, submission timestamp.
    2. Grading status badge (Pending, Accepted, Wrong Answer, etc.) and is_late flag.
    3. The submitted source code displayed inside a read-only Monaco Editor.
       - Syntax highlighting matching the submission language.
       - Prevents accidental edits of historical submission records.
    4. Grader feedback section:
       - Displays compiler output or test case results (populated by Module 5 grading engine).
       - Shows a placeholder when grading is pending.
    5. Navigation back to the assignment code editor and history list.

  Security note:
    The backend view (`SubmissionDetailView`) filters queries by `student=request.user`.
    If student A tries to view student B's submission ID, the server returns 404,
    preventing unauthorized access to another student's code.
*/

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Editor from '@monaco-editor/react';

import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { getSubmissionDetail } from '../services/api';
import { MONACO_LANGUAGE, LANGUAGE_DISPLAY } from '../utils/languageMap';

function SubmissionDetailPage() {
  const { submissionId } = useParams();

  // Submission detail object from backend
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // ---------------------------------------------------------------------------
  // Load submission detail on mount or when submissionId changes
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      setErrorMessage('');

      try {
        // GET /api/submissions/<id>/
        const response = await getSubmissionDetail(submissionId);
        setSubmission(response.data);
      } catch (err) {
        const errorText =
          err.response?.data?.detail ||
          'Failed to load submission details. This submission may not exist or belongs to another student.';
        setErrorMessage(errorText);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [submissionId]);

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="container" style={{ marginTop: '40px' }}>
          <LoadingSpinner message="Loading submission details..." />
        </div>
      </>
    );
  }

  if (errorMessage || !submission) {
    return (
      <>
        <Navbar />
        <div className="container" style={{ marginTop: '40px', maxWidth: '700px' }}>
          <div className="card">
            <h2>Submission Not Found</h2>
            <div className="error-msg">{errorMessage}</div>
            <Link to="/login" className="btn btn-secondary" style={{ marginTop: '12px' }}>
              ← Return
            </Link>
          </div>
        </div>
      </>
    );
  }

  // Determine Monaco mode string for syntax highlighting
  const monacoMode = MONACO_LANGUAGE[submission.language] || 'plaintext';

  return (
    <>
      <Navbar />

      <main className="container" style={{ marginTop: '24px' }}>
        {/* Navigation and Summary Header */}
        <section className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <h1 style={{ margin: 0 }}>Submission #{submission.id}</h1>
                <StatusBadge status={submission.status} />
                {submission.is_late && <span className="late-badge">⚠️ Late Submission</span>}
              </div>

              <p className="subtitle" style={{ margin: 0 }}>
                Assignment: <strong>{submission.assignment_title}</strong> | Classroom:{' '}
                <strong>{submission.classroom_name || `Class #${submission.classroom_id}`}</strong>
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <Link
                to={`/assignments/${submission.assignment_id}/submissions`}
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
              >
                📜 All Submissions
              </Link>
              <Link
                to={`/assignments/${submission.assignment_id}/submit`}
                className="btn btn-primary"
                style={{ fontSize: '13px' }}
              >
                ✏️ Re-open Editor
              </Link>
            </div>
          </div>

          <hr className="divider" />

          {/* Submission metadata pills */}
          <div className="row" style={{ fontSize: '13px', color: '#cbd5e1' }}>
            <div>
              👤 <strong>Submitted By:</strong> {submission.student?.username || 'You'}
            </div>
            <div>
              💻 <strong>Language:</strong> {LANGUAGE_DISPLAY[submission.language] || submission.language}
            </div>
            <div>
              📅 <strong>Submitted At:</strong>{' '}
              {new Date(submission.submitted_at).toLocaleString('en-IN', {
                dateStyle: 'medium',
                timeStyle: 'medium',
              })}
            </div>
          </div>
        </section>

        {/* Read-Only Source Code Viewer */}
        <section className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3>Submitted Source Code</h3>
            <span className="text-muted" style={{ fontSize: '12px' }}>
              Read-only view • {submission.source_code.split('\n').length} lines
            </span>
          </div>

          <div className="editor-wrapper">
            <Editor
              height="450px"
              language={monacoMode}
              theme="vs-dark"
              value={submission.source_code}
              options={{
                readOnly: true, // Prevents modifications of submitted code
                fontSize: 14,
                fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
                lineNumbers: 'on',
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                wordWrap: 'on',
                tabSize: 4,
                domReadOnly: true,
              }}
            />
          </div>
        </section>

        {/* Grader Feedback Section */}
        <section className="card">
          <h3 style={{ marginBottom: '10px', color: '#93c5fd' }}>Grading Results & Feedback</h3>

          {submission.feedback ? (
            <div
              style={{
                backgroundColor: '#0f172a',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid #334155',
                fontFamily: 'monospace',
                fontSize: '13px',
                whiteSpace: 'pre-wrap',
                color: '#e2e8f0',
              }}
            >
              {submission.feedback}
            </div>
          ) : (
            <div
              style={{
                backgroundColor: '#0f172a',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid #334155',
                fontSize: '14px',
                color: '#94a3b8',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <span style={{ fontSize: '20px' }}>⏳</span>
              <div>
                <strong style={{ color: '#cbd5e1' }}>Awaiting Execution & Grading</strong>
                <p style={{ margin: 0, fontSize: '13px' }}>
                  Your code has been securely saved. Automatic execution and evaluation will be
                  performed by the Module 5 grading engine.
                </p>
              </div>
            </div>
          )}
        </section>
      </main>
    </>
  );
}

export default SubmissionDetailPage;
