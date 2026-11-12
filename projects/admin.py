from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'deadline', 'created_by', 'created_at')
    search_fields = ('name', 'description', 'created_by__username')
    list_filter = ('status', 'start_date', 'deadline')
    date_hierarchy = 'deadline'
