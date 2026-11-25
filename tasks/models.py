from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from projects.models import Project
from accounts.models import Employee


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    assigned_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    start_date = models.DateField()
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError({'due_date': 'Due date cannot be earlier than start date.'})
        # If assigned_user is specified, validate project membership
        if self.assigned_user and self.project_id:
            project = self.project
            if hasattr(project, 'is_member') and not project.is_member(self.assigned_user):
                if self.pk:
                    existing = Task.objects.filter(pk=self.pk).values('assigned_user_id', 'assigned_to_id').first()
                    if existing and (existing['assigned_user_id'] == self.assigned_user_id or (self.assigned_to_id and existing['assigned_to_id'] == self.assigned_to_id)):
                        return
                raise ValidationError({'assigned_user': f'User "{self.assigned_user.username}" is not a member of this project.'})

    def save(self, *args, **kwargs):
        # Synchronize assigned_user and assigned_to for universal compatibility
        if self.assigned_user and not self.assigned_to:
            employee = getattr(self.assigned_user, 'employee_profile', None)
            if employee:
                self.assigned_to = employee
        elif self.assigned_to and not self.assigned_user:
            if hasattr(self.assigned_to, 'user'):
                self.assigned_user = self.assigned_to.user
        super().save(*args, **kwargs)

    @property
    def assignee(self):
        if self.assigned_user:
            return self.assigned_user
        if self.assigned_to and hasattr(self.assigned_to, 'user'):
            return self.assigned_to.user
        return None

    @property
    def assignee_name(self):
        u = self.assignee
        if u:
            full = u.get_full_name()
            return full if full else u.username
        return 'Unassigned'

    def __str__(self):
        return f"{self.title} ({self.project.name})"
