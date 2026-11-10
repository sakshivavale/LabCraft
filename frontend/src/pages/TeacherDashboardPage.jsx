/*
  src/pages/TeacherDashboardPage.jsx — Teacher & Multi-Classroom Analytics Cockpit for LabCraft.

  Features (Module 6 + Classroom CRUD):
    - Multi-classroom analytics overview: enrolled students, acceptance rate, submissions
    - Complete Classroom CRUD:
        * "+ Create Classroom" button and modal
        * Display unique join code for students
        * "+ New Assignment" creation modal
        * Delete classroom option
    - Classroom Deep Dive Modal: Student leaderboard & assignment pass rates
    - Assignment Gradebook Modal: 5-tier score distribution histogram & roster
    - Recent student submissions live feed with 1-click code inspection
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
  createClassroom,
  deleteClassroom,
  createAssignment,
} from '../services/api';
import { getUser } from '../utils/auth';
import { STATUS_COLORS } from '../utils/languageMap';

function TeacherDashboardPage() {
  const user = getUser();

  // Root teacher dashboard state
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Classroom CRUD Modal State
  const [showCreateClassModal, setShowCreateClassModal] = useState(false);
  const [newClassName, setNewClassName] = useState('');
  const [newClassDesc, setNewClassDesc] = useState('');
  const [creatingClass, setCreatingClass] = useState(false);

  // Assignment CRUD Modal State
  const [assignmentModalClassId, setAssignmentModalClassId] = useState(null);
  const [assignmentTitle, setAssignmentTitle] = useState('');
  const [assignmentDesc, setAssignmentDesc] = useState('');
  const [assignmentInstructions, setAssignmentInstructions] = useState('');
  const [assignmentLang, setAssignmentLang] = useState('python');
  const [assignmentDifficulty, setAssignmentDifficulty] = useState('easy');
  const [assignmentMaxMarks, setAssignmentMaxMarks] = useState(100);
  const [assignmentDueDate, setAssignmentDueDate] = useState('');
  const [creatingAssignment, setCreatingAssignment] = useState(false);

  // Deep Dive Modal state
  const [selectedClassroomId, setSelectedClassroomId] = useState(null);
  const [classroomAnalytics, setClassroomAnalytics] = useState(null);
  const [loadingClassroom, setLoadingClassroom] = useState(false);

  const [selectedAssignmentId, setSelectedAssignmentId] = useState(null);
  const [assignmentAnalytics, setAssignmentAnalytics] = useState(null);
  const [loadingAssignment, setLoadingAssignment] = useState(false);

  // Fetch or re-fetch dashboard metrics
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

  useEffect(() => {
    fetchDashboard();
  }, []);

  // Handle Create Classroom
  const handleCreateClassroom = async (e) => {
    e.preventDefault();
    if (!newClassName.trim()) {
      alert('Please enter a classroom name.');
      return;
    }

    setCreatingClass(true);
    try {
      const response = await createClassroom({
        name: newClassName.trim(),
        description: newClassDesc.trim(),
      });

      const createdCode = response.data?.join_code || response.data?.classroom?.join_code;
      setSuccessMessage(
        `Classroom "${newClassName}" created successfully! Student Join Code: ${createdCode}`
      );
      setNewClassName('');
      setNewClassDesc('');
      setShowCreateClassModal(false);
      await fetchDashboard();
    } catch (err) {
      alert(err.response?.data?.detail || err.response?.data?.name?.[0] || 'Failed to create classroom.');
    } finally {
      setCreatingClass(false);
    }
  };

  // Handle Delete Classroom
  const handleDeleteClassroom = async (classroomId, className) => {
    if (!window.confirm(`Are you sure you want to delete classroom "${className}"? This will remove all associated assignments and student enrollments.`)) {
      return;
    }

    try {
      await deleteClassroom(classroomId);
      setSuccessMessage(`Classroom "${className}" was deleted.`);
      await fetchDashboard();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete classroom.');
    }
  };

  // Handle Create Assignment
  const handleCreateAssignment = async (e) => {
    e.preventDefault();
    if (!assignmentTitle.trim()) {
      alert('Please enter an assignment title.');
      return;
    }

    setCreatingAssignment(true);
    try {
      const payload = {
        title: assignmentTitle.trim(),
        description: assignmentDesc.trim() || 'Programming assignment',
        instructions: assignmentInstructions.trim() || 'Solve the problem and submit your solution.',
        language: assignmentLang,
        difficulty: assignmentDifficulty,
        max_marks: Number(assignmentMaxMarks) || 100,
        is_published: true,
      };

      if (assignmentDueDate) {
        payload.due_date = new Date(assignmentDueDate).toISOString();
      }

      await createAssignment(assignmentModalClassId, payload);
      setSuccessMessage(`Assignment "${assignmentTitle}" created successfully!`);
      setAssignmentModalClassId(null);
      setAssignmentTitle('');
      setAssignmentDesc('');
      setAssignmentInstructions('');
      await fetchDashboard();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create assignment.');
    } finally {
      setCreatingAssignment(false);
    }
  };

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

  // Normalize data schemas to handle both backend field variants seamlessly
  const rawSummary = dashboardData?.summary || {};
  const rawClassrooms = dashboardData?.classrooms_overview || dashboardData?.classrooms || [];
  const status_distribution = dashboardData?.status_distribution || {};
  const recent_submissions = dashboardData?.recent_submissions || [];

  const summary = {
    total_classrooms: rawSummary.total_classrooms ?? rawClassrooms.length,
    total_enrolled_students: rawSummary.total_students_enrolled ?? rawSummary.total_enrolled_students ?? 0,
    total_assignments: rawSummary.published_assignments ?? rawSummary.total_assignments ?? 0,
    total_submissions: rawSummary.total_submissions_received ?? rawSummary.total_submissions ?? 0,
    overall_acceptance_rate: rawSummary.overall_acceptance_rate ?? 0,
    overall_average_score: rawSummary.overall_average_score ?? 0,
  };

  const classrooms = rawClassrooms.map((c) => ({
    id: c.id ?? c.classroom_id,
    name: c.name ?? c.classroom_name,
    code: c.join_code ?? c.code ?? '',
    enrolled_student_count: c.student_count ?? c.enrolled_student_count ?? 0,
    assignment_count: c.total_assignments ?? c.assignment_count ?? 0,
    total_submissions: c.total_submissions ?? 0,
    submission_rate_percentage:
      c.submission_rate_percentage ??
      (c.student_count > 0 && c.total_assignments > 0
        ? Math.min(100, Math.round((c.total_submissions / (c.student_count * c.total_assignments)) * 100))
        : 0),
    average_score: c.average_score ?? 0,
    is_active: c.is_active ?? true,
  }));

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

        {/* Header with Title and Create Classroom CTA */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
          <div>
            <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <span>🎓 Instructor Analytics Cockpit</span>
            </h1>
            <p className="subtitle" style={{ margin: '4px 0 0 0' }}>
              Welcome, Prof. {user?.username || 'Teacher'}. Real-time student performance, classroom management, and gradebooks.
            </p>
          </div>

          {/* Primary Action: Create Classroom */}
          <button
            onClick={() => setShowCreateClassModal(true)}
            className="btn btn-primary"
            style={{ padding: '10px 18px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <span>➕</span> Create New Classroom
          </button>
        </div>

        {/* Top Summary Metrics */}
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Active Classrooms</span>
            <div className="stat-val" style={{ color: '#8b5cf6' }}>
              {summary.total_classrooms}
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#8b5cf6' }} />
            </div>
            <span className="stat-sub">Teaching workspaces</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Enrolled Students</span>
            <div className="stat-val" style={{ color: '#3b82f6' }}>
              {summary.total_enrolled_students}
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#3b82f6' }} />
            </div>
            <span className="stat-sub">Active learners across courses</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Total Submissions</span>
            <div className="stat-val">
              {summary.total_submissions}
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '100%', background: '#06b6d4' }} />
            </div>
            <span className="stat-sub">{summary.total_assignments} published assignments</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Overall Acceptance Rate</span>
            <div className="stat-val text-success">
              {summary.overall_acceptance_rate}%
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary.overall_acceptance_rate}%`,
                  background: '#10b981',
                }}
              />
            </div>
            <span className="stat-sub">{status_distribution?.accepted || 0} accepted runs</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Average Score</span>
            <div className="stat-val" style={{ color: '#f59e0b' }}>
              {summary.overall_average_score}%
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${summary.overall_average_score}%`,
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

        {/* Classroom Management & Performance Grid */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div>
              <h2 style={{ margin: 0 }}>🏫 Classroom Performance & Management ({classrooms.length})</h2>
              <p className="subtitle" style={{ margin: '4px 0 0 0' }}>
                Share the 8-character join code with students to invite them to your classrooms.
              </p>
            </div>
            <button
              onClick={() => setShowCreateClassModal(true)}
              className="btn btn-secondary"
              style={{ fontSize: '13px', padding: '6px 14px' }}
            >
              + Add Classroom
            </button>
          </div>

          {classrooms.length === 0 ? (
            <div className="card" style={{ color: '#94a3b8', textAlign: 'center', padding: '36px' }}>
              <p style={{ fontSize: '16px', marginBottom: '12px' }}>You do not have any active classrooms yet.</p>
              <button onClick={() => setShowCreateClassModal(true)} className="btn btn-primary">
                Create Your First Classroom
              </button>
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
                gap: '16px',
                marginTop: '12px',
              }}
            >
              {classrooms.map((c) => (
                <div key={c.id} className="card" style={{ marginBottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '18px' }}>{c.name}</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                          <span className="text-muted" style={{ fontSize: '12px' }}>Join Code:</span>
                          <code
                            style={{
                              background: '#0f172a',
                              border: '1px solid #334155',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '13px',
                              color: '#38bdf8',
                              fontWeight: 700,
                              letterSpacing: '1px',
                            }}
                          >
                            {c.code}
                          </code>
                        </div>
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
                  </div>

                  {/* Actions for this Classroom */}
                  <div style={{ borderTop: '1px solid #334155', paddingTop: '12px', marginTop: '12px' }}>
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                      <button
                        onClick={() => handleOpenClassroom(c.id)}
                        className="btn btn-primary"
                        style={{ flex: 1, padding: '7px 10px', fontSize: '12px', textAlign: 'center' }}
                      >
                        Leaderboard & Stats 📈
                      </button>
                      <button
                        onClick={() => setAssignmentModalClassId(c.id)}
                        className="btn btn-success"
                        style={{ padding: '7px 10px', fontSize: '12px' }}
                        title="Create a new assignment for this classroom"
                      >
                        + New Lab 📝
                      </button>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => handleDeleteClassroom(c.id, c.name)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#ef4444',
                          fontSize: '12px',
                          cursor: 'pointer',
                          padding: '2px 4px',
                        }}
                      >
                        🗑️ Delete Classroom
                      </button>
                    </div>
                  </div>
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
                          <strong style={{ color: '#f8fafc' }}>
                            {sub.student_username || sub.student?.username || 'Student'}
                          </strong>
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
                            {sub.score !== null && sub.score !== undefined ? `${sub.score} / ${sub.max_score || 100}` : '—'}
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
      {/* 1. Modal: Create New Classroom */}
      {/* --------------------------------------------------------------------- */}
      {showCreateClassModal && (
        <div className="modal-overlay" onClick={() => setShowCreateClassModal(false)}>
          <div className="modal-content" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ margin: 0 }}>➕ Create Classroom</h2>
              <button onClick={() => setShowCreateClassModal(false)} className="btn btn-secondary" style={{ padding: '4px 8px' }}>
                ✕
              </button>
            </div>

            <p className="subtitle" style={{ marginBottom: '16px' }}>
              Create a new teaching workspace. A unique 8-character join code will be generated automatically.
            </p>

            <form onSubmit={handleCreateClassroom}>
              <div style={{ marginBottom: '14px' }}>
                <label htmlFor="className">Classroom Name *</label>
                <input
                  id="className"
                  type="text"
                  placeholder="e.g. Data Structures & Algorithms (CS 201)"
                  value={newClassName}
                  onChange={(e) => setNewClassName(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label htmlFor="classDesc">Course Description (Optional)</label>
                <textarea
                  id="classDesc"
                  rows="3"
                  placeholder="Brief overview or syllabus details for students..."
                  value={newClassDesc}
                  onChange={(e) => setNewClassDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateClassModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingClass}
                  className="btn btn-primary"
                >
                  {creatingClass ? 'Creating...' : 'Create Classroom'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 2. Modal: Create New Assignment */}
      {/* --------------------------------------------------------------------- */}
      {assignmentModalClassId && (
        <div className="modal-overlay" onClick={() => setAssignmentModalClassId(null)}>
          <div className="modal-content" style={{ maxWidth: '580px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ margin: 0 }}>📝 Create New Assignment</h2>
              <button onClick={() => setAssignmentModalClassId(null)} className="btn btn-secondary" style={{ padding: '4px 8px' }}>
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateAssignment}>
              <div style={{ marginBottom: '12px' }}>
                <label htmlFor="assignTitle">Assignment Title *</label>
                <input
                  id="assignTitle"
                  type="text"
                  placeholder="e.g. Binary Search Tree Insertion"
                  value={assignmentTitle}
                  onChange={(e) => setAssignmentTitle(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label htmlFor="assignLang">Language</label>
                  <select
                    id="assignLang"
                    value={assignmentLang}
                    onChange={(e) => setAssignmentLang(e.target.value)}
                  >
                    <option value="python">Python</option>
                    <option value="java">Java</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                    <option value="javascript">JavaScript</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="assignDifficulty">Difficulty</label>
                  <select
                    id="assignDifficulty"
                    value={assignmentDifficulty}
                    onChange={(e) => setAssignmentDifficulty(e.target.value)}
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label htmlFor="assignMaxMarks">Max Marks</label>
                  <input
                    id="assignMaxMarks"
                    type="number"
                    min="1"
                    value={assignmentMaxMarks}
                    onChange={(e) => setAssignmentMaxMarks(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="assignDueDate">Due Date & Time (Optional)</label>
                  <input
                    id="assignDueDate"
                    type="datetime-local"
                    value={assignmentDueDate}
                    onChange={(e) => setAssignmentDueDate(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label htmlFor="assignDesc">Problem Statement</label>
                <textarea
                  id="assignDesc"
                  rows="2"
                  placeholder="Explain the problem and constraints..."
                  value={assignmentDesc}
                  onChange={(e) => setAssignmentDesc(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label htmlFor="assignInstructions">Input / Output Instructions</label>
                <textarea
                  id="assignInstructions"
                  rows="2"
                  placeholder="e.g. Read n lines from stdin and print the result to stdout..."
                  value={assignmentInstructions}
                  onChange={(e) => setAssignmentInstructions(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setAssignmentModalClassId(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingAssignment}
                  className="btn btn-primary"
                >
                  {creatingAssignment ? 'Publishing...' : 'Publish Assignment 🚀'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* 3. Modal: Classroom Analytics & Leaderboard */}
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
                      🏫 {classroomAnalytics.classroom?.name} ({classroomAnalytics.classroom?.join_code || classroomAnalytics.classroom?.code})
                    </h2>
                    <span className="text-muted" style={{ fontSize: '13px' }}>
                      Enrolled: {classroomAnalytics.classroom?.enrolled_student_count || classroomAnalytics.metrics?.enrolled_students || 0} students
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
                <div className="table-wrapper" style={{ maxHeight: '280px', overflowY: 'auto', marginBottom: '24px' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Student</th>
                        <th>Email</th>
                        <th>Completed Labs</th>
                        <th>Total Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(classroomAnalytics.leaderboard || []).length === 0 ? (
                        <tr>
                          <td colSpan="5" style={{ textAlign: 'center', color: '#94a3b8', padding: '16px' }}>
                            No student scores recorded yet in this classroom.
                          </td>
                        </tr>
                      ) : (
                        classroomAnalytics.leaderboard.map((s, idx) => (
                          <tr key={s.student_id || idx}>
                            <td>
                              <strong>
                                {idx === 0 ? '🥇 1' : idx === 1 ? '🥈 2' : idx === 2 ? '🥉 3' : idx + 1}
                              </strong>
                            </td>
                            <td>
                              <strong style={{ color: '#f8fafc' }}>{s.username || s.student_username}</strong>
                            </td>
                            <td>
                              <span className="text-muted">{s.email || s.student_email}</span>
                            </td>
                            <td>{s.assignments_completed ?? 0}</td>
                            <td>
                              <strong style={{ color: '#3b82f6' }}>{s.total_score ?? 0}</strong>
                            </td>
                          </tr>
                        ))
                      )}
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
                        <th>Average Score</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(classroomAnalytics.assignments_breakdown || classroomAnalytics.assignments || []).map((a) => (
                        <tr key={a.id}>
                          <td>
                            <strong style={{ color: '#f8fafc' }}>{a.title}</strong>
                          </td>
                          <td>{a.max_marks || a.max_score}</td>
                          <td>{a.unique_students_submitted ?? 0}</td>
                          <td>
                            <strong style={{ color: '#3b82f6' }}>{a.average_score ?? 0}%</strong>
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
      {/* 4. Modal: Assignment Analytics & Gradebook */}
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
                      Max Score: {assignmentAnalytics.assignment?.max_marks || assignmentAnalytics.assignment?.max_score}
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
                      {(assignmentAnalytics.student_gradebook || assignmentAnalytics.gradebook || []).map((entry) => (
                        <tr key={entry.student_id}>
                          <td>
                            <strong style={{ color: '#f8fafc' }}>
                              {entry.username || entry.student_username}
                            </strong>
                          </td>
                          <td>
                            <span className="text-muted">{entry.email || entry.student_email}</span>
                          </td>
                          <td>
                            {entry.has_submitted || entry.submitted ? (
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
                            {entry.has_submitted || entry.submitted ? (
                              <StatusBadge status={entry.best_status || entry.latest_status} />
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td>
                            <strong>{entry.best_score ?? 0}</strong>
                          </td>
                          <td>{entry.attempts_count ?? 0}</td>
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
