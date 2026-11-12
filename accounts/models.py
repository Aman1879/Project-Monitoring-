from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    date_joined = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['employee_id']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        full_name = self.user.get_full_name()
        display_name = full_name if full_name else self.user.username
        return f"{display_name} ({self.employee_id})"
