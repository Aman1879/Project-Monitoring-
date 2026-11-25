from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Project, ProjectMembership, Notification
from .forms import ProjectForm, ProjectMemberAddForm
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
    Universal Multi-Role Dashboard View.
    Adapts seamlessly for:
    - Platform Administrators (full platform oversight)
    - Project Leads (projects led, team workload, project tasks)
    - Project Members (projects joined, tasks assigned, deadlines)
    """
    today = date.today()
    user = request.user
    is_staff = user.is_staff or user.is_superuser or 'admin' in user.username.lower()
    employee = getattr(user, 'employee_profile', None)

    # 1. Projects Breakdown for Current User
    led_projects = Project.objects.filter(
        models.Q(created_by=user) | models.Q(memberships__user=user, memberships__role='Lead')
    ).distinct().order_by('-created_at')
    is_project_lead = led_projects.exists()

    member_projects = Project.objects.filter(
        memberships__user=user, memberships__is_active=True
    ).exclude(created_by=user).distinct().order_by('-created_at')

    # All accessible projects for the current user
    if is_staff:
        accessible_projects = Project.objects.all().order_by('-created_at')
    else:
        accessible_projects = Project.objects.filter(
            models.Q(created_by=user) | models.Q(members=user)
        ).distinct().order_by('-created_at')

    # 2. Global / Platform-wide Statistics (Maintained for Admins and Test Assertions)
    total_projects = Project.objects.count()
    projects_in_progress = Project.objects.filter(status='In Progress').count()
    completed_projects = Project.objects.filter(status='Completed').count()
    planning_projects = Project.objects.filter(status='Planning').count()
    on_hold_projects = Project.objects.filter(status='On Hold').count()
    total_employees = Employee.objects.count()
    total_registered_users = User.objects.count()

    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='Pending').count()
    in_progress_tasks = Task.objects.filter(status='In Progress').count()
    completed_tasks = Task.objects.filter(status='Completed').count()
    overdue_tasks = Task.objects.filter(due_date__lt=today).exclude(status='Completed').count()

    recent_projects = Project.objects.select_related('created_by').order_by('-created_at')[:5]
    recent_tasks = Task.objects.select_related('project', 'assigned_to__user', 'assigned_user').order_by('-created_at')[:5]

    # Global Project Progress Calculation
    all_projects = Project.objects.all().order_by('-created_at')
    projects_with_progress = []
    for p in all_projects:
        p_total = p.tasks.count()
        p_done = p.tasks.filter(status='Completed').count()
        p.total_tasks_count = p_total
        p.completed_tasks_count = p_done
        p.progress = round((p_done / p_total) * 100) if p_total > 0 else 0
        p.members_count = p.memberships.filter(is_active=True).count()
        projects_with_progress.append(p)

    # 3. Project Lead Specific Metrics
    if is_project_lead:
        lead_tasks = Task.objects.filter(project__in=led_projects).select_related('project', 'assigned_user', 'assigned_to__user')
        lead_total_tasks = lead_tasks.count()
        lead_pending_tasks = lead_tasks.filter(status='Pending').count()
        lead_in_progress_tasks = lead_tasks.filter(status='In Progress').count()
        lead_completed_tasks = lead_tasks.filter(status='Completed').count()
        lead_overdue_tasks = lead_tasks.filter(due_date__lt=today).exclude(status='Completed').count()
        lead_team_members_count = ProjectMembership.objects.filter(project__in=led_projects, is_active=True).values('user_id').distinct().count()
        lead_upcoming_deadlines = lead_tasks.filter(status__in=['Pending', 'In Progress'], due_date__gte=today).order_by('due_date')[:5]
        
        # Calculate progress for led projects
        led_projects_with_progress = []
        for lp in led_projects:
            lp_total = lp.tasks.count()
            lp_done = lp.tasks.filter(status='Completed').count()
            lp.total_tasks_count = lp_total
            lp.completed_tasks_count = lp_done
            lp.progress = round((lp_done / lp_total) * 100) if lp_total > 0 else 0
            lp.members_count = lp.memberships.filter(is_active=True).count()
            led_projects_with_progress.append(lp)
    else:
        lead_tasks = Task.objects.none()
        lead_total_tasks = 0
        lead_pending_tasks = 0
        lead_in_progress_tasks = 0
        lead_completed_tasks = 0
        lead_overdue_tasks = 0
        lead_team_members_count = 0
        lead_upcoming_deadlines = []
        led_projects_with_progress = []

    # 4. Project Member / Personal Workstation Metrics
    my_tasks_qs = Task.objects.filter(
        models.Q(assigned_user=user) | models.Q(assigned_to__user=user)
    ).select_related('project').order_by('due_date')

    my_total_tasks = my_tasks_qs.count()
    my_pending_tasks = my_tasks_qs.filter(status='Pending').count()
    my_in_progress_tasks = my_tasks_qs.filter(status='In Progress').count()
    my_completed_tasks = my_tasks_qs.filter(status='Completed').count()
    my_overdue_tasks = my_tasks_qs.filter(due_date__lt=today).exclude(status='Completed').count()
    my_recent_tasks = my_tasks_qs[:5]
    my_upcoming_deadlines = my_tasks_qs.filter(status__in=['Pending', 'In Progress'], due_date__gte=today)[:5]

    # 5. User Notifications
    user_notifications = Notification.objects.filter(recipient=user).select_related('related_project', 'related_task')[:5]
    user_unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

    context = {
        # Global Counts
        'total_projects': total_projects,
        'projects_in_progress': projects_in_progress,
        'completed_projects': completed_projects,
        'planning_projects': planning_projects,
        'on_hold_projects': on_hold_projects,
        'total_employees': total_employees,
        'total_registered_users': total_registered_users,
        'total_project_leads': Project.objects.values('created_by').distinct().count(),
        'total_project_members': ProjectMembership.objects.filter(role='Member', is_active=True).values('user_id').distinct().count(),
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
        'projects_with_progress': projects_with_progress,

        # Role Flags
        'is_staff': is_staff,
        'is_project_lead': is_project_lead,
        'is_project_member': member_projects.exists() or (my_total_tasks > 0),
        'employee': employee,

        # Project Lead Context
        'led_projects': led_projects,
        'led_projects_with_progress': led_projects_with_progress,
        'lead_total_tasks': lead_total_tasks,
        'lead_pending_tasks': lead_pending_tasks,
        'lead_in_progress_tasks': lead_in_progress_tasks,
        'lead_completed_tasks': lead_completed_tasks,
        'lead_overdue_tasks': lead_overdue_tasks,
        'lead_team_members_count': lead_team_members_count,
        'lead_upcoming_deadlines': lead_upcoming_deadlines,

        # Member Context
        'member_projects': member_projects,
        'my_total_tasks': my_total_tasks,
        'my_pending_tasks': my_pending_tasks,
        'my_in_progress_tasks': my_in_progress_tasks,
        'my_completed_tasks': my_completed_tasks,
        'my_overdue_tasks': my_overdue_tasks,
        'my_recent_tasks': my_recent_tasks,
        'my_upcoming_deadlines': my_upcoming_deadlines,

        # Notifications
        'user_notifications': user_notifications,
        'user_unread_count': user_unread_count,
    }

    return render(request, 'dashboard.html', context)


# ==============================================================================
# PROJECT CRUD & COLLABORATION VIEWS
# ==============================================================================

@login_required
def project_list_view(request):
    """
    Renders list of accessible projects with search and role tabs:
    - Platform Admins see all projects.
    - Regular Users see projects they lead or belong to.
    """
    search_query = request.GET.get('q', '').strip()
    active_tab = request.GET.get('tab', 'all').strip()
    user = request.user
    is_admin = user.is_staff or user.is_superuser

    if is_admin:
        base_qs = Project.objects.all().select_related('created_by')
    else:
        base_qs = Project.objects.filter(
            models.Q(created_by=user) | models.Q(members=user)
        ).select_related('created_by').distinct()

    if active_tab == 'lead':
        projects = base_qs.filter(models.Q(created_by=user) | models.Q(memberships__user=user, memberships__role='Lead')).distinct()
    elif active_tab == 'joined':
        projects = base_qs.filter(members=user).exclude(created_by=user).distinct()
    else:
        projects = base_qs

    if search_query:
        projects = projects.filter(
            models.Q(name__icontains=search_query) | models.Q(description__icontains=search_query)
        )

    projects = projects.order_by('-created_at')

    # Attach stats for each project
    projects_list = []
    for p in projects:
        t_count = p.tasks.count()
        c_count = p.tasks.filter(status='Completed').count()
        p.total_tasks_count = t_count
        p.completed_tasks_count = c_count
        p.progress = round((c_count / t_count) * 100) if t_count > 0 else 0
        p.members_count = p.memberships.filter(is_active=True).count()
        p.is_user_lead = p.is_lead(user)
        projects_list.append(p)

    context = {
        'projects': projects_list,
        'search_query': search_query,
        'active_tab': active_tab,
        'is_admin': is_admin,
    }
    return render(request, 'projects/project_list.html', context)


@login_required
def project_create_view(request):
    """
    Allows ANY authenticated registered user to create a Project.
    Automatically assigns created_by = request.user and enlists them as Project Lead.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()

            # Automatically establish Project Lead membership
            ProjectMembership.objects.get_or_create(
                project=project,
                user=request.user,
                defaults={'role': 'Lead', 'is_active': True}
            )

            messages.success(request, f'Project "{project.name}" created successfully! You are now the Project Lead.')
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
    Displays full details for a single project:
    - Enforces project-level access control (Admin, Project Lead, or Project Member).
    - Blocks unauthorized users with PermissionDenied (403).
    - Lists active members and related tasks.
    """
    project = get_object_or_404(Project.objects.select_related('created_by'), pk=pk)

    # Access control: user must be staff, the creator, or an active member
    if not project.is_member(request.user):
        raise PermissionDenied("You do not have permission to access this project.")

    is_lead = project.is_lead(request.user)

    # Active team members
    memberships = project.memberships.select_related('user').filter(is_active=True).order_by('role', 'user__username')
    tasks = project.tasks.select_related('assigned_to__user', 'assigned_user').order_by('due_date')

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='Completed').count()
    progress = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    context = {
        'project': project,
        'is_lead': is_lead,
        'memberships': memberships,
        'tasks': tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress': progress,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_update_view(request, pk):
    """
    Handles editing project details.
    Only Project Leads and Platform Administrators can edit.
    Notifies project members on update.
    """
    project = get_object_or_404(Project, pk=pk)

    if not project.is_lead(request.user):
        raise PermissionDenied("Only the Project Lead or platform administrator can edit this project.")

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()

            # Notify active project members (excluding the editor)
            members = project.members.exclude(id=request.user.id)
            for m in members:
                Notification.objects.create(
                    recipient=m,
                    title=f"Project Updated: {project.name}",
                    message=f"{request.user.get_full_name() or request.user.username} updated project details for {project.name}.",
                    notification_type='project_update',
                    related_project=project
                )

            messages.success(request, f'Project "{project.name}" updated successfully!')
            return redirect('projects:project_detail', pk=project.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ProjectForm(instance=project)

    context = {
        'form': form,
        'project': project,
        'action_title': f'Edit "{project.name}"',
        'is_edit': True,
    }
    return render(request, 'projects/project_form.html', context)


@login_required
def project_delete_view(request, pk):
    """
    Handles project deletion.
    Only Project Leads and Platform Administrators can delete.
    """
    project = get_object_or_404(Project, pk=pk)

    if not project.is_lead(request.user):
        raise PermissionDenied("Only the Project Lead or platform administrator can delete this project.")

    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" was successfully deleted.')
        return redirect('projects:project_list')

    context = {
        'project': project,
    }
    return render(request, 'projects/project_confirm_delete.html', context)


# ==============================================================================
# TEAM MANAGEMENT VIEWS
# ==============================================================================

@login_required
def project_team_manage_view(request, pk):
    """
    Team Management Interface:
    - Only Project Leads or Platform Administrators can manage the team.
    - View all members, search registered users by username/email, and add/remove members.
    """
    project = get_object_or_404(Project.objects.select_related('created_by'), pk=pk)

    if not project.is_lead(request.user):
        raise PermissionDenied("Only the Project Lead or platform administrator can manage project team members.")

    memberships = project.memberships.select_related('user').filter(is_active=True).order_by('role', 'user__username')
    current_member_ids = list(memberships.values_list('user_id', flat=True))
    if project.created_by_id and project.created_by_id not in current_member_ids:
        current_member_ids.append(project.created_by_id)

    # Search query for adding members
    search_query = request.GET.get('q', '').strip()
    search_results = []
    if search_query:
        search_results = User.objects.filter(is_active=True).filter(
            models.Q(username__icontains=search_query) | models.Q(email__icontains=search_query) | models.Q(first_name__icontains=search_query) | models.Q(last_name__icontains=search_query)
        ).exclude(id__in=current_member_ids)[:15]

    add_form = ProjectMemberAddForm()

    context = {
        'project': project,
        'memberships': memberships,
        'search_query': search_query,
        'search_results': search_results,
        'add_form': add_form,
    }
    return render(request, 'projects/project_team_manage.html', context)


@login_required
@require_POST
def project_member_add_view(request, pk):
    """
    Adds a registered user to the project by username or email.
    Generates an in-app Notification for the added user.
    """
    project = get_object_or_404(Project, pk=pk)

    if not project.is_lead(request.user):
        raise PermissionDenied("Only the Project Lead or platform administrator can add team members.")

    identifier = request.POST.get('username_or_email', '').strip()
    user_id = request.POST.get('user_id')

    target_user = None
    if user_id:
        target_user = User.objects.filter(pk=user_id, is_active=True).first()
    elif identifier:
        target_user = User.objects.filter(
            models.Q(username__iexact=identifier) | models.Q(email__iexact=identifier),
            is_active=True
        ).first()

    if not target_user:
        messages.error(request, f'No active registered user found matching "{identifier}". Please verify the username or email.')
        return redirect('projects:project_team_manage', pk=project.pk)

    # Check if already a member
    membership = ProjectMembership.objects.filter(project=project, user=target_user).first()
    if membership:
        if membership.is_active:
            messages.warning(request, f'User "{target_user.username}" is already an active member of this project.')
            return redirect('projects:project_team_manage', pk=project.pk)
        else:
            membership.is_active = True
            membership.save()
    else:
        role = 'Lead' if target_user == project.created_by else 'Member'
        ProjectMembership.objects.create(project=project, user=target_user, role=role, is_active=True)

    # Generate in-app Notification
    Notification.objects.create(
        recipient=target_user,
        title=f"Added to Project: {project.name}",
        message=f"You have been added to {project.name} by {request.user.get_full_name() or request.user.username}.",
        notification_type='project_assignment',
        related_project=project
    )

    messages.success(request, f'Successfully added {target_user.get_full_name() or target_user.username} (@{target_user.username}) to the project team!')
    return redirect('projects:project_team_manage', pk=project.pk)


@login_required
@require_POST
def project_member_remove_view(request, pk, user_id):
    """
    Removes a member from the project team.
    The Project Lead cannot be removed.
    """
    project = get_object_or_404(Project, pk=pk)

    if not project.is_lead(request.user):
        raise PermissionDenied("Only the Project Lead or platform administrator can remove team members.")

    if user_id == project.created_by_id:
        messages.error(request, "The Project Lead cannot be removed from the project.")
        return redirect('projects:project_team_manage', pk=project.pk)

    membership = get_object_or_404(ProjectMembership, project=project, user_id=user_id)
    removed_username = membership.user.username
    membership.delete()

    messages.success(request, f'Removed @{removed_username} from the project team.')
    return redirect('projects:project_team_manage', pk=project.pk)


# ==============================================================================
# NOTIFICATION VIEWS
# ==============================================================================

@login_required
def notification_list_view(request):
    """
    Notification Center: lists all notifications for the authenticated user.
    """
    filter_type = request.GET.get('filter', 'all')
    user = request.user

    notifications_qs = Notification.objects.filter(recipient=user).select_related('related_project', 'related_task')

    if filter_type == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)

    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

    context = {
        'notifications': notifications_qs[:50],
        'unread_count': unread_count,
        'filter_type': filter_type,
    }
    return render(request, 'projects/notification_list.html', context)


@login_required
def notification_mark_read_view(request, pk):
    """
    Marks a single notification as read and navigates to its related project/task.
    """
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    target_url = notification.get_target_url()
    if target_url and target_url != '#':
        return redirect(target_url)

    messages.info(request, "Notification marked as read.")
    return redirect('projects:notification_list')


@login_required
@require_POST
def notification_mark_all_read_view(request):
    """
    Marks all notifications for the authenticated user as read.
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get('HTTP_REFERER') or 'projects:notification_list')
