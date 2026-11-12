from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    """
    ModelForm for Staff users to Create and Edit Tasks.
    Enforces Bootstrap 5 styling and date logic validation.
    """
    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'project',
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

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        due_date = cleaned_data.get('due_date')

        if start_date and due_date and due_date < start_date:
            self.add_error('due_date', 'Due date cannot be earlier than start date.')

        return cleaned_data


class TaskStatusUpdateForm(forms.ModelForm):
    """
    Limited form for Regular Employees to update the status of their assigned tasks.
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

