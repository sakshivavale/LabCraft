/*
  src/components/CodeEditor.js — The Monaco Editor React component.

  What is Monaco Editor?
    Monaco is the same code editor used in VS Code. It gives students:
    - Syntax highlighting (keywords in different colors)
    - Line numbers
    - Auto-indentation
    - Code folding
    - Keyboard shortcuts (Ctrl+Z for undo, etc.)

  What is @monaco-editor/react?
    It's a wrapper library that makes it easy to use Monaco inside a React app.
    Without it, we'd have to manually configure Monaco's JavaScript bundle,
    which is complex. The wrapper handles that for us.

  Props (inputs to this component):
    - language:   string — the programming language (e.g. 'python', 'java')
    - value:      string — the current code content
    - onChange:   function — called every time the student types something
    - readOnly:   boolean — whether the editor is read-only (for viewing submissions)
    - height:     string — CSS height of the editor (e.g. '500px')

  Usage example:
    <CodeEditor
      language="python"
      value={code}
      onChange={setCode}
      height="500px"
    />
*/

import React from 'react';
import Editor from '@monaco-editor/react';   // the Monaco wrapper


/*
  LANGUAGE MAP — Monaco uses slightly different language identifiers than Django.
  For example, 'cpp' in Django maps to 'cpp' in Monaco, but 'javascript'
  maps to 'javascript' (same in this case). We define a map to be explicit.
*/
const MONACO_LANGUAGE_MAP = {
  python:     'python',
  java:       'java',
  c:          'c',
  cpp:        'cpp',
  javascript: 'javascript',
  other:      'plaintext',   // 'other' has no specific highlighting — use plain text
};

/*
  DEFAULT CODE SNIPPETS — when a student opens the editor, they see a
  helpful starting template instead of a blank white page.
  This reduces the "blank page" intimidation and shows correct syntax.
*/
const DEFAULT_CODE = {
  python: `# Write your Python solution here\n\ndef solution():\n    # Your code here\n    pass\n\n# Example:\nprint(solution())\n`,
  java:   `// Write your Java solution here\nimport java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        // Your code here\n    }\n}\n`,
  c:      `/* Write your C solution here */\n#include <stdio.h>\n\nint main() {\n    // Your code here\n    return 0;\n}\n`,
  cpp:    `// Write your C++ solution here\n#include <iostream>\nusing namespace std;\n\nint main() {\n    // Your code here\n    return 0;\n}\n`,
  javascript: `// Write your JavaScript solution here\n\nfunction solution() {\n    // Your code here\n}\n\nconsole.log(solution());\n`,
  other:  `# Write your solution here\n`,
};


function CodeEditor({ language = 'python', value, onChange, readOnly = false, height = '450px' }) {
  /*
    What is "controlled" vs "uncontrolled" in React?
    - Controlled: the parent component owns the value (passed as a prop).
    - Uncontrolled: the component manages its own value internally.
    
    This editor is controlled. The parent (CodeEditorPage) owns 'value' and
    updates it via 'onChange'. This lets the parent read the code when the
    student submits.
  */

  // Determine the Monaco language identifier from our backend language string
  const monacoLang = MONACO_LANGUAGE_MAP[language] || 'plaintext';

  // The initial code shown when the editor first renders
  // If parent provides a value, use it; otherwise use our default snippet
  const initialValue = value !== undefined ? value : (DEFAULT_CODE[language] || '');

  return (
    <div style={{ border: '1px solid #3c3c3c', borderRadius: '4px', overflow: 'hidden' }}>
      {/*
        Editor — the actual Monaco editor component.
        
        height: how tall the editor is on screen.
        language: controls syntax highlighting.
        value: the current code (controlled by parent).
        onChange: called every keystroke with the new full code string.
        theme: 'vs-dark' is the dark VS Code theme — easier on the eyes when coding.
        options: fine-tune editor behavior.
      */}
      <Editor
        height={height}
        language={monacoLang}
        value={initialValue}
        onChange={onChange}
        theme="vs-dark"
        options={{
          fontSize: 14,              // comfortable reading size
          minimap: { enabled: false },  // hide the miniature code map (saves space)
          wordWrap: 'on',            // wrap long lines (don't scroll horizontally)
          scrollBeyondLastLine: false,  // don't allow blank space below the last line
          readOnly: readOnly,        // prevent editing when viewing old submissions
          automaticLayout: true,     // resize automatically when parent container changes
          tabSize: 4,                // 4 spaces per tab (Python convention)
          lineNumbers: 'on',         // show line numbers on the left
          folding: true,             // allow code folding (collapse functions)
          suggestOnTriggerCharacters: true,  // show autocomplete suggestions while typing
        }}
      />
    </div>
  );
}

export default CodeEditor;
