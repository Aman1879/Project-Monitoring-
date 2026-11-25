from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    """
    ModelForm for creating and updating Project instances.
    Excludes 'created_by' as it is set automatically to request.user.
    """
    class Meta:
        model = Project
        fields = ['name', 'description', 'start_date', 'deadline', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Enterprise Web Portal'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter project objectives, scope, and deliverables...'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean(self):
        """
        Form-level validation to ensure deadline is not earlier than start date.
        """
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        deadline = cleaned_data.get('deadline')

        if start_date and deadline and deadline < start_date:
            self.add_error('deadline', 'Deadline cannot be earlier than start date.')

        return cleaned_data


class ProjectMemberAddForm(forms.Form):
    """
    Form used by Project Leads to add members by username or email.
    """
    username_or_email = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username or email address (e.g. alex or alex@example.com)...',
            'autocomplete': 'off',
            'autofocus': True,
        })
    )
