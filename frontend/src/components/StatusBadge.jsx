/*
  src/components/StatusBadge.jsx — Visual indicator badge for submission grading status.

  Why is this a separate component?
    Status badges are rendered in multiple places across the app:
    - CodeEditorPage (after a successful submission)
    - SubmissionHistoryPage (table rows for each attempt)
    - SubmissionDetailPage (header summary card)
    - TeacherSubmissionsPage (all student submissions table)
    Keeping it in a single component ensures consistent styling, colors,
    and emoji indicators everywhere.
*/

import React from 'react';
import { STATUS_COLORS, STATUS_DISPLAY } from '../utils/languageMap';

/**
 * StatusBadge component
 *
 * @param {Object} props
 * @param {string} props.status - Status slug from backend (e.g. 'pending', 'accepted', 'wrong_answer')
 */
function StatusBadge({ status }) {
  // Look up the hex color code for this status from our central map.
  // If the status is unrecognized, fall back to a neutral gray (#6b7280).
  const backgroundColor = STATUS_COLORS[status] || '#6b7280';

  // Look up the human-readable label with emoji (e.g. '✅ Accepted').
  // Fall back to the raw status string if not in the map.
  const displayLabel = STATUS_DISPLAY[status] || status;

  return (
    <span
      className="status-badge"
      style={{
        backgroundColor,
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.2)',
      }}
    >
      {displayLabel}
    </span>
  );
}

export default StatusBadge;

