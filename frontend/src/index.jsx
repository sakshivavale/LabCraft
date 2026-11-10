// src/index.jsx — Application entry point
// React 18's createRoot API (replaces the old ReactDOM.render)
import React from 'react';
import ReactDOM from 'react-dom/client';

// BrowserRouter gives all descendant components access to React Router's
// navigation context (useNavigate, useParams, Link, etc.)
import { BrowserRouter } from 'react-router-dom';

// Root App component that owns the route table
import App from './App';

// Global CSS applied across every page
import './styles/global.css';

// Find the <div id="root"> in public/index.html and hand it to React
const rootElement = document.getElementById('root');

// createRoot is the React 18 concurrent-mode entry point
const root = ReactDOM.createRoot(rootElement);

// Render the full app wrapped in BrowserRouter so routing works everywhere
root.render(
  // StrictMode activates additional runtime warnings in development
  // (double-invokes effects to surface side-effect bugs) — has no effect in production
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
