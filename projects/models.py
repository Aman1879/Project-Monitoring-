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

    def __str__(self):
        return self.name
