from django import forms
from django.db import models
from django.contrib.auth.models import User
from .models import Task
from projects.models import Project


class TaskForm(forms.ModelForm):
    """
    Form for Project Leads and Administrators to create and edit Tasks.
    Filters available assignees strictly to members of the selected project.
    """
    assigned_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label="-- Select Project Member --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'project',
            'assigned_user',
            'assigned_to',
            'priority',
            'status',
            'start_date',
            'due_date',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Design Relational Database Schema'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide technical specifications, acceptance criteria, and notes...'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        fixed_project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        # 1. Project filtering based on user permissions
        if user and not (user.is_staff or user.is_superuser):
            self.fields['project'].queryset = Project.objects.filter(
                models.Q(created_by=user) | models.Q(memberships__user=user, memberships__role='Lead')
            ).distinct()

        # 2. Determine target project
        target_project = fixed_project or (self.instance.project if getattr(self.instance, 'project_id', None) else None)
        if not target_project and 'project' in self.data:
            try:
                project_id = int(self.data.get('project'))
                target_project = Project.objects.filter(pk=project_id).first()
            except (ValueError, TypeError):
                pass

        # 3. Populate assignee choices
        if target_project:
            member_ids = list(target_project.memberships.filter(is_active=True).values_list('user_id', flat=True))
            if target_project.created_by_id and target_project.created_by_id not in member_ids:
                member_ids.append(target_project.created_by_id)
            self.fields['assigned_user'].queryset = User.objects.filter(id__in=member_ids).order_by('username')
        elif user and (user.is_staff or user.is_superuser):
            self.fields['assigned_user'].queryset = User.objects.filter(is_active=True).order_by('username')
        else:
            self.fields['assigned_user'].queryset = User.objects.all().order_by('username')

        # Custom format for assignee choices
        self.fields['assigned_user'].label_from_instance = (
            lambda u: f"{u.get_full_name() or u.username} (@{u.username}){' • ' + u.email if u.email else ''}"
        )

        # Make assigned_to optional (synced automatically)
        self.fields['assigned_to'].required = False

        # Set initial assigned_user if editing existing task
        if self.instance.pk and self.instance.assignee:
            self.fields['assigned_user'].initial = self.instance.assignee

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        due_date = cleaned_data.get('due_date')
        project = cleaned_data.get('project')
        assigned_user = cleaned_data.get('assigned_user')

        if start_date and due_date and due_date < start_date:
            self.add_error('due_date', 'Due date cannot be earlier than start date.')

        # Validate that assigned user is a member of the project
        if project and assigned_user:
            if hasattr(project, 'is_member') and not project.is_member(assigned_user):
                self.add_error('assigned_user', f'User "{assigned_user.username}" is not a member of this project.')

        return cleaned_data


class TaskStatusUpdateForm(forms.ModelForm):
    """
    Limited form for Project Members / Assignees to update the status of their assigned tasks.
    Cannot modify project, assignee, priority, or dates.
    """
    class Meta:
        model = Task
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
