/*
  src/services/submissionService.js — API calls for the submissions module.

  This file contains all the functions that communicate with the Django
  submissions API. Separating API calls from components makes the code:
    - Easier to test (you can mock this file)
    - Easier to change (if the API URL changes, change it here, not everywhere)
    - Easier to understand (components stay focused on UI, not data fetching)

  Every function here returns a Promise — JavaScript's way of handling
  async operations that take time (like network requests).
*/

import api from './api';


/*
  submitCode — POST a code submission to the backend.

  Parameters:
    - assignmentId: the ID of the assignment being submitted to
    - sourceCode: the student's code as a string
    - language: the programming language (e.g. 'python', 'java')

  What it does:
    Sends the code to: POST /api/submissions/assignment/<id>/submit/
    Django view will:
      1. Check the student is enrolled in the classroom
      2. Check the deadline hasn't passed
      3. Validate the language matches the assignment
      4. Store the submission with status='pending'
      5. Return the created submission object

  Returns:
    The response data from Django (includes submission id, status, etc.)
*/
export const submitCode = async (assignmentId, sourceCode, language) => {
  const response = await api.post(`/api/submissions/assignment/${assignmentId}/submit/`, {
    source_code: sourceCode,  // WHY snake_case? Django REST Framework uses Python naming conventions
    language: language,
  });
  return response.data;
};


/*
  getMySubmissions — GET the student's own submission history for an assignment.

  Parameters:
    - assignmentId: the assignment whose history to fetch

  Returns:
    An array of submission objects (compact list — no source_code included).
*/
export const getMySubmissions = async (assignmentId) => {
  const response = await api.get(`/api/submissions/assignment/${assignmentId}/my/`);
  return response.data;
};


/*
  getSubmissionDetail — GET the full detail of one specific submission.

  Parameters:
    - submissionId: the unique ID of the submission

  Returns:
    A single submission object with source_code, status, and feedback.
*/
export const getSubmissionDetail = async (submissionId) => {
  const response = await api.get(`/api/submissions/${submissionId}/`);
  return response.data;
};


/*
  getAssignment — GET a specific assignment's details.
  Used by the code editor to display the assignment title, language, due date.

  Parameters:
    - assignmentId: the assignment to fetch

  Returns:
    The assignment object including title, language, due_date, instructions.
*/
export const getAssignment = async (assignmentId) => {
  // Students use the student endpoint to get assignment details
  const response = await api.get(`/api/assignments/${assignmentId}/student/`);
  return response.data;
};


/*
  getTeacherSubmissions — GET all submissions for an assignment (teacher only).

  Parameters:
    - assignmentId: the assignment ID

  Returns:
    An array of all students' submissions for this assignment.
*/
export const getTeacherSubmissions = async (assignmentId) => {
  const response = await api.get(`/api/submissions/assignment/${assignmentId}/all/`);
  return response.data;
};
