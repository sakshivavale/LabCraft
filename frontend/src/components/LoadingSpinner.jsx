/*
  src/components/LoadingSpinner.jsx — Reusable loading spinner with explanatory text.

  Why is this a separate component?
    Any asynchronous data fetch (fetching assignment details, loading submissions,
    submitting source code) takes time over the network.
    Providing clear visual feedback prevents students/teachers from thinking the app
    is stuck and prevents duplicate button clicks.
*/

import React from 'react';

/**
 * LoadingSpinner component
 *
 * @param {Object} props
 * @param {string} [props.message='Loading...'] - Optional custom text shown next to spinner
 */
function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="loading-wrap" role="status" aria-live="polite">
      {/* Animated spinning ring defined in global.css */}
      <div className="spinner" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export default LoadingSpinner;

