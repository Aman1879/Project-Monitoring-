from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import models, transaction
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Employee
from .forms import EmployeeCreationForm, EmployeeUpdateForm, UserRegistrationForm


def login_view(request):
    """
    Handles user login.
    - If user is already authenticated, redirects them to the main page.
    - On GET: renders the login form.
    - On POST: validates credentials, logs in the user, and redirects to dashboard/preview.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Check for ?next= redirect parameter
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                messages.error(request, 'Your account is disabled. Please contact the administrator.')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html')


@require_POST
def logout_view(request):
    """
    Handles user logout.
    - Protected with @require_POST to prevent CSRF attacks via GET requests.
    - Clears the session and redirects to public homepage with feedback.
    """
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('home')


def register_view(request):
    """
    Handles public user registration.
    - If user is already authenticated, redirects them to the authenticated dashboard.
    - Validates matching passwords and unique username.
    - Hashes password securely and ensures non-staff/non-superuser flags.
    - Does NOT auto-login; redirects to login page so user must log in with their credentials.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Account created successfully for {user.username}! Please sign in with your credentials to access your dashboard.'
            )
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below to register.')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


# ==============================================================================
# EMPLOYEE MANAGEMENT CRUD VIEWS
# ==============================================================================

@login_required
def employee_list_view(request):
    """
    Displays a list of all employees with optional search filtering
    by name, employee ID, or department.
    """
    search_query = request.GET.get('q', '').strip()
    employees = Employee.objects.select_related('user').order_by('employee_id')

    if search_query:
        employees = employees.filter(
            models.Q(user__first_name__icontains=search_query) |
            models.Q(user__last_name__icontains=search_query) |
            models.Q(user__username__icontains=search_query) |
            models.Q(employee_id__icontains=search_query) |
            models.Q(department__icontains=search_query)
        )

    context = {
        'employees': employees,
        'search_query': search_query,
    }
    return render(request, 'accounts/employee_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def employee_create_view(request):
    """
    Staff-only view to register a new employee.
    Creates User and Employee models atomically.
    """
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST)
        if form.is_valid():
            employee = form.save()
            messages.success(
                request,
                f'Employee "{employee.user.get_full_name() or employee.user.username}" created successfully!'
            )
            return redirect('accounts:employee_detail', pk=employee.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = EmployeeCreationForm()

    context = {
        'form': form,
        'action_title': 'Add New Employee',
        'is_edit': False,
    }
    return render(request, 'accounts/employee_form.html', context)


@login_required
def employee_detail_view(request, pk):
    """
    Displays detailed information for a single employee, including assigned tasks.
    """
    employee = get_object_or_404(Employee.objects.select_related('user'), pk=pk)
    tasks = employee.tasks.select_related('project').order_by('due_date')

    context = {
        'employee': employee,
        'tasks': tasks,
    }
    return render(request, 'accounts/employee_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def employee_update_view(request, pk):
    """
    Staff-only view to edit an existing Employee and linked User information.
    Does not modify password.
    """
    employee = get_object_or_404(Employee.objects.select_related('user'), pk=pk)

    if request.method == 'POST':
        form = EmployeeUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Employee "{employee.user.get_full_name() or employee.user.username}" updated successfully!'
            )
            return redirect('accounts:employee_detail', pk=employee.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = EmployeeUpdateForm(instance=employee)

    context = {
        'form': form,
        'employee': employee,
        'action_title': 'Edit Employee Details',
        'is_edit': True,
    }
    return render(request, 'accounts/employee_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def employee_delete_view(request, pk):
    """
    Staff-only view to delete an Employee and linked User record.
    Prevents administrators from accidentally deleting their own account.
    """
    employee = get_object_or_404(Employee.objects.select_related('user'), pk=pk)

    # Prevent deleting self
    if employee.user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:employee_list')

    if request.method == 'POST':
        emp_name = str(employee)
        user = employee.user
        with transaction.atomic():
            employee.delete()
            user.delete()
        messages.success(request, f'Employee "{emp_name}" and associated account were deleted.')
        return redirect('accounts:employee_list')

    context = {
        'employee': employee,
        'task_count': employee.tasks.count(),
    }
    return render(request, 'accounts/employee_confirm_delete.html', context)
