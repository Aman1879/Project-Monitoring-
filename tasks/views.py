from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db import models
from .models import Task
from .forms import TaskForm, TaskStatusUpdateForm
from projects.models import Project, Notification


@login_required
def task_list_view(request):
    """
    Task List View:
    - Platform Administrators see all tasks across all projects and members.
    - Project Leads and Members see tasks belonging to authorized projects.
    - Includes search, filter by project, status, priority, and role tabs.
    - Preserves personal metrics for assignees.
    """
    today = date.today()
    user = request.user
    is_staff = user.is_staff or user.is_superuser
    is_project_lead = Project.objects.filter(
        models.Q(created_by=user) | models.Q(memberships__user=user, memberships__role='Lead')
    ).distinct().exists()

    # 1. Personal assignee tasks & metrics (preserved for test suite & dashboard)
    my_tasks = Task.objects.filter(
        models.Q(assigned_user=user) | models.Q(assigned_to__user=user)
    )
    if is_staff:
        employee_metrics = None
    else:
        employee_metrics = {
            'total_assigned': my_tasks.count(),
            'pending': my_tasks.filter(status='Pending').count(),
            'in_progress': my_tasks.filter(status='In Progress').count(),
            'completed': my_tasks.filter(status='Completed').count(),
            'overdue': my_tasks.filter(due_date__lt=today).exclude(status='Completed').count(),
        }

    # 2. Base Queryset depending on role
    tab = request.GET.get('tab', 'all').strip()
    if is_staff:
        base_tasks = Task.objects.select_related('project', 'assigned_to__user', 'assigned_user').all()
    elif is_project_lead:
        led_project_ids = Project.objects.filter(
            models.Q(created_by=user) | models.Q(memberships__user=user, memberships__role='Lead')
        ).values_list('id', flat=True)
        if tab == 'assigned':
            base_tasks = my_tasks.select_related('project', 'assigned_to__user', 'assigned_user')
        elif tab == 'led':
            base_tasks = Task.objects.filter(project_id__in=led_project_ids).select_related('project', 'assigned_to__user', 'assigned_user')
        else:
            base_tasks = Task.objects.filter(
                models.Q(project_id__in=led_project_ids) |
                models.Q(assigned_user=user) |
                models.Q(assigned_to__user=user)
            ).select_related('project', 'assigned_to__user', 'assigned_user').distinct()
    else:
        # Regular members/employees only see their own assigned tasks
        base_tasks = my_tasks.select_related('project', 'assigned_to__user', 'assigned_user')

    tasks = base_tasks

    # 4. Search and Dropdown Filters
    search_query = request.GET.get('q', '').strip()
    selected_project = request.GET.get('project', '').strip()
    selected_status = request.GET.get('status', '').strip()
    selected_priority = request.GET.get('priority', '').strip()

    if search_query:
        tasks = tasks.filter(
            models.Q(title__icontains=search_query) | models.Q(description__icontains=search_query)
        )

    if selected_project:
        tasks = tasks.filter(project_id=selected_project)

    if selected_status:
        tasks = tasks.filter(status=selected_status)

    if selected_priority:
        tasks = tasks.filter(priority=selected_priority)

    # Filter dropdown options: only show accessible projects
    if is_staff:
        projects = Project.objects.all().order_by('name')
    else:
        projects = Project.objects.filter(
            models.Q(created_by=user) | models.Q(members=user)
        ).distinct().order_by('name')

    priority_choices = Task.PRIORITY_CHOICES
    status_choices = Task.STATUS_CHOICES

    context = {
        'tasks': tasks.order_by('due_date', '-created_at'),
        'employee_metrics': employee_metrics,
        'projects': projects,
        'priority_choices': priority_choices,
        'status_choices': status_choices,
        'search_query': search_query,
        'selected_project': selected_project,
        'selected_status': selected_status,
        'selected_priority': selected_priority,
        'tab': tab,
        'has_filters': bool(search_query or selected_project or selected_status or selected_priority),
        'is_project_lead': Project.objects.filter(created_by=user).exists(),
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_create_view(request):
    """
    Allows Project Leads and Platform Administrators to create and assign tasks.
    Validates that the assigned user belongs to the target project.
    """
    user = request.user
    is_staff = user.is_staff or user.is_superuser
    led_projects = Project.objects.filter(
        models.Q(created_by=user) | models.Q(memberships__user=user, memberships__role='Lead')
    ).distinct()

    if not is_staff and not led_projects.exists():
        raise PermissionDenied("Only Project Leads and platform administrators can create tasks.")

    target_project = None
    project_id = request.GET.get('project') or request.POST.get('project')
    if project_id:
        target_project = Project.objects.filter(pk=project_id).first()

    if request.method == 'POST':
        form = TaskForm(request.POST, user=user, project=target_project)
        if form.is_valid():
            task = form.save()

            # Automatic notification to assigned member
            if task.assignee and task.assignee != user:
                Notification.objects.create(
                    recipient=task.assignee,
                    title=f"New Task: {task.title}",
                    message=f"New task assigned: '{task.title}' in {task.project.name}. Assigned by {user.get_full_name() or user.username}.",
                    notification_type='task_assignment',
                    related_project=task.project,
                    related_task=task
                )

            messages.success(request, f'Task "{task.title}" was created successfully!')
            return redirect('tasks:task_detail', pk=task.pk)
        else:
            messages.error(request, 'Please correct the errors in the task form.')
    else:
        form = TaskForm(user=user, project=target_project, initial={'project': target_project} if target_project else None)

    context = {
        'form': form,
        'action_title': 'Create New Task',
        'is_edit': False,
        'target_project': target_project,
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_detail_view(request, pk):
    """
    Task Detail View:
    - Platform Administrators, Project Leads, Project Members, and Assignees can view.
    - Prevents unauthorized access across unrelated projects.
    """
    task = get_object_or_404(
        Task.objects.select_related('project__created_by', 'assigned_to__user', 'assigned_user'),
        pk=pk
    )

    project = task.project
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    is_lead = project.is_lead(user)
    is_assignee = (task.assignee == user) or (hasattr(user, 'employee_profile') and task.assigned_to == user.employee_profile)
    is_member = project.is_member(user)

    if not (is_admin or is_lead or is_assignee):
        raise PermissionDenied("You do not have permission to view tasks assigned to other employees.")

    context = {
        'task': task,
        'is_lead': is_lead,
        'is_admin': is_admin,
        'is_assignee': is_assignee,
        'is_assigned_to_current_user': bool(is_assignee),
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_update_view(request, pk):
    """
    Allows Project Leads and Platform Administrators to edit full task details.
    Assignees are redirected to update status instead of getting a raw error.
    """
    task = get_object_or_404(Task.objects.select_related('project'), pk=pk)
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    is_lead = task.project.is_lead(user)

    if not (is_admin or is_lead):
        raise PermissionDenied("Only the Project Lead or platform administrator can edit full task details.")

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=user, project=task.project)
        if form.is_valid():
            prev_assignee = task.assignee
            updated_task = form.save()

            # Notify new assignee if changed
            new_assignee = updated_task.assignee
            if new_assignee and new_assignee != user and new_assignee != prev_assignee:
                Notification.objects.create(
                    recipient=new_assignee,
                    title=f"Task Assigned: {updated_task.title}",
                    message=f"Task '{updated_task.title}' in {updated_task.project.name} was assigned to you by {user.get_full_name() or user.username}.",
                    notification_type='task_assignment',
                    related_project=updated_task.project,
                    related_task=updated_task
                )

            messages.success(request, f'Task "{updated_task.title}" updated successfully!')
            return redirect('tasks:task_detail', pk=updated_task.pk)
        else:
            messages.error(request, 'Please correct the errors in the task form.')
    else:
        form = TaskForm(instance=task, user=user, project=task.project)

    context = {
        'form': form,
        'task': task,
        'action_title': f'Edit Task: {task.title}',
        'is_edit': True,
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_delete_view(request, pk):
    """
    Allows Project Leads and Platform Administrators to delete a task.
    """
    task = get_object_or_404(Task.objects.select_related('project'), pk=pk)
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    is_lead = task.project.is_lead(user)

    if not (is_admin or is_lead):
        raise PermissionDenied("Only the Project Lead or platform administrator can delete tasks.")

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
    Allows Project Members / Assignees (as well as Leads and Admins) to update task status.
    Automatically sends a Notification to the Project Lead.
    """
    task = get_object_or_404(
        Task.objects.select_related('project__created_by', 'assigned_to__user', 'assigned_user'),
        pk=pk
    )
    user = request.user
    project = task.project
    is_admin = user.is_staff or user.is_superuser
    is_lead = project.is_lead(user)
    is_assignee = (task.assignee == user) or (hasattr(user, 'employee_profile') and task.assigned_to == user.employee_profile)

    if not (is_admin or is_lead or is_assignee):
        raise PermissionDenied("You can only update the status of tasks assigned to you.")

    if request.method == 'POST':
        form = TaskStatusUpdateForm(request.POST, instance=task)
        if form.is_valid():
            prev_status = task.status
            updated_task = form.save()

            # If updated by someone other than the Project Lead, notify the Project Lead
            project_lead = project.created_by
            if project_lead and project_lead != user:
                Notification.objects.create(
                    recipient=project_lead,
                    title=f"Task Status Updated: {updated_task.title}",
                    message=f"{user.get_full_name() or user.username} updated '{updated_task.title}' to {updated_task.status}.",
                    notification_type='task_status_update',
                    related_project=project,
                    related_task=updated_task
                )

            messages.success(request, f'Status for "{updated_task.title}" updated to {updated_task.status}.')
            return redirect('tasks:task_detail', pk=updated_task.pk)
        else:
            messages.error(request, 'Please choose a valid task status.')
    else:
        form = TaskStatusUpdateForm(instance=task)

    context = {
        'form': form,
        'task': task,
    }
    return render(request, 'tasks/task_status_update.html', context)
