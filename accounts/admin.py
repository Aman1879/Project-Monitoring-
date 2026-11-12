from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_name', 'department', 'designation', 'phone', 'date_joined')
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'user__last_name', 'department', 'designation')
    list_filter = ('department', 'designation', 'date_joined')

    @admin.display(description='Employee Name')
    def get_name(self, obj):
        full_name = obj.user.get_full_name()
        return full_name if full_name else obj.user.username
