from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list_view, name='task_list'),
    path('create/', views.task_create_view, name='task_create'),
    path('<int:pk>/', views.task_detail_view, name='task_detail'),
    path('<int:pk>/edit/', views.task_update_view, name='task_update'),
    path('<int:pk>/delete/', views.task_delete_view, name='task_delete'),
    path('<int:pk>/status/', views.task_status_update_view, name='task_update_status'),
]

