// src/services/api.js — Centralised Axios instance and API helper functions
// All backend calls go through this module so auth headers are added automatically.

import axios from 'axios';

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------
// Create a dedicated instance so we don't pollute the global axios defaults.
// baseURL means every relative path like '/api/submissions/' resolves correctly.
const api = axios.create({
  baseURL: 'http://localhost:8000', // Django dev server address
});

// ---------------------------------------------------------------------------
// Request interceptor — attach the JWT access token to every outgoing request
// ---------------------------------------------------------------------------
api.interceptors.request.use(
  (config) => {
    // Read the access token that was stored in localStorage during login
    const token = localStorage.getItem('access');

    if (token) {
      // Authorization header format expected by djangorestframework-simplejwt
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    return config; // Return the (possibly modified) config to continue the request
  },
  (error) => {
    // If request setup itself fails, reject immediately so callers can catch it
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Response interceptor — handle expired / invalid tokens globally
// ---------------------------------------------------------------------------
api.interceptors.response.use(
  (response) => response, // Successful responses pass straight through

  (error) => {
    // 401 Unauthorized → token is missing, expired, or tampered
    if (error.response && error.response.status === 401) {
      // Wipe all stored credentials so the user can't stay in a broken state
      localStorage.clear();

      // Hard-redirect to login; using window.location instead of React Router
      // because interceptors live outside the React component tree and have no
      // access to useNavigate.
      window.location.href = '/login';
    }

    // Re-reject so individual callers can still handle other error codes (403, 404, etc.)
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Submission API helpers
// ---------------------------------------------------------------------------
// Each function wraps one API endpoint. Exporting named functions (not the raw
// axios instance) lets pages stay thin — they just call these functions and
// await the result.

/**
 * Student submits source code for an assignment.
 * POST /api/submissions/assignment/<assignmentId>/submit/
 * @param {number|string} assignmentId
 * @param {{ source_code: string, language: string }} data
 */
export const submitCode = (assignmentId, data) =>
  api.post(`/api/submissions/assignment/${assignmentId}/submit/`, data);

/**
 * Student fetches their own submission history for an assignment.
 * GET /api/submissions/assignment/<assignmentId>/my/
 * @param {number|string} assignmentId
 */
export const getMySubmissions = (assignmentId) =>
  api.get(`/api/submissions/assignment/${assignmentId}/my/`);

/**
 * Any user fetches the full detail of one submission by its ID.
 * GET /api/submissions/<id>/
 * @param {number|string} submissionId
 */
export const getSubmissionDetail = (submissionId) =>
  api.get(`/api/submissions/${submissionId}/`);

/**
 * Teacher fetches ALL submissions for an assignment (every student).
 * GET /api/submissions/assignment/<assignmentId>/all/
 * @param {number|string} assignmentId
 */
export const getTeacherSubmissions = (assignmentId) =>
  api.get(`/api/submissions/assignment/${assignmentId}/all/`);

/**
 * Teacher fetches one specific student's submissions for an assignment.
 * GET /api/submissions/assignment/<assignmentId>/student/<studentId>/
 * @param {number|string} assignmentId
 * @param {number|string} studentId
 */
export const getTeacherStudentSubmissions = (assignmentId, studentId) =>
  api.get(`/api/submissions/assignment/${assignmentId}/student/${studentId}/`);

/**
 * Student or Teacher fetches published assignment details.
 * GET /api/assignments/<assignmentId>/student/
 * @param {number|string} assignmentId
 */
export const getAssignment = (assignmentId) =>
  api.get(`/api/assignments/${assignmentId}/student/`);

/**
 * User login helper.
 * POST /api/auth/login/
 * @param {{ username: string, password: string }} credentials
 */
export const login = (credentials) =>
  api.post('/api/auth/login/', credentials);

// Export the raw instance too so pages can reach other endpoints (e.g. assignment details)
export default api;
