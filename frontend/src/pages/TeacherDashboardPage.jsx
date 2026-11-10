/*
  src/pages/TeacherDashboardPage.jsx — Teacher & Multi-Classroom Analytics Dashboard for LabCraft.

  Why this page exists (Module 6):
    Teachers require an operational cockpit to monitor class progress:
    - Multi-classroom summary: enrolled student counts, submission rates, acceptance rate
    - Classroom deep dive: student leaderboards and assignment completion metrics
    - Assignment deep dive: score distribution histograms and full student gradebooks
    - Recent submissions feed with 1-click links to code review and grading results.
*/

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import {
  getTeacherDashboard,
  getClassroomAnalytics,
  getAssignmentAnalytics,
} from '../services/api';
import { getUser } from '../utils/auth';
import { STATUS_COLORS } from '../utils/languageMap';

function TeacherDashboardPage() {
  const user = getUser();

  // Root teacher dashboard state
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // Modal deep-dive state
  const [selectedClassroomId, setSelectedClassroomId] = useState(null);
  const [classroomAnalytics, setClassroomAnalytics] = useState(null);
  const [loadingClassroom, setLoadingClassroom] = useState(false);

  const [selectedAssignmentId, setSelectedAssignmentId] = useState(null);
  const [assignmentAnalytics, setAssignmentAnalytics] = useState(null);
  const [loadingAssignment, setLoadingAssignment] = useState(false);

  // Fetch teacher dashboard metrics on mount
  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      setErrorMessage('');

      try {
        const response = await getTeacherDashboard();
        setDashboardData(response.data);
      } catch (err) {
        const detail =
          err.response?.data?.detail ||
          'Failed to load teacher analytics. Please ensure you are logged in as an approved teacher.';
        setErrorMessage(detail);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  // Open Classroom Deep Dive Modal
  const handleOpenClassroom = async (classroomId) => {
    setSelectedClassroomId(classroomId);
    setLoadingClassroom(true);
    setClassroomAnalytics(null);

    try {
      const response = await getClassroomAnalytics(classroomId);
      setClassroomAnalytics(response.data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to load classroom analytics.');
      setSelectedClassroomId(null);
    } finally {
      setLoadingClassroom(false);
    }
  };

  // Open Assignment Deep Dive Modal
  const handleOpenAssignment = async (assignmentId) => {
    setSelectedAssignmentId(assignmentId);
    setLoadingAssignment(true);
    setAssignmentAnalytics(null);

    try {
      const response = await getAssignmentAnalytics(assignmentId);
      setAssignmentAnalytics(response.data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to load assignment analytics.');
      setSelectedAssignmentId(null);
    } finally {
      setLoadingAssignment(false);
    }
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="container">
          <LoadingSpinner message="Aggregating multi-classroom analytics..." />
        </div>
      </>
    );
  }

  if (errorMessage) {
    return (
      <>
        <Navbar />
        <div className="container">
          <div className="card">
            <h1>Instructor Dashboard</h1>
            <div className="error-msg">{errorMessage}</div>
            <Link to="/login" className="btn btn-secondary" style={{ marginTop: '12px' }}>
              Return to Login
            </Link>
          </div>
        </div>
      </>
    );
  }

  const {
    summary,
    status_distribution,
    classrooms = [],
    recent_submissions = [],
  } = dashboardData || {};

  const totalEvaluated =
    (status_distribution?.accepted || 0) +
    (status_distribution?.wrong_answer || 0) +
    (status_distribution?.time_limit_exceeded || 0) +
    (status_distribution?.runtime_error || 0) +
    (status_distribution?.compile_error || 0) +
    (status_distribution?.memory_limit_exceeded || 0);

  return (
    <>
      <Navbar />
      <div className="container">
        {/* Header */}
        <div style={{ marginBottom: '24px' }}>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🎓 Instructor Analytics Cockpit</span>
          </h1>
          <p className="subtitle">
            Welcome, Prof. {user?.username || 'Teacher'}. Real-time student performance, submission rates, and gradebooks.
          </p>
        </div>

        {/* Top Summary Metrics */}
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Active Classrooms</span>
            <div className="stat-val" style={{ color: '#8b5cf6' }}>
              {summary?.total_classrooms || 0}
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#8b5cf6' }} />
            </div>
            <span className="stat-sub">Teaching workspaces</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Enrolled Students</span>
            <div className="stat-val" style={{ color: '#3b82f6' }}>
              {summary?.total_enrolled_students || 0}
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#3b82f6' }} />
            </div>
            <span className="stat-sub">Active learners across courses</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Total Submissions</span>
            <div className="stat-val">
              {summary?.total_submissions || 0}
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#06b6d4' }} />
            </div>
            <span className="stat-sub">{summary?.total_assignments || 0} published assignments</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Overall Acceptance Rate</span>
            <div className="stat-val text-success">
              {summary?.overall_acceptance_rate || 0}%
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary?.overall_acceptance_rate || 0}%`,
                  background: '#10b981',
                }}
              />
            </div>
            <span className="stat-sub">{status_distribution?.accepted || 0} accepted runs</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Average Score</span>
            <div className="stat-val" style={{ color: '#f59e0b' }}>
              {summary?.overall_average_score || 0}%
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary?.overall_average_score || 0}%`,
                  background: '#f59e0b',
                }}
              />
            </div>
            <span className="stat-sub">Mean assignment grade</span>
          </div>
        </div>

        {/* Global Verdict Breakdown */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>📊 System-Wide Grading Outcome Distribution</h2>
            <span className="text-muted" style={{ fontSize: '13px' }}>
              {totalEvaluated} total evaluations
            </span>
          </div>
          <p className="subtitle" style={{ marginBottom: '12px' }}>
            Aggregated verdict proportions across all student submissions in your courses.
          </p>

          {totalEvaluated > 0 ? (
            <>
              <div className="dist-bar-wrapper">
                {status_distribution?.accepted > 0 && (
                  <div
                    className="dist-bar-segment"
                    style={{
                      width: `${(status_distribution.accepted / totalEvaluated) * 100}%`,
                      backgroundColor: STATUS_COLORS.accepted,
                    }}
                    title={`Accepted: ${status_distribution.accepted}`}
                  />
                )}
                {status_distribution?.wrong_answer > 0 && (
                  <div
                    className="dist-bar-segment"
                    style={{
                      width: `${(status_distribution.wrong_answer / totalEvaluated) * 100}%`,
                      backgroundColor: STATUS_COLORS.wrong_answer,
                    }}
                    title={`Wrong Answer: ${status_distribution.wrong_answer}`}
                  />
                )}
                {status_distribution?.time_limit_exceeded > 0 && (
                  <div
                    className="dist-bar-segment"
                    style={{
                      width: `${(status_distribution.time_limit_exceeded / totalEvaluated) * 100}%`,
                      backgroundColor: STATUS_COLORS.time_limit_exceeded,
                    }}
                    title={`Time Limit Exceeded: ${status_distribution.time_limit_exceeded}`}
                  />
                )}
                {status_distribution?.runtime_error > 0 && (
                  <div
                    className="dist-bar-segment"
                    style={{
                      width: `${(status_distribution.runtime_error / totalEvaluated) * 100}%`,
                      backgroundColor: STATUS_COLORS.runtime_error,
                    }}
                    title={`Runtime Error: ${status_distribution.runtime_error}`}
                  />
                )}
                {status_distribution?.compile_error > 0 && (
                  <div
                    className="dist-bar-segment"
                    style={{
                      width: `${(status_distribution.compile_error / totalEvaluated) * 100}%`,
                      backgroundColor: STATUS_COLORS.compile_error,
                    }}
                    title={`Compile Error: ${status_distribution.compile_error}`}
                  />
                )}
              </div>

              <div className="dist-legend">
                <div className="dist-legend-item">
                  <div className="dist-legend-dot" style={{ backgroundColor: STATUS_COLORS.accepted }} />
                  <span>Accepted: <strong>{status_distribution?.accepted || 0}</strong></span>
                </div>
                <div className="dist-legend-item">
                  <div className="dist-legend-dot" style={{ backgroundColor: STATUS_COLORS.wrong_answer }} />
                  <span>Wrong Answer: <strong>{status_distribution?.wrong_answer || 0}</strong></span>
                </div>
                <div className="dist-legend-item">
                  <div className="dist-legend-dot" style={{ backgroundColor: STATUS_COLORS.time_limit_exceeded }} />
                  <span>TLE: <strong>{status_distribution?.time_limit_exceeded || 0}</strong></span>
                </div>
                <div className="dist-legend-item">
                  <div className="dist-legend-dot" style={{ backgroundColor: STATUS_COLORS.runtime_error }} />
                  <span>Runtime Error: <strong>{status_distribution?.runtime_error || 0}</strong></span>
                </div>
                <div className="dist-legend-item">
                  <div className="dist-legend-dot" style={{ backgroundColor: STATUS_COLORS.compile_error }} />
                  <span>Compile Error: <strong>{status_distribution?.compile_error || 0}</strong></span>
                </div>
              </div>
            </>
          ) : (
            <div style={{ padding: '16px 0', color: '#94a3b8', fontStyle: 'italic' }}>
              No submissions evaluated yet across your classrooms.
            </div>
          )}
        </div>

        {/* Classroom Performance Grid */}
        <div style={{ marginBottom: '24px' }}>
          <h2>🏫 Classroom Performance & Leaderboards</h2>
          <p className="subtitle">
            Click on any classroom to view student rankings, score distributions, and assignment analytics.
          </p>

          {classrooms.length === 0 ? (
            <div className="card" style={{ color: '#94a3b8' }}>
              You do not have any active classrooms. Create one to begin assigning coding labs.
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '16px',
              }}
            >
              {classrooms.map((c) => (
                <div key={c.id} className="card" style={{ marginBottom: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '18px' }}>{c.name}</h3>
                      <span className="text-muted" style={{ fontSize: '12px' }}>Code: {c.code}</span>
                    </div>
                    <span
                      style={{
                        fontSize: '11px',
                        background: '#1e3a8a',
                        color: '#93c5fd',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        fontWeight: 600,
                      }}
                    >
                      {c.enrolled_student_count} Students
                    </span>
                  </div>

                  <div style={{ margin: '16px 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '13px' }}>
                    <div>
                      <span className="text-muted">Assignments:</span>{' '}
                      <strong>{c.assignment_count}</strong>
                    </div>
                    <div>
                      <span className="text-muted">Submissions:</span>{' '}
                      <strong>{c.total_submissions}</strong>
                    </div>
                    <div>
                      <span className="text-muted">Submission Rate:</span>{' '}
                      <strong className="text-success">{c.submission_rate_percentage}%</strong>
                    </div>
                    <div>
                      <span className="text-muted">Average Score:</span>{' '}
                      <strong style={{ color: '#3b82f6' }}>{c.average_score}%</strong>
                    </div>
                  </div>

                  <button
                    onClick={() => handleOpenClassroom(c.id)}
                    className="btn btn-primary"
                    style={{ width: '100%', padding: '8px', fontSize: '13px' }}
                  >
                    View Analytics & Leaderboard 📈
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Student Submissions Feed */}
        <div className="card">
          <h2>⏱️ Recent Submissions Across All Classrooms</h2>
          <p className="subtitle">Live feed of student code submissions and automated evaluation results.</p>

          {recent_submissions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
              No submissions recorded yet.
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Assignment</th>
                    <th>Classroom</th>
                    <th>Verdict</th>
                    <th>Score</th>
                    <th>Language</th>
                    <th>Time</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recent_submissions.map((sub) => {
                    const timeStr = new Date(sub.submitted_at).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    });

                    return (
                      <tr key={sub.id}>
                        <td>
                          <strong style={{ color: '#f8fafc' }}>{sub.student_username}</strong>
                        </td>
                        <td>{sub.assignment_title}</td>
                        <td>
                          <span className="text-muted">{sub.classroom_name}</span>
                        </td>
                        <td>
                          <StatusBadge status={sub.status} />
                        </td>
                        <td>
                          <strong style={{ color: sub.score > 0 ? '#10b981' : '#e2e8f0' }}>
                            {sub.score} / {sub.max_score}
                          </strong>
                        </td>
                        <td>
                          <code style={{ fontSize: '12px', background: '#0f172a', padding: '2px 6px', borderRadius: '4px' }}>
                            {sub.language}
                          </code>
                        </td>
                        <td>
                          <span style={{ fontSize: '13px', color: '#94a3b8' }}>{timeStr}</span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <Link
                            to={`/submissions/${sub.id}`}
                            className="btn btn-secondary"
                            style={{ padding: '4px 10px', fontSize: '12px' }}
                          >
                            Inspect Code
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
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* Classroom Analytics & Leaderboard Modal */}
      {/* --------------------------------------------------------------------- */}
      {selectedClassroomId && (
        <div className="modal-overlay" onClick={() => setSelectedClassroomId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {loadingClassroom ? (
              <LoadingSpinner message="Loading classroom leaderboard and assignment stats..." />
            ) : classroomAnalytics ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h2 style={{ margin: 0 }}>
                      🏫 {classroomAnalytics.classroom?.name} ({classroomAnalytics.classroom?.code})
                    </h2>
                    <span className="text-muted" style={{ fontSize: '13px' }}>
                      Enrolled: {classroomAnalytics.classroom?.enrolled_student_count} students | Submissions: {classroomAnalytics.classroom?.total_submissions} | Avg Score: {classroomAnalytics.classroom?.average_score}%
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedClassroomId(null)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px' }}
                  >
                    ✕ Close
                  </button>
                </div>

                {/* Leaderboard Table */}
                <h3 style={{ marginTop: '20px', marginBottom: '8px' }}>🏆 Student Leaderboard</h3>
                <div className="table-wrapper" style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '24px' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Student</th>
                        <th>Email</th>
                        <th>Completed Labs</th>
                        <th>Total Score</th>
                        <th>Percentage</th>
                      </tr>
                    </thead>
                    <tbody>
                      {classroomAnalytics.leaderboard?.map((s) => (
                        <tr key={s.student_id}>
                          <td>
                            <strong>
                              {s.rank === 1 ? '🥇 1' : s.rank === 2 ? '🥈 2' : s.rank === 3 ? '🥉 3' : s.rank}
                            </strong>
                          </td>
                          <td>
                            <strong style={{ color: '#f8fafc' }}>{s.student_username}</strong>
                          </td>
                          <td>
                            <span className="text-muted">{s.student_email}</span>
                          </td>
                          <td>{s.assignments_completed}</td>
                          <td>
                            <strong style={{ color: '#3b82f6' }}>
                              {s.total_score} / {s.max_possible_score}
                            </strong>
                          </td>
                          <td>
                            <span className="text-success" style={{ fontWeight: 600 }}>
                              {s.score_percentage}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Classroom Assignments Table */}
                <h3 style={{ marginBottom: '8px' }}>📝 Assignment Performance Breakdown</h3>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Assignment</th>
                        <th>Max Score</th>
                        <th>Students Submitted</th>
                        <th>Submission Rate</th>
                        <th>Avg Score</th>
                        <th>High / Low</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {classroomAnalytics.assignments?.map((a) => (
                        <tr key={a.id}>
                          <td>
                            <strong style={{ color: '#f8fafc' }}>{a.title}</strong>
                          </td>
                          <td>{a.max_score}</td>
                          <td>{a.unique_students_submitted}</td>
                          <td>
                            <span className="text-success">{a.submission_rate_percentage}%</span>
                          </td>
                          <td>
                            <strong style={{ color: '#3b82f6' }}>{a.average_score}%</strong>
                          </td>
                          <td>
                            <span style={{ fontSize: '13px' }}>
                              {a.highest_score} / {a.lowest_score}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px' }}>
                              <button
                                onClick={() => handleOpenAssignment(a.id)}
                                className="btn btn-primary"
                                style={{ padding: '4px 8px', fontSize: '12px' }}
                              >
                                Gradebook 📊
                              </button>
                              <Link
                                to={`/teacher/assignments/${a.id}/submissions`}
                                className="btn btn-secondary"
                                style={{ padding: '4px 8px', fontSize: '12px' }}
                              >
                                Submissions
                              </Link>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Assignment Analytics & Gradebook Modal */}
      {/* --------------------------------------------------------------------- */}
      {selectedAssignmentId && (
        <div className="modal-overlay" onClick={() => setSelectedAssignmentId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {loadingAssignment ? (
              <LoadingSpinner message="Loading assignment gradebook and score distribution..." />
            ) : assignmentAnalytics ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h2 style={{ margin: 0 }}>
                      📊 {assignmentAnalytics.assignment?.title} — Gradebook
                    </h2>
                    <span className="text-muted" style={{ fontSize: '13px' }}>
                      Classroom: {assignmentAnalytics.assignment?.classroom_name} | Max Score: {assignmentAnalytics.assignment?.max_score} | Avg: {assignmentAnalytics.assignment?.average_score}%
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedAssignmentId(null)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px' }}
                  >
                    ✕ Close
                  </button>
                </div>

                {/* Score Distribution Buckets */}
                <h3 style={{ marginTop: '16px', marginBottom: '8px' }}>📈 Score Distribution Buckets</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginBottom: '20px' }}>
                  {Object.entries(assignmentAnalytics.score_distribution || {}).map(([bucket, count]) => {
                    const label = bucket.replace('_pct', '%').replace(/_/g, ' ');
                    return (
                      <div
                        key={bucket}
                        style={{
                          background: '#0f172a',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                          padding: '10px',
                          textAlign: 'center',
                        }}
                      >
                        <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>
                          {label}
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: count > 0 ? '#3b82f6' : '#64748b', marginTop: '4px' }}>
                          {count}
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748b' }}>students</div>
                      </div>
                    );
                  })}
                </div>

                {/* Student Gradebook Table */}
                <h3 style={{ marginBottom: '8px' }}>📋 Enrolled Students Roster & Submissions</h3>
                <div className="table-wrapper" style={{ maxHeight: '350px', overflowY: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Best Verdict</th>
                        <th>Score</th>
                        <th>Attempts</th>
                        <th style={{ textAlign: 'right' }}>Latest Submission</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assignmentAnalytics.gradebook?.map((entry) => (
                        <tr key={entry.student_id}>
                          <td>
                            <strong style={{ color: '#f8fafc' }}>{entry.student_username}</strong>
                          </td>
                          <td>
                            <span className="text-muted">{entry.student_email}</span>
                          </td>
                          <td>
                            {entry.has_submitted ? (
                              <span className="text-success" style={{ fontWeight: 600 }}>
                                Submitted
                              </span>
                            ) : (
                              <span style={{ color: '#ef4444', fontWeight: 600 }}>
                                Missing
                              </span>
                            )}
                          </td>
                          <td>
                            {entry.has_submitted ? (
                              <StatusBadge status={entry.best_status} />
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td>
                            {entry.has_submitted ? (
                              <strong style={{ color: entry.best_score > 0 ? '#10b981' : '#e2e8f0' }}>
                                {entry.best_score}
                              </strong>
                            ) : (
                              <span className="text-muted">0</span>
                            )}
                          </td>
                          <td>{entry.attempts_count}</td>
                          <td style={{ textAlign: 'right' }}>
                            {entry.latest_submission_id ? (
                              <Link
                                to={`/submissions/${entry.latest_submission_id}`}
                                className="btn btn-secondary"
                                style={{ padding: '4px 8px', fontSize: '12px' }}
                              >
                                View Code
                              </Link>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
    </>
  );
}

export default TeacherDashboardPage;

