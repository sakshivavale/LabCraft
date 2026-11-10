/*
  src/components/SubmissionStatus.js — Badge component for submission status.

  Displays a colored badge for the submission status:
    pending    → grey
    running    → blue (animated)
    accepted   → green ✅
    wrong_answer → red ❌
    runtime_error → orange
    compile_error → red
    time_limit_exceeded → yellow
    memory_limit_exceeded → purple

  WHY a separate component?
    Status badges appear in the history list AND the detail view.
    Making it a reusable component avoids duplicating the styling logic.
*/

import React from 'react';

/*
  STATUS_CONFIG maps each backend status value to:
    - label: human-friendly display text
    - color: CSS background color
    - emoji: a quick visual indicator
*/
const STATUS_CONFIG = {
  pending:               { label: 'Pending',               color: '#6b7280', emoji: '⏳' },
  running:               { label: 'Running',               color: '#3b82f6', emoji: '⚙️' },
  accepted:              { label: 'Accepted',              color: '#22c55e', emoji: '✅' },
  wrong_answer:          { label: 'Wrong Answer',          color: '#ef4444', emoji: '❌' },
  runtime_error:         { label: 'Runtime Error',         color: '#f97316', emoji: '💥' },
  compile_error:         { label: 'Compile Error',         color: '#dc2626', emoji: '🔴' },
  time_limit_exceeded:   { label: 'Time Limit Exceeded',   color: '#eab308', emoji: '⏱️' },
  memory_limit_exceeded: { label: 'Memory Limit Exceeded', color: '#a855f7', emoji: '📦' },
};

function SubmissionStatus({ status }) {
  /*
    If we receive an unknown status, fall back to a sensible default.
    This prevents the app from crashing if the backend adds a new status.
  */
  const config = STATUS_CONFIG[status] || { label: status, color: '#6b7280', emoji: '?' };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '3px 10px',
        borderRadius: '12px',         // pill-shaped badge
        backgroundColor: config.color,
        color: 'white',
        fontSize: '13px',
        fontWeight: '600',
        whiteSpace: 'nowrap',         // don't wrap the status text
      }}
    >
      {config.emoji} {config.label}
    </span>
  );
}

export default SubmissionStatus;
