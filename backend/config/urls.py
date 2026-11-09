"""
Root URL configuration for LabCraft.

Each LabCraft app has its own urls.py; they are included here with an
API prefix so all endpoints live under /api/.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # LabCraft API routes
    path('api/auth/',        include('accounts.urls')),
    path('api/classrooms/',  include('classrooms.urls')),
    path('api/assignments/', include('assignments.urls')),
    path('api/submissions/', include('submissions.urls')),
    path('api/grader/',      include('grader.urls')),
    path('api/analytics/',   include('analytics.urls')),
]

