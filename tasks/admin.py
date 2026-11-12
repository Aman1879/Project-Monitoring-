from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'priority', 'status', 'start_date', 'due_date')
    search_fields = ('title', 'description', 'project__name', 'assigned_to__user__username')
    list_filter = ('priority', 'status', 'project', 'due_date')
    date_hierarchy = 'due_date'
