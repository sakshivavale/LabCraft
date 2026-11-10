// src/utils/auth.js — Authentication helper functions
// Centralises all localStorage reads/writes related to the logged-in user so
// every component gets user data the same way and we only change this one file
// if the storage schema ever changes.

/**
 * Parse and return the user object stored after login.
 * Returns null if no user is in localStorage (not logged in).
 */
export function getUser() {
  try {
    // localStorage.getItem returns null when the key doesn't exist
    const raw = localStorage.getItem('user');
    // JSON.parse(null) throws, so guard with the truthiness check
    return raw ? JSON.parse(raw) : null;
  } catch {
    // Corrupted JSON → treat as logged-out rather than crashing
    return null;
  }
}

/**
 * Return the role string ('student' | 'teacher') of the current user.
 * Returns null when no user is logged in.
 */
export function getRole() {
  const user = getUser();
  return user ? user.role : null;
}

/**
 * Convenience check: is the logged-in user a student?
 */
export function isStudent() {
  return getRole() === 'student';
}

/**
 * Convenience check: is the logged-in user a teacher?
 */
export function isTeacher() {
  return getRole() === 'teacher';
}

/**
 * Log the user out by clearing all credentials from localStorage, then
 * redirect to the login page.
 * Uses window.location so it works both inside and outside React components.
 */
export function logout() {
  // Remove every key set during login (access token, refresh token, user object)
  localStorage.removeItem('access');
  localStorage.removeItem('refresh');
  localStorage.removeItem('user');

  // Hard-navigate to /login — this also resets all React state automatically
  window.location.href = '/login';
}
