// src/utils/languageMap.js — Display labels and Monaco language IDs
// Keeping these mappings in one place means every component that needs to
// translate a backend language slug (e.g. "cpp") to a human label or a Monaco
// mode string imports from here — no magic strings scattered across the app.

/**
 * Maps backend language slugs → human-readable display names
 * Used in dropdowns and table cells.
 */
export const LANGUAGE_DISPLAY = {
  python:     'Python',
  java:       'Java',
  c:          'C',
  cpp:        'C++',
  javascript: 'JavaScript',
  other:      'Other',
};

/**
 * Maps backend language slugs → Monaco Editor language identifiers
 * Monaco uses these strings to enable syntax highlighting and intellisense.
 * 'plaintext' is the Monaco fallback when no grammar is available.
 */
export const MONACO_LANGUAGE = {
  python:     'python',
  java:       'java',
  c:          'c',
  cpp:        'cpp',
  javascript: 'javascript',
  other:      'plaintext', // Monaco doesn't have an "other" mode — fall back to plain
};

/**
 * Maps submission status values → hex colour codes for status badges.
 * Colour semantics:
 *   amber  (#f59e0b) — still processing (pending / running)
 *   green  (#10b981) — correct answer
 *   red    (#ef4444) — incorrect or errored
 *   orange (#f97316) — resource limit exceeded
 */
export const STATUS_COLORS = {
  pending:              '#f59e0b',
  running:              '#3b82f6',
  accepted:             '#10b981',
  wrong_answer:         '#ef4444',
  runtime_error:        '#ef4444',
  compile_error:        '#ef4444',
  time_limit_exceeded:  '#f97316',
  memory_limit_exceeded:'#f97316',
};

/**
 * Maps submission status values → emoji + human-readable labels
 * Emoji give an at-a-glance visual cue without relying solely on colour
 * (improves accessibility for colour-blind users).
 */
export const STATUS_DISPLAY = {
  pending:              '⏳ Pending',
  running:              '🔄 Running',
  accepted:             '✅ Accepted',
  wrong_answer:         '❌ Wrong Answer',
  runtime_error:        '💥 Runtime Error',
  compile_error:        '🔧 Compile Error',
  time_limit_exceeded:  '⏰ Time Limit Exceeded',
  memory_limit_exceeded:'📦 Memory Limit Exceeded',
};
