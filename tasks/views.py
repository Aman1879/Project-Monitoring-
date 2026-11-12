from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import Task
from .forms import TaskForm, TaskStatusUpdateForm
from projects.models import Project


@login_required
def task_list_view(request):
    """
    Task List View:
    - Staff users see all tasks across all projects and employees.
    - Regular employees only see tasks assigned to their linked Employee profile.
    - Includes search by title, and filters by project, status, and priority.
    - For regular employees, includes personal metrics (total, pending, in progress, completed, overdue).
    """
    today = date.today()
    user = request.user
    is_staff = user.is_staff
    employee = getattr(user, 'employee_profile', None)

    # 1. Base Queryset depending on role
    if is_staff:
        base_tasks = Task.objects.select_related('project', 'assigned_to__user').all()
        employee_metrics = None
    else:
        if employee:
            base_tasks = Task.objects.filter(assigned_to=employee).select_related('project', 'assigned_to__user')
            # Calculate Employee Task Dashboard Metrics
            employee_metrics = {
                'total_assigned': base_tasks.count(),
                'pending': base_tasks.filter(status='Pending').count(),
                'in_progress': base_tasks.filter(status='In Progress').count(),
                'completed': base_tasks.filter(status='Completed').count(),
                'overdue': base_tasks.filter(due_date__lt=today).exclude(status='Completed').count(),
            }
        else:
            base_tasks = Task.objects.none()
            employee_metrics = {
                'total_assigned': 0,
                'pending': 0,
                'in_progress': 0,
                'completed': 0,
                'overdue': 0,
            }

    tasks = base_tasks

    # 2. Filters
    search_query = request.GET.get('q', '').strip()
    selected_project = request.GET.get('project', '').strip()
    selected_status = request.GET.get('status', '').strip()
    selected_priority = request.GET.get('priority', '').strip()

    if search_query:
        tasks = tasks.filter(title__icontains=search_query)

    if selected_project:
        tasks = tasks.filter(project_id=selected_project)

    if selected_status:
        tasks = tasks.filter(status=selected_status)

    if selected_priority:
        tasks = tasks.filter(priority=selected_priority)

    # Filter dropdown options
    projects = Project.objects.all().order_by('name')
    priority_choices = Task.PRIORITY_CHOICES
    status_choices = Task.STATUS_CHOICES

    context = {
        'tasks': tasks,
        'employee_metrics': employee_metrics,
        'projects': projects,
        'priority_choices': priority_choices,
        'status_choices': status_choices,
        'search_query': search_query,
        'selected_project': selected_project,
        'selected_status': selected_status,
        'selected_priority': selected_priority,
        'has_filters': bool(search_query or selected_project or selected_status or selected_priority),
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_create_view(request):
    """
    Staff-only view to create a new task.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators and staff members can create tasks.")

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            messages.success(request, f'Task "{task.title}" was created successfully!')
            return redirect('tasks:task_detail', pk=task.pk)
        else:
            messages.error(request, 'Please correct the errors in the task form.')
    else:
        form = TaskForm()

    context = {
        'form': form,
        'action_title': 'Create New Task',
        'is_edit': False,
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_detail_view(request, pk):
    """
    Task Detail View:
    - Staff users can view any task.
    - Regular employees can only view tasks assigned to them.
    """
    task = get_object_or_404(Task.objects.select_related('project', 'assigned_to__user'), pk=pk)

    if not request.user.is_staff:
        employee = getattr(request.user, 'employee_profile', None)
        if not employee or task.assigned_to != employee:
            raise PermissionDenied("You do not have permission to view tasks assigned to other employees.")

    context = {
        'task': task,
        'is_assigned_to_current_user': bool(
            hasattr(request.user, 'employee_profile') and task.assigned_to == request.user.employee_profile
        ),
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_update_view(request, pk):
    """
    Staff-only view to edit all task details (project, assignee, dates, priority, etc.).
    """
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators and staff members can edit full task details.")

    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            messages.success(request, f'Task "{task.title}" updated successfully!')
            return redirect('tasks:task_detail', pk=task.pk)
        else:
            messages.error(request, 'Please correct the errors in the task form.')
    else:
        form = TaskForm(instance=task)

    context = {
        'form': form,
        'task': task,
        'action_title': 'Edit Task Details',
        'is_edit': True,
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_delete_view(request, pk):
    """
    Staff-only view to delete a task.
    Requires explicit POST confirmation.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators and staff members can delete tasks.")

    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST':
        task_title = task.title
        task.delete()
        messages.success(request, f'Task "{task_title}" was deleted successfully.')
        return redirect('tasks:task_list')

    context = {
        'task': task,
    }
    return render(request, 'tasks/task_confirm_delete.html', context)


@login_required
def task_status_update_view(request, pk):
    """
    Allows regular employees to update the status (Pending, In Progress, Completed)
    of tasks assigned to them without altering other task fields. Staff can also use this.
    """
    task = get_object_or_404(Task.objects.select_related('project', 'assigned_to__user'), pk=pk)

    # Permission check: Staff can update any, Regular employee can ONLY update their own task
    if not request.user.is_staff:
        employee = getattr(request.user, 'employee_profile', None)
        if not employee or task.assigned_to != employee:
            raise PermissionDenied("You can only update the status of tasks assigned to you.")

    if request.method == 'POST':
        form = TaskStatusUpdateForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, f'Status for "{task.title}" updated to {task.status}.')
            return redirect('tasks:task_detail', pk=task.pk)
        else:
            messages.error(request, 'Please choose a valid task status.')
    else:
        form = TaskStatusUpdateForm(instance=task)

    context = {
        'form': form,
        'task': task,
    }
    return render(request, 'tasks/task_status_form.html', context)
