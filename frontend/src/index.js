/*
  src/index.js — The entry point of the React application.

  What does this file do?
    1. Finds the <div id="root"> inside public/index.html.
    2. Initializes React 18's createRoot.
    3. Wraps the App component in BrowserRouter to enable SPA routing.
    4. Imports the global stylesheet for consistent theming.
*/

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles/global.css';

// Find the <div id="root"> in public/index.html
const rootElement = document.getElementById('root');
const root = ReactDOM.createRoot(rootElement);

// Mount the App component inside that div
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
