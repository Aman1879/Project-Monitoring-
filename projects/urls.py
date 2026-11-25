from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list_view, name='project_list'),
    path('create/', views.project_create_view, name='project_create'),
    path('<int:pk>/', views.project_detail_view, name='project_detail'),
    path('<int:pk>/edit/', views.project_update_view, name='project_update'),
    path('<int:pk>/delete/', views.project_delete_view, name='project_delete'),
    path('<int:pk>/team/', views.project_team_manage_view, name='project_team_manage'),
    path('<int:pk>/team/add/', views.project_member_add_view, name='project_member_add'),
    path('<int:pk>/team/remove/<int:user_id>/', views.project_member_remove_view, name='project_member_remove'),
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/<int:pk>/read/', views.notification_mark_read_view, name='notification_mark_read'),
    path('notifications/<int:pk>/go/', views.notification_mark_read_view, name='notification_read'),
    path('notifications/read-all/', views.notification_mark_all_read_view, name='notification_mark_all_read'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
