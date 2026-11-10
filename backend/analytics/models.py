"""
analytics/models.py

The Analytics module provides computational aggregation, reporting, and dashboard
metrics over core LabCraft models:
  - accounts.User
  - classrooms.Classroom & ClassroomMembership
  - assignments.Assignment
  - submissions.Submission
  - grader.GradingResult

Design Decision:
  Analytics are dynamically computed from transactional records via optimized Django
  ORM queries (aggregation, annotation, subqueries, and Q filters). No redundant
  denormalized tables are required, ensuring zero data desynchronization and real-time
  accuracy.
"""

from django.db import models

# No custom database models required; analytics operates over existing models.
