/*
  src/pages/CodeEditorPage.jsx — Code Editor & Submission interface for students.

  Features:
    1. Monaco Editor integration (VS Code dark theme, syntax highlighting, line numbers).
    2. Dynamic language selection matching assignment requirements (locked to required language,
       or selectable if assignment language is 'other').
    3. Code draft auto-save to browser localStorage so student doesn't lose code on accidental reload.
    4. Code submission via POST /api/submissions/assignment/<id>/submit/.
    5. Deadline enforcement display (blocks submission if assignment due date has passed).
    6. Success confirmation and direct link to submission history.
*/

import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';

import Navbar from '../components/Navbar';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { getAssignment, submitCode } from '../services/api';
import { MONACO_LANGUAGE, LANGUAGE_DISPLAY } from '../utils/languageMap';
import { isStudent } from '../utils/auth';

// Starter templates for each programming language to help students get started
const STARTER_CODE = {
  python: `# Python 3 solution\n\ndef main():\n    # Write your code here\n    print("Hello from LabCraft!")\n\nif __name__ == "__main__":\n    main()\n`,
  java: `// Java solution\nimport java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        // Write your code here\n        System.out.println("Hello from LabCraft!");\n    }\n}\n`,
  c: `/* C solution */\n#include <stdio.h>\n\nint main() {\n    // Write your code here\n    printf("Hello from LabCraft!\\n");\n    return 0;\n}\n`,
  cpp: `// C++ solution\n#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    cout << "Hello from LabCraft!" << endl;\n    return 0;\n}\n`,
  javascript: `// JavaScript (Node.js) solution\n\nfunction main() {\n    // Write your code here\n    console.log("Hello from LabCraft!");\n}\n\nmain();\n`,
  other: `# Plain text or other language\n`,
};

function CodeEditorPage() {
  const { assignmentId } = useParams();
  const navigate = useNavigate();

  // Assignment details fetched from backend
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  // Selected language for submission
  const [selectedLanguage, setSelectedLanguage] = useState('python');

  // Source code currently in the Monaco editor
  const [sourceCode, setSourceCode] = useState('');

  // Draft save status notification ("Draft saved")
  const [saveMessage, setSaveMessage] = useState('');

  // Submission network status
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(null);
  const [submitError, setSubmitError] = useState('');

  // ---------------------------------------------------------------------------
  // Load assignment details on mount or when assignmentId changes
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchAssignmentDetails = async () => {
      setLoading(true);
      setLoadError('');

      try {
        // GET /api/assignments/<assignmentId>/student/
        const response = await getAssignment(assignmentId);
        const data = response.data;
        setAssignment(data);

        // Determine initial language
        const initialLang = data.language === 'other' ? 'python' : data.language;
        setSelectedLanguage(initialLang);

        // Check if there is saved code in localStorage for this assignment
        const storageKey = `labcraft_draft_${assignmentId}`;
        const savedDraft = localStorage.getItem(storageKey);

        if (savedDraft) {
          setSourceCode(savedDraft);
          setSaveMessage('Restored your previously saved draft.');
        } else {
          // Fall back to starter template for the assignment's language
          setSourceCode(STARTER_CODE[initialLang] || STARTER_CODE.python);
        }
      } catch (err) {
        const errorDetail =
          err.response?.data?.detail ||
          'Failed to load assignment. Ensure you are enrolled in this classroom.';
        setLoadError(errorDetail);
      } finally {
        setLoading(false);
      }
    };

    fetchAssignmentDetails();
  }, [assignmentId]);

  // ---------------------------------------------------------------------------
  // Save draft code to localStorage
  // ---------------------------------------------------------------------------
  const handleSaveDraft = () => {
    const storageKey = `labcraft_draft_${assignmentId}`;
    localStorage.setItem(storageKey, sourceCode);
    setSaveMessage('Draft saved locally in your browser!');

    // Fade out save indicator after 3 seconds
    setTimeout(() => {
      setSaveMessage('');
    }, 3000);
  };

  // ---------------------------------------------------------------------------
  // Switch programming language (when assignment language is 'other')
  // ---------------------------------------------------------------------------
  const handleLanguageChange = (e) => {
    const newLang = e.target.value;
    setSelectedLanguage(newLang);

    // If editor has default code from previous language, switch to new template
    const currentIsStarter = Object.values(STARTER_CODE).some((snippet) => snippet === sourceCode);
    if (!sourceCode.trim() || currentIsStarter) {
      setSourceCode(STARTER_CODE[newLang] || '');
    }
  };

  // ---------------------------------------------------------------------------
  // Submit code to backend
  // ---------------------------------------------------------------------------
  const handleSubmit = async () => {
    setSubmitError('');
    setSubmitSuccess(null);

    // Validation: prevent submitting empty code
    if (!sourceCode || !sourceCode.trim()) {
      setSubmitError('Source code cannot be empty. Please write your code before submitting.');
      return;
    }

    setSubmitting(true);

    try {
      // POST /api/submissions/assignment/<id>/submit/
      const payload = {
        source_code: sourceCode,
        language: selectedLanguage,
      };

      const response = await submitCode(assignmentId, payload);
      setSubmitSuccess(response.data);

      // Auto-save submitted version in localStorage draft
      localStorage.setItem(`labcraft_draft_${assignmentId}`, sourceCode);

      // Scroll smoothly to top so student sees confirmation
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      // Format backend error response
      const errData = err.response?.data;
      if (errData?.error) {
        setSubmitError(errData.error);
      } else if (errData?.source_code) {
        setSubmitError(errData.source_code[0]);
      } else if (errData?.language) {
        setSubmitError(errData.language[0]);
      } else if (errData?.detail) {
        setSubmitError(errData.detail);
      } else {
        setSubmitError('Failed to submit code. Please check your network and try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render loading and error states
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <>
        <Navbar />
        <div className="container" style={{ marginTop: '40px' }}>
          <LoadingSpinner message="Loading assignment and editor..." />
        </div>
      </>
    );
  }

  if (loadError) {
    return (
      <>
        <Navbar />
        <div className="container" style={{ marginTop: '40px', maxWidth: '700px' }}>
          <div className="card">
            <h2>Assignment Unavailable</h2>
            <div className="error-msg">{loadError}</div>
            <Link to="/login" className="btn btn-secondary" style={{ marginTop: '12px' }}>
              ← Return to Login
            </Link>
          </div>
        </div>
      </>
    );
  }

  // Check if deadline has passed
  const isPastDue = assignment?.is_past_due || assignment?.status === 'closed';

  // Determine Monaco mode string (e.g. 'python', 'cpp', 'java')
  const monacoMode = MONACO_LANGUAGE[selectedLanguage] || 'plaintext';

  return (
    <>
      <Navbar />

      <main className="container" style={{ marginTop: '20px' }}>
        {/* Assignment metadata card */}
        <section className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1 style={{ marginBottom: '6px' }}>{assignment.title}</h1>
              <p className="text-muted" style={{ fontSize: '14px' }}>
                Classroom: <strong>{assignment.classroom_name || 'Enrolled Class'}</strong> | Max Marks: <strong>{assignment.max_marks}</strong>
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <StatusBadge status={assignment.status || (isPastDue ? 'wrong_answer' : 'accepted')} />
              <Link
                to={`/assignments/${assignmentId}/submissions`}
                className="btn btn-secondary"
                style={{ fontSize: '13px', padding: '8px 14px' }}
              >
                📜 View History
              </Link>
            </div>
          </div>

          {/* Due date notice */}
          <div style={{ marginTop: '12px', fontSize: '13px' }}>
            📅 <strong>Deadline:</strong>{' '}
            {assignment.due_date ? (
              <span style={{ color: isPastDue ? '#ef4444' : '#10b981', fontWeight: '600' }}>
                {new Date(assignment.due_date).toLocaleString()} {isPastDue ? '(Expired)' : '(Open)'}
              </span>
            ) : (
              <span className="text-muted">No deadline</span>
            )}
          </div>

          {/* Problem instructions */}
          {assignment.instructions && (
            <div style={{ marginTop: '16px', background: '#0f172a', padding: '14px', borderRadius: '8px', border: '1px solid #334155' }}>
              <h3 style={{ color: '#93c5fd', marginBottom: '8px' }}>Problem Instructions</h3>
              <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '13px', color: '#cbd5e1' }}>
                {assignment.instructions}
              </div>
            </div>
          )}
        </section>

        {/* Success alert */}
        {submitSuccess && (
          <div className="card" style={{ borderLeft: '4px solid #10b981', background: '#052e16' }}>
            <h3 style={{ color: '#86efac', marginBottom: '4px' }}>✅ Submission Recorded</h3>
            <p style={{ fontSize: '14px', color: '#bbf7d0' }}>{submitSuccess.message}</p>
            <div style={{ marginTop: '10px', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <span style={{ fontSize: '13px' }}>
                Submission ID: <strong>#{submitSuccess.submission.id}</strong> | Status:
              </span>
              <StatusBadge status={submitSuccess.submission.status} />
              <Link
                to={`/submissions/${submitSuccess.submission.id}`}
                className="btn btn-success"
                style={{ padding: '6px 14px', fontSize: '12px', marginLeft: 'auto' }}
              >
                View Details →
              </Link>
            </div>
          </div>
        )}

        {/* Error alert */}
        {submitError && <div className="error-msg">❌ {submitError}</div>}

        {/* Deadline expired warning */}
        {isPastDue && (
          <div className="error-msg" style={{ background: '#7c2d12', color: '#ffedd5', borderColor: '#ea580c' }}>
            ⚠️ The deadline for this assignment has passed. New submissions are no longer accepted.
          </div>
        )}

        {/* Draft save confirmation message */}
        {saveMessage && <div className="success-msg" style={{ padding: '8px 12px', fontSize: '13px' }}>💾 {saveMessage}</div>}

        {/* Monaco Code Editor Section */}
        <section className="card" style={{ padding: '16px' }}>
          {/* Editor toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label htmlFor="languageSelect" style={{ margin: 0, fontSize: '13px' }}>
                Language:
              </label>

              {assignment.language === 'other' ? (
                // If assignment allows 'other', student can pick their preferred programming language
                <select
                  id="languageSelect"
                  value={selectedLanguage}
                  onChange={handleLanguageChange}
                  disabled={isPastDue || submitting}
                  style={{ width: 'auto', margin: 0, padding: '6px 10px', fontSize: '13px' }}
                >
                  <option value="python">Python</option>
                  <option value="java">Java</option>
                  <option value="c">C</option>
                  <option value="cpp">C++</option>
                  <option value="javascript">JavaScript</option>
                  <option value="other">Other</option>
                </select>
              ) : (
                // Assignment specifies a required language — lock to it
                <span
                  style={{
                    backgroundColor: '#334155',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: '600',
                    color: '#93c5fd',
                  }}
                >
                  {LANGUAGE_DISPLAY[assignment.language] || assignment.language} (Required)
                </span>
              )}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={handleSaveDraft}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '12px' }}
                title="Save code draft locally in browser"
              >
                💾 Save Draft
              </button>
            </div>
          </div>

          {/* Monaco Editor Component */}
          <div className="editor-wrapper">
            <Editor
              height="500px"
              language={monacoMode}
              theme="vs-dark"
              value={sourceCode}
              onChange={(value) => setSourceCode(value || '')}
              options={{
                fontSize: 14,
                fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
                fontLigatures: true,
                minimap: { enabled: false }, // Cleaner view for student coding
                scrollBeyondLastLine: false,
                automaticLayout: true, // Resize automatically when viewport changes
                wordWrap: 'on',
                lineNumbers: 'on',
                tabSize: 4,
                readOnly: isPastDue || submitting, // Lock editing if expired or currently submitting
                suggestOnTriggerCharacters: true,
              }}
            />
          </div>

          {/* Submission action bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <span className="text-muted" style={{ fontSize: '12px' }}>
              💡 Remember to test your solution locally or review your logic before submitting.
            </span>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isPastDue || submitting}
              className="btn btn-success"
              style={{
                padding: '12px 28px',
                fontSize: '15px',
                fontWeight: '700',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {submitting ? (
                <>
                  <span className="spinner" style={{ width: '16px', height: '16px', margin: 0 }} />
                  Submitting Code...
                </>
              ) : (
                '🚀 Submit Solution'
              )}
            </button>
          </div>
        </section>
      </main>
    </>
  );
}

export default CodeEditorPage;

