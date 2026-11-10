/*
  src/pages/StudentDashboardPage.jsx — Student Performance Analytics Dashboard for LabCraft.

  Features (Module 6 + Join Classroom):
    - Learning progress metrics: assignments completed, acceptance rate, marks earned
    - Real-time submission outcome distribution (AC, WA, TLE, RE, CE)
    - "+ Join Classroom with Code" modal to enroll into new courses using teacher's 8-character join code
    - Enrolled classrooms cards with instructor info and progress
    - Unified assignments table with filters (All / Pending / Submitted) and direct 1-click links
      to launch the Monaco Code Editor or review past submission histories.
*/

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { getStudentDashboard, joinClassroom } from '../services/api';
import { getUser } from '../utils/auth';
import { STATUS_COLORS } from '../utils/languageMap';

function StudentDashboardPage() {
  const user = getUser();

  // State to hold analytics returned by GET /api/analytics/student/dashboard/
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Join Classroom Modal State
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCodeInput, setJoinCodeInput] = useState('');
  const [joiningClass, setJoiningClass] = useState(false);

  // Filter state for assignment table: 'all' | 'pending' | 'submitted'
  const [filter, setFilter] = useState('all');

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

  useEffect(() => {
    fetchDashboard();
  }, []);

  // Handle Join Classroom
  const handleJoinClassroom = async (e) => {
    e.preventDefault();
    const cleanCode = joinCodeInput.trim().toUpperCase();
    if (!cleanCode) {
      alert('Please enter an 8-character join code.');
      return;
    }

    setJoiningClass(true);
    try {
      const response = await joinClassroom(cleanCode);
      const joinedClassName = response.data?.classroom?.name || 'classroom';
      setSuccessMessage(`Successfully joined "${joinedClassName}"!`);
      setJoinCodeInput('');
      setShowJoinModal(false);
      await fetchDashboard();
    } catch (err) {
      alert(err.response?.data?.detail || err.response?.data?.join_code?.[0] || 'Failed to join classroom. Please check your join code.');
    } finally {
      setJoiningClass(false);
    }
  };

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

  // Normalize data schemas to handle both backend field variants seamlessly
  const rawSummary = analytics?.summary || {};
  const rawClassrooms = analytics?.classrooms || [];
  const rawAssignments = analytics?.per_assignment_breakdown || analytics?.assignments || [];
  const status_distribution = analytics?.status_distribution || {};

  const summary = {
    total_classrooms: rawSummary.enrolled_classrooms_count ?? rawSummary.total_classrooms ?? rawClassrooms.length,
    submitted_assignments: rawSummary.assignments_submitted ?? rawSummary.submitted_assignments ?? 0,
    total_assignments: rawSummary.total_assignments_available ?? rawSummary.total_assignments ?? rawAssignments.length,
    pending_assignments: rawSummary.assignments_pending ?? rawSummary.pending_assignments ?? 0,
    total_submissions: rawSummary.total_submissions ?? 0,
    acceptance_rate_percentage: rawSummary.acceptance_rate ?? rawSummary.acceptance_rate_percentage ?? 0,
    total_marks_earned: rawSummary.total_score_earned ?? rawSummary.total_marks_earned ?? 0,
    total_marks_possible: rawSummary.total_possible_marks ?? rawSummary.total_marks_possible ?? 0,
    average_score_percentage: rawSummary.overall_average_score_percentage ?? rawSummary.average_score_percentage ?? 0,
  };

  const classrooms = rawClassrooms.map((c) => ({
    id: c.classroom_id ?? c.id,
    name: c.classroom_name ?? c.name,
    code: c.join_code ?? c.code ?? '',
    teacher_name: c.teacher_name ?? 'Instructor',
    total_assignments: c.total_assignments ?? 0,
    submitted_assignments: c.submitted_assignments ?? 0,
    earned_marks: c.total_marks_earned ?? c.earned_marks ?? 0,
    possible_marks: c.max_marks_possible ?? c.possible_marks ?? 0,
  }));

  const assignments = rawAssignments.map((a) => ({
    id: a.assignment_id ?? a.id,
    title: a.assignment_title ?? a.title,
    classroom_name: a.classroom_name ?? '',
    due_date: a.due_date,
    is_submitted: a.submitted ?? a.is_submitted ?? false,
    submission_count: a.attempts_count ?? a.submission_count ?? 0,
    best_status: a.latest_status ?? a.best_status ?? null,
    best_score: a.best_score ?? 0,
    max_score: a.max_marks ?? a.max_score ?? 100,
  }));

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
    summary.total_assignments > 0
      ? Math.round((summary.submitted_assignments / summary.total_assignments) * 100)
      : 0;

  return (
    <>
      <Navbar />
      <div className="container">
        {/* Success Alert Banner */}
        {successMessage && (
          <div className="success-msg" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{successMessage}</span>
            <button
              onClick={() => setSuccessMessage('')}
              style={{ background: 'none', border: 'none', color: '#10b981', cursor: 'pointer', fontWeight: 700 }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Page Title & Join Classroom CTA */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
          <div>
            <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <span>👋 Welcome back, {user?.username || 'Student'}!</span>
            </h1>
            <p className="subtitle" style={{ margin: '4px 0 0 0' }}>
              Here is your real-time learning progress, enrolled courses, and assignment tasks.
            </p>
          </div>

          {/* Join Classroom CTA Button */}
          <button
            onClick={() => setShowJoinModal(true)}
            className="btn btn-success"
            style={{ padding: '10px 18px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <span>🔑</span> Join Classroom with Code
          </button>
        </div>

        {/* Top Summary Metrics Grid */}
        <div className="stats-grid">
          {/* Card 1: Assignment Completion */}
          <div className="stat-card">
            <span className="stat-label">Assignments Completed</span>
            <div className="stat-val">
              {summary.submitted_assignments}
              <span style={{ fontSize: '16px', color: '#64748b', fontWeight: 500 }}>
                {' '}/ {summary.total_assignments}
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
              {summary.acceptance_rate_percentage}%
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary.acceptance_rate_percentage}%`,
                  background: '#10b981',
                }}
              />
            </div>
            <span className="stat-sub">
              {status_distribution?.accepted || 0} of {summary.total_submissions} submissions accepted
            </span>
          </div>

          {/* Card 3: Marks Earned */}
          <div className="stat-card">
            <span className="stat-label">Total Marks Earned</span>
            <div className="stat-val" style={{ color: '#3b82f6' }}>
              {summary.total_marks_earned}
              <span style={{ fontSize: '16px', color: '#64748b', fontWeight: 500 }}>
                {' '}/ {summary.total_marks_possible}
              </span>
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary.average_score_percentage}%`,
                  background: '#3b82f6',
                }}
              />
            </div>
            <span className="stat-sub">{summary.average_score_percentage}% Average Score</span>
          </div>

          {/* Card 4: Total Enrolled Classrooms */}
          <div className="stat-card">
            <span className="stat-label">Enrolled Classrooms</span>
            <div className="stat-val">{summary.total_classrooms}</div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h2 style={{ margin: 0 }}>🏫 Enrolled Classrooms ({classrooms.length})</h2>
            <button
              onClick={() => setShowJoinModal(true)}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '5px 12px' }}
            >
              + Join Another Class
            </button>
          </div>

          {classrooms.length === 0 ? (
            <div className="card" style={{ color: '#94a3b8', textAlign: 'center', padding: '36px' }}>
              <p style={{ fontSize: '16px', marginBottom: '12px' }}>
                You are not enrolled in any classrooms yet.
              </p>
              <button onClick={() => setShowJoinModal(true)} className="btn btn-success">
                Enter an 8-Character Join Code
              </button>
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
                      <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '18px' }}>{c.name}</h3>
                      {c.code && (
                        <span
                          style={{
                            fontSize: '11px',
                            background: '#334155',
                            padding: '2px 8px',
                            borderRadius: '6px',
                            color: '#38bdf8',
                            fontWeight: 700,
                            letterSpacing: '1px',
                          }}
                        >
                          {c.code}
                        </span>
                      )}
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
              <h2 style={{ margin: 0 }}>📝 Assignments & Coding Tasks ({assignments.length})</h2>
              <p className="subtitle" style={{ margin: '4px 0 0 0' }}>
                Solve programming tasks directly inside the Monaco Code Editor.
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
                Pending ({summary.pending_assignments})
              </button>
              <button
                className={`btn ${filter === 'submitted' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 14px', fontSize: '13px' }}
                onClick={() => setFilter('submitted')}
              >
                Submitted ({summary.submitted_assignments})
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
                    <th>Status</th>
                    <th>Best Score</th>
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

      {/* --------------------------------------------------------------------- */}
      {/* Modal: Join Classroom with Code */}
      {/* --------------------------------------------------------------------- */}
      {showJoinModal && (
        <div className="modal-overlay" onClick={() => setShowJoinModal(false)}>
          <div className="modal-content" style={{ maxWidth: '440px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ margin: 0 }}>🔑 Join a Classroom</h2>
              <button onClick={() => setShowJoinModal(false)} className="btn btn-secondary" style={{ padding: '4px 8px' }}>
                ✕
              </button>
            </div>

            <p className="subtitle" style={{ marginBottom: '16px' }}>
              Ask your teacher for the 8-character classroom join code and paste it below.
            </p>

            <form onSubmit={handleJoinClassroom}>
              <div style={{ marginBottom: '20px' }}>
                <label htmlFor="joinCode">Classroom Join Code *</label>
                <input
                  id="joinCode"
                  type="text"
                  placeholder="e.g. F7FF660A"
                  maxLength={8}
                  style={{ textTransform: 'uppercase', letterSpacing: '2px', fontSize: '18px', fontWeight: 700 }}
                  value={joinCodeInput}
                  onChange={(e) => setJoinCodeInput(e.target.value.toUpperCase())}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowJoinModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={joiningClass}
                  className="btn btn-success"
                >
                  {joiningClass ? 'Joining...' : 'Join Classroom'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

export default StudentDashboardPage;
