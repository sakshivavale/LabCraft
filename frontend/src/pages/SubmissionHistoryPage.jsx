/*
  src/pages/SubmissionHistoryPage.jsx — Student's submission history for an assignment.

  Why is this page important?
    Students typically submit multiple iterations of code as they debug and improve
    their solutions. This page presents their submission timeline:
    - Lists all previous attempts (newest first, per Django model ordering)
    - Shows grading status badges (Pending, Accepted, Wrong Answer, etc.)
    - Identifies whether an attempt was on time or submitted past deadline
    - Links to the full submission detail view to review past code
*/

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';

import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { getMySubmissions, getAssignment } from '../services/api';
import { LANGUAGE_DISPLAY } from '../utils/languageMap';

function SubmissionHistoryPage() {
  const { assignmentId } = useParams();

  // Submissions list returned by GET /api/submissions/assignment/<id>/my/
  const [submissions, setSubmissions] = useState([]);
  const [assignment, setAssignment] = useState(null);

  // Loading and error indicators
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // ---------------------------------------------------------------------------
  // Fetch submission history and assignment title on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      setErrorMessage('');

      try {
        // Fetch student's own submissions for this assignment
        const historyResponse = await getMySubmissions(assignmentId);
        setSubmissions(historyResponse.data);

        // Fetch assignment metadata for header title display
        try {
          const assignResponse = await getAssignment(assignmentId);
          setAssignment(assignResponse.data);
        } catch {
          // If assignment fetch fails, we still show the submissions
        }
      } catch (err) {
        const errorDetail =
          err.response?.data?.detail ||
          'Failed to load your submission history. Please make sure you are logged in as a student.';
        setErrorMessage(errorDetail);
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [assignmentId]);

  return (
    <>
      <Navbar />

      <main className="container" style={{ marginTop: '24px' }}>
        {/* Header navigation and title */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1>Submission History</h1>
              <p className="subtitle" style={{ margin: 0 }}>
                {assignment ? (
                  <>
                    Assignment: <strong>{assignment.title}</strong>
                  </>
                ) : (
                  `Assignment #${assignmentId}`
                )}
              </p>
            </div>

            <Link
              to={`/assignments/${assignmentId}/submit`}
              className="btn btn-primary"
              style={{ fontSize: '14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              💻 Open Code Editor
            </Link>
          </div>
        </div>

        {/* Loading state */}
        {loading && <LoadingSpinner message="Retrieving your past submissions..." />}

        {/* Error message */}
        {errorMessage && <div className="error-msg">❌ {errorMessage}</div>}

        {/* Submissions list */}
        {!loading && !errorMessage && (
          <div className="card">
            {submissions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                <div style={{ fontSize: '36px', marginBottom: '12px' }}>📝</div>
                <h3 style={{ color: '#e2e8f0', marginBottom: '6px' }}>No submissions yet</h3>
                <p style={{ fontSize: '14px', marginBottom: '20px' }}>
                  You haven't submitted any code for this assignment yet.
                </p>
                <Link to={`/assignments/${assignmentId}/submit`} className="btn btn-primary">
                  Write Your First Submission →
                </Link>
              </div>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: '80px' }}>Attempt</th>
                      <th>Language</th>
                      <th>Status</th>
                      <th>Submitted At</th>
                      <th>Timing</th>
                      <th style={{ textAlign: 'right' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((sub, index) => {
                      // Attempt numbering: since submissions are sorted newest first,
                      // the latest attempt is submissions.length - index
                      const attemptNumber = submissions.length - index;

                      return (
                        <tr key={sub.id}>
                          <td>
                            <strong>#{attemptNumber}</strong>{' '}
                            <span className="text-muted" style={{ fontSize: '11px' }}>
                              (ID: {sub.id})
                            </span>
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
                            <Link
                              to={`/submissions/${sub.id}`}
                              className="btn btn-secondary"
                              style={{ padding: '6px 14px', fontSize: '12px' }}
                            >
                              View Details →
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </>
  );
}

export default SubmissionHistoryPage;

