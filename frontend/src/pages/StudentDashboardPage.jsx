/*
  src/pages/StudentDashboardPage.jsx — Student Performance Analytics Dashboard for LabCraft.

  Why this page exists (Module 6):
    Students need a centralized view to track their academic progress:
    - Overall completion rate (% of assigned lab work submitted)
    - Acceptance rate (% of submissions passing all test cases)
    - Cumulative marks earned vs. total marks possible across all enrolled classrooms
    - Detailed per-assignment status with direct 1-click links to the Monaco Code Editor
      and Submission History.
*/

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { getStudentDashboard } from '../services/api';
import { getUser } from '../utils/auth';
import { STATUS_COLORS, STATUS_DISPLAY } from '../utils/languageMap';

function StudentDashboardPage() {
  const user = getUser();

  // State to hold analytics returned by GET /api/analytics/student/dashboard/
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // Filter state for assignment table: 'all' | 'pending' | 'submitted'
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      setErrorMessage('');

      try {
        const response = await getStudentDashboard();
        setAnalytics(response.data);
      } catch (err) {
        const detail =
          err.response?.data?.detail ||
          'Failed to load student performance analytics. Please ensure you are logged in as a student.';
        setErrorMessage(detail);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="container">
          <LoadingSpinner message="Calculating your performance analytics..." />
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
            <h1>Student Dashboard</h1>
            <div className="error-msg">{errorMessage}</div>
            <Link to="/login" className="btn btn-secondary" style={{ marginTop: '12px' }}>
              Return to Login
            </Link>
          </div>
        </div>
      </>
    );
  }

  const { summary, status_distribution, classrooms = [], assignments = [] } = analytics || {};

  // Calculate filtered assignments for display
  const filteredAssignments = assignments.filter((a) => {
    if (filter === 'pending') return !a.is_submitted;
    if (filter === 'submitted') return a.is_submitted;
    return true;
  });

  // Calculate total non-zero statuses for proportional distribution bar
  const totalEvaluated =
    (status_distribution?.accepted || 0) +
    (status_distribution?.wrong_answer || 0) +
    (status_distribution?.time_limit_exceeded || 0) +
    (status_distribution?.runtime_error || 0) +
    (status_distribution?.compile_error || 0) +
    (status_distribution?.memory_limit_exceeded || 0);

  const completionRate =
    summary?.total_assignments > 0
      ? Math.round((summary.submitted_assignments / summary.total_assignments) * 100)
      : 0;

  return (
    <>
      <Navbar />
      <div className="container">
        {/* Page Title & Greeting */}
        <div style={{ marginBottom: '24px' }}>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>👋 Welcome back, {user?.username || 'Student'}!</span>
          </h1>
          <p className="subtitle">
            Here is your real-time learning progress, submission history, and assignment analytics.
          </p>
        </div>

        {/* Top Summary Metrics Grid */}
        <div className="stats-grid">
          {/* Card 1: Assignment Completion */}
          <div className="stat-card">
            <span className="stat-label">Assignments Completed</span>
            <div className="stat-val">
              {summary?.submitted_assignments || 0}
              <span style={{ fontSize: '16px', color: '#64748b', fontWeight: 500 }}>
                {' '}/ {summary?.total_assignments || 0}
              </span>
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{ width: `${completionRate}%` }}
              />
            </div>
            <span className="stat-sub">{completionRate}% Completion Rate</span>
          </div>

          {/* Card 2: Acceptance Rate */}
          <div className="stat-card">
            <span className="stat-label">Acceptance Rate</span>
            <div className="stat-val text-success">
              {summary?.acceptance_rate_percentage || 0}%
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary?.acceptance_rate_percentage || 0}%`,
                  background: '#10b981',
                }}
              />
            </div>
            <span className="stat-sub">
              {status_distribution?.accepted || 0} of {summary?.total_submissions || 0} submissions accepted
            </span>
          </div>

          {/* Card 3: Marks Earned */}
          <div className="stat-card">
            <span className="stat-label">Total Marks Earned</span>
            <div className="stat-val" style={{ color: '#3b82f6' }}>
              {summary?.total_marks_earned || 0}
              <span style={{ fontSize: '16px', color: '#64748b', fontWeight: 500 }}>
                {' '}/ {summary?.total_marks_possible || 0}
              </span>
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary?.average_score_percentage || 0}%`,
                  background: '#3b82f6',
                }}
              />
            </div>
            <span className="stat-sub">{summary?.average_score_percentage || 0}% Average Score</span>
          </div>

          {/* Card 4: Total Enrolled Classrooms */}
          <div className="stat-card">
            <span className="stat-label">Enrolled Classrooms</span>
            <div className="stat-val">{summary?.total_classrooms || 0}</div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#8b5cf6' }} />
            </div>
            <span className="stat-sub">Active course memberships</span>
          </div>
        </div>

        {/* Submission Outcome Distribution */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>📊 Submission Verdict Distribution</h2>
            <span className="text-muted" style={{ fontSize: '13px' }}>
              Total submissions evaluated: {totalEvaluated}
            </span>
          </div>
          <p className="subtitle" style={{ marginBottom: '12px' }}>
            Proportion of all test runner results across your coding submissions.
          </p>

          {/* Multi-segment distribution bar */}
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

              {/* Legend with exact counts */}
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
            <div style={{ padding: '20px 0', color: '#94a3b8', fontStyle: 'italic' }}>
              No submissions evaluated yet. Open an assignment below to write and test your code!
            </div>
          )}
        </div>

        {/* Enrolled Classrooms Grid */}
        <div style={{ marginBottom: '24px' }}>
          <h2>🏫 Enrolled Classrooms ({classrooms.length})</h2>
          {classrooms.length === 0 ? (
            <div className="card" style={{ color: '#94a3b8' }}>
              You are not currently enrolled in any approved classrooms. Ask your instructor for an invite code.
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '16px',
                marginTop: '12px',
              }}
            >
              {classrooms.map((c) => {
                const cRate =
                  c.total_assignments > 0
                    ? Math.round((c.submitted_assignments / c.total_assignments) * 100)
                    : 0;
                return (
                  <div key={c.id} className="card" style={{ marginBottom: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <h3 style={{ margin: 0, color: '#f8fafc' }}>{c.name}</h3>
                      <span
                        style={{
                          fontSize: '11px',
                          background: '#334155',
                          padding: '2px 8px',
                          borderRadius: '6px',
                          color: '#94a3b8',
                          fontWeight: 600,
                        }}
                      >
                        {c.code}
                      </span>
                    </div>
                    <div className="text-muted" style={{ fontSize: '13px', margin: '4px 0 12px 0' }}>
                      Instructor: <strong style={{ color: '#cbd5e1' }}>{c.teacher_name}</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                      <span>Assignments Progress</span>
                      <strong>{c.submitted_assignments} / {c.total_assignments} ({cRate}%)</strong>
                    </div>
                    <div className="progress-bar-bg" style={{ marginBottom: '12px' }}>
                      <div className="progress-bar-fill" style={{ width: `${cRate}%` }} />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                      <span>Marks Earned</span>
                      <strong style={{ color: '#3b82f6' }}>{c.earned_marks} / {c.possible_marks}</strong>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Assignment Performance & Action Table */}
        <div className="card">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '16px',
            }}
          >
            <div>
              <h2 style={{ margin: 0 }}>📝 Assignments & Submissions</h2>
              <p className="subtitle" style={{ margin: '4px 0 0 0' }}>
                Track deadlines, best scores, and launch the Monaco Code Editor.
              </p>
            </div>

            {/* Filter Buttons */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 14px', fontSize: '13px' }}
                onClick={() => setFilter('all')}
              >
                All ({assignments.length})
              </button>
              <button
                className={`btn ${filter === 'pending' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 14px', fontSize: '13px' }}
                onClick={() => setFilter('pending')}
              >
                Pending ({summary?.pending_assignments || 0})
              </button>
              <button
                className={`btn ${filter === 'submitted' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 14px', fontSize: '13px' }}
                onClick={() => setFilter('submitted')}
              >
                Submitted ({summary?.submitted_assignments || 0})
              </button>
            </div>
          </div>

          {filteredAssignments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
              No assignments found for the selected filter.
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Assignment Title</th>
                    <th>Classroom</th>
                    <th>Due Date</th>
                    <th>Best Verdict</th>
                    <th>Score</th>
                    <th>Attempts</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAssignments.map((a) => {
                    const dueDateStr = a.due_date
                      ? new Date(a.due_date).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : 'No deadline';

                    return (
                      <tr key={a.id}>
                        <td>
                          <strong style={{ color: '#f8fafc' }}>{a.title}</strong>
                        </td>
                        <td>
                          <span style={{ color: '#cbd5e1' }}>{a.classroom_name}</span>
                        </td>
                        <td>
                          <span style={{ fontSize: '13px', color: '#94a3b8' }}>{dueDateStr}</span>
                        </td>
                        <td>
                          {a.is_submitted ? (
                            <StatusBadge status={a.best_status} />
                          ) : (
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '3px 8px',
                                borderRadius: '12px',
                                fontSize: '11px',
                                background: '#334155',
                                color: '#94a3b8',
                                fontWeight: 600,
                              }}
                            >
                              ⏳ Not Submitted
                            </span>
                          )}
                        </td>
                        <td>
                          {a.is_submitted ? (
                            <strong style={{ color: a.best_score > 0 ? '#10b981' : '#e2e8f0' }}>
                              {a.best_score} / {a.max_score}
                            </strong>
                          ) : (
                            <span className="text-muted">— / {a.max_score}</span>
                          )}
                        </td>
                        <td>
                          <span style={{ fontSize: '13px' }}>{a.submission_count}</span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '8px' }}>
                            {a.is_submitted && (
                              <Link
                                to={`/assignments/${a.id}/submissions`}
                                className="btn btn-secondary"
                                style={{ padding: '6px 10px', fontSize: '12px' }}
                                title="View submission history and feedback"
                              >
                                History
                              </Link>
                            )}
                            <Link
                              to={`/assignments/${a.id}/submit`}
                              className={`btn ${a.is_submitted ? 'btn-secondary' : 'btn-primary'}`}
                              style={{ padding: '6px 12px', fontSize: '12px' }}
                            >
                              {a.is_submitted ? 'Resubmit' : 'Solve & Submit 💻'}
                            </Link>
                          </div>
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
    </>
  );
}

export default StudentDashboardPage;

