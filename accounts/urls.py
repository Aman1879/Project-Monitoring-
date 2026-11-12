from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Employee Management CRUD
    path('employees/', views.employee_list_view, name='employee_list'),
    path('employees/create/', views.employee_create_view, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail_view, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_update_view, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete_view, name='employee_delete'),
]
