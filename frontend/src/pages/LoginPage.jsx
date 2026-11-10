/*
  src/pages/LoginPage.jsx — User authentication page for students and teachers.

  How authentication works in LabCraft:
    1. User enters username and password.
    2. We send a POST request to /api/auth/login/.
    3. The Django backend validates credentials and returns:
       - access: short-lived JWT token (1 hour) sent with subsequent API calls
       - refresh: long-lived token (7 days) used to refresh the session
       - user: public profile info (id, username, email, role, is_approved)
    4. We store these values in browser localStorage so the session persists
       across page refreshes.
    5. Based on the user's role (student vs teacher), we redirect them to their
       appropriate landing view.
*/

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../services/api';
import Navbar from '../components/Navbar';

function LoginPage() {
  const navigate = useNavigate();

  // Controlled component state for username and password input fields
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // UI state for loading spinner and error alert
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  /**
   * Handle login form submission
   * @param {React.FormEvent} e - Form submit event
   */
  const handleSubmit = async (e) => {
    // Prevent the default browser behavior of submitting the form via a full page reload
    e.preventDefault();
    setErrorMessage('');

    // Client-side quick check
    if (!username.trim() || !password) {
      setErrorMessage('Please enter both username and password.');
      return;
    }

    setLoading(true);

    try {
      // POST /api/auth/login/
      const response = await login({ username: username.trim(), password });

      // Extract tokens and profile from backend response
      const { access, refresh, user } = response.data;

      // Store in localStorage for api.js request interceptor to pick up
      localStorage.setItem('access', access);
      localStorage.setItem('refresh', refresh);
      localStorage.setItem('user', JSON.stringify(user));

      // Redirect depending on user role
      if (user.role === 'teacher') {
        // Teachers land on the instructor multi-classroom dashboard
        navigate('/teacher/dashboard');
      } else {
        // Students land on their performance & assignment progress dashboard
        navigate('/dashboard');
      }
    } catch (err) {
      // Extract custom error message from DRF backend if available
      const backendError =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Login failed. Please check your username and password.';
      setErrorMessage(backendError);
    } finally {
      // Ensure loading state is turned off whether login succeeds or fails
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <div className="container" style={{ maxWidth: '440px', marginTop: '60px' }}>
        <div className="card">
          <h1 style={{ textAlign: 'center', marginBottom: '8px' }}>Sign In</h1>
          <p className="subtitle" style={{ textAlign: 'center' }}>
            Enter your credentials to access LabCraft
          </p>

          {/* Show error alert if login failed */}
          {errorMessage && <div className="error-msg">{errorMessage}</div>}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '14px' }}>
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                placeholder="e.g. alice or prof_smith"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                autoFocus
                required
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '15px' }}
              disabled={loading}
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          <hr className="divider" />

          <p style={{ fontSize: '12px', color: '#94a3b8', textAlign: 'center', lineHeight: '1.5' }}>
            Tip: For testing, use an enrolled student account to submit code, or an approved teacher
            account to review submissions.
          </p>
        </div>
      </div>
    </>
  );
}

export default LoginPage;

