from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Project(models.Model):
    STATUS_CHOICES = [
        ('Planning', 'Planning'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Planning')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(
        User,
        through='ProjectMembership',
        related_name='joined_projects',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def clean(self):
        super().clean()
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValidationError({'deadline': 'Deadline cannot be earlier than start date.'})

    def is_lead(self, user):
        """Check if a user is the Project Lead or Platform Administrator."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if self.created_by_id == user.id:
            return True
        return self.memberships.filter(user=user, role='Lead', is_active=True).exists()

    def is_member(self, user):
        """Check if a user is an active member or lead of this project."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if self.created_by_id == user.id:
            return True
        if self.pk:
            if self.memberships.filter(user=user, is_active=True).exists():
                return True
            if self.tasks.filter(models.Q(assigned_user=user) | models.Q(assigned_to__user=user)).exists():
                return True
        return False

    def __str__(self):
        return self.name


class ProjectMembership(models.Model):
    ROLE_CHOICES = [
        ('Lead', 'Project Lead'),
        ('Member', 'Project Member'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-joined_at']
        unique_together = ('project', 'user')
        verbose_name = 'Project Membership'
        verbose_name_plural = 'Project Memberships'

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.role})"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('project_assignment', 'Project Assignment'),
        ('task_assignment', 'Task Assignment'),
        ('task_status_update', 'Task Status Update'),
        ('project_update', 'Project Update'),
        ('general', 'General Notification'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    related_project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    related_task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.notification_type}] {self.recipient.username}: {self.title}"

    def get_target_url(self):
        """Returns the appropriate URL to navigate to when clicked."""
        if self.related_task_id:
            from django.urls import reverse
            try:
                return reverse('tasks:task_detail', kwargs={'pk': self.related_task_id})
            except Exception:
                pass
        if self.related_project_id:
            from django.urls import reverse
            try:
                return reverse('projects:project_detail', kwargs={'pk': self.related_project_id})
            except Exception:
                pass
        return '#'
