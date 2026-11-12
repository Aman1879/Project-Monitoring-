from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Project
from .forms import ProjectForm
from tasks.models import Task
from accounts.models import Employee


def public_home_view(request):
    """
    Public homepage view accessible to both anonymous and authenticated visitors.
    Displays high-level platform introduction, feature highlights, and public metrics
    without exposing private employee details or sensitive project data.
    """
    total_projects = Project.objects.count()
    completed_projects = Project.objects.filter(status='Completed').count()
    active_projects = Project.objects.filter(status='In Progress').count()
    total_tasks = Task.objects.count()

    context = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'active_projects': active_projects,
        'total_tasks': total_tasks,
    }
    return render(request, 'home.html', context)


@login_required
def dashboard_view(request):
    """
    Admin Dashboard View.
    Gathers real-time statistics from SQLite database using Django ORM:
    - Project, Employee, and Task counts
    - Overdue tasks (due_date < today and not completed)
    - Recent projects & recent tasks
    - Project-by-project progress percentage
    """
    today = date.today()

    # 1. Project Statistics
    total_projects = Project.objects.count()
    projects_in_progress = Project.objects.filter(status='In Progress').count()
    completed_projects = Project.objects.filter(status='Completed').count()

    # 2. Employee Statistics
    total_employees = Employee.objects.count()

    # 3. Task Statistics
    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='Pending').count()
    in_progress_tasks = Task.objects.filter(status='In Progress').count()
    completed_tasks = Task.objects.filter(status='Completed').count()

    # 4. Overdue Tasks:
    # Tasks where due_date < today and status is NOT 'Completed'
    overdue_tasks = Task.objects.filter(
        due_date__lt=today
    ).exclude(status='Completed').count()

    # 5. Recent Projects (Latest 5)
    recent_projects = Project.objects.select_related('created_by').order_by('-created_at')[:5]

    # 6. Recent Tasks (Latest 5)
    recent_tasks = Task.objects.select_related('project', 'assigned_to__user').order_by('-created_at')[:5]

    # 7. Project Progress Calculation:
    # Progress = (completed_tasks / total_tasks) * 100
    # Safely handles projects with 0 tasks by assigning 0%
    all_projects = Project.objects.all().order_by('-created_at')
    projects_with_progress = []

    for project in all_projects:
        p_total_tasks = project.tasks.count()
        p_completed_tasks = project.tasks.filter(status='Completed').count()
        
        # Calculate percentage safely to avoid ZeroDivisionError
        if p_total_tasks > 0:
            progress = round((p_completed_tasks / p_total_tasks) * 100)
        else:
            progress = 0

        # Attach calculated attributes to the project instance
        project.total_tasks_count = p_total_tasks
        project.completed_tasks_count = p_completed_tasks
        project.progress = progress

        projects_with_progress.append(project)

    context = {
        'total_projects': total_projects,
        'projects_in_progress': projects_in_progress,
        'completed_projects': completed_projects,
        'total_employees': total_employees,
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
        'projects_with_progress': projects_with_progress,
    }

    return render(request, 'dashboard.html', context)


# ==============================================================================
# PROJECT CRUD VIEWS
# ==============================================================================

@login_required
def project_list_view(request):
    """
    Renders list of all projects with optional search by project name.
    """
    search_query = request.GET.get('q', '').strip()
    projects = Project.objects.select_related('created_by').order_by('-created_at')

    if search_query:
        projects = projects.filter(name__icontains=search_query)

    context = {
        'projects': projects,
        'search_query': search_query,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_create_view(request):
    """
    Handles creation of a new Project using ModelForm.
    Automatically assigns created_by = request.user.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('projects:project_detail', pk=project.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ProjectForm()

    context = {
        'form': form,
        'action_title': 'Create New Project',
        'is_edit': False,
    }
    return render(request, 'projects/project_form.html', context)


@login_required
def project_detail_view(request, pk):
    """
    Displays full details for a single project, including related tasks and progress.
    """
    project = get_object_or_404(Project.objects.select_related('created_by'), pk=pk)
    tasks = project.tasks.select_related('assigned_to__user').order_by('due_date')

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='Completed').count()
    progress = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    context = {
        'project': project,
        'tasks': tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress': progress,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_update_view(request, pk):
    """
    Handles editing an existing Project.
    Keeps created_by unchanged.
    """
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project "{project.name}" updated successfully!')
            return redirect('projects:project_detail', pk=project.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ProjectForm(instance=project)

    context = {
        'form': form,
        'project': project,
        'action_title': 'Edit Project',
        'is_edit': True,
    }
    return render(request, 'projects/project_form.html', context)


@login_required
def project_delete_view(request, pk):
    """
    Displays confirmation on GET, deletes project on POST.
    Warns user about associated tasks (which will cascade delete).
    """
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" was deleted successfully.')
        return redirect('projects:project_list')

    context = {
        'project': project,
        'task_count': project.tasks.count(),
    }
    return render(request, 'projects/project_confirm_delete.html', context)
