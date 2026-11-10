/*
  src/components/Navbar.jsx — Global navigation bar for LabCraft.

  Features:
    - LabCraft branding linking to home
    - Displays current logged-in user's username and role badge
    - Logout button calling logout() utility
*/

import React from 'react';
import { Link } from 'react-router-dom';
import { getUser, logout } from '../utils/auth';

function Navbar() {
  const user = getUser();
  const dashboardPath = user?.role === 'teacher' ? '/teacher/dashboard' : '/dashboard';

  return (
    <header className="navbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <Link to={user ? dashboardPath : '/login'} className="navbar-brand">
          ⚡ LabCraft
        </Link>
        {user && (
          <nav style={{ display: 'flex', gap: '12px' }}>
            <Link
              to={dashboardPath}
              className="btn btn-secondary"
              style={{
                padding: '6px 12px',
                fontSize: '13px',
                textDecoration: 'none',
              }}
            >
              📊 {user.role === 'teacher' ? 'Instructor Dashboard' : 'My Dashboard'}
            </Link>
          </nav>
        )}
      </div>

      <div className="navbar-actions">
        {user ? (
          <>
            <span className="text-muted" style={{ fontSize: '13px' }}>
              Logged in as: <strong style={{ color: '#f1f5f9' }}>{user.username}</strong>{' '}
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  backgroundColor: user.role === 'teacher' ? '#4338ca' : '#047857',
                  color: '#fff',
                  marginLeft: '4px',
                  textTransform: 'uppercase',
                  fontWeight: '700',
                }}
              >
                {user.role}
              </span>
            </span>
            <button
              onClick={logout}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              Sign Out
            </button>
          </>
        ) : (
          <Link to="/login" className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '13px' }}>
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
}

export default Navbar;

