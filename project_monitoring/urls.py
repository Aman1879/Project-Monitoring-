from django.contrib import admin
from django.urls import path, include
from projects.views import public_home_view, dashboard_view
from accounts.views import register_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('projects/', include('projects.urls')),
    path('tasks/', include('tasks.urls')),
    # Public Homepage (Accessible to all visitors)
    path('', public_home_view, name='home'),
    # Authenticated Dashboard (Requires login)
    path('dashboard/', dashboard_view, name='dashboard'),
    path('preview/', dashboard_view, name='preview'),  # Backwards compatibility alias
    # Public Registration
    path('register/', register_view, name='register'),
]
