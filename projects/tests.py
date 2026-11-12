from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from projects.models import Project
from tasks.models import Task
from accounts.models import Employee


class DashboardViewTests(TestCase):
    def setUp(self):
        # 1. Create admin/user
        self.user = User.objects.create_user(
            username='adminuser',
            password='Password123!',
            first_name='Admin',
            last_name='User'
        )

        # 2. Create employees
        self.emp1 = Employee.objects.create(
            user=self.user,
            employee_id='EMP001',
            phone='1234567890',
            department='Engineering',
            designation='Lead Dev'
        )
        self.user2 = User.objects.create_user(username='emp2', password='Password123!')
        self.emp2 = Employee.objects.create(
            user=self.user2,
            employee_id='EMP002',
            phone='0987654321',
            department='QA',
            designation='QA Tester'
        )

        # 3. Create projects
        self.proj_in_progress = Project.objects.create(
            name='Alpha Project',
            description='In progress project',
            start_date=date.today() - timedelta(days=10),
            deadline=date.today() + timedelta(days=20),
            status='In Progress',
            created_by=self.user
        )

        self.proj_completed = Project.objects.create(
            name='Beta Project',
            description='Finished project',
            start_date=date.today() - timedelta(days=30),
            deadline=date.today() - timedelta(days=5),
            status='Completed',
            created_by=self.user
        )

        self.proj_empty = Project.objects.create(
            name='Gamma Project (No Tasks)',
            description='Project with 0 tasks',
            start_date=date.today(),
            deadline=date.today() + timedelta(days=15),
            status='Planning',
            created_by=self.user
        )

        # 4. Create tasks for Alpha Project (2 tasks: 1 completed, 1 in-progress)
        self.task1 = Task.objects.create(
            title='Alpha Task 1',
            project=self.proj_in_progress,
            assigned_to=self.emp1,
            priority='High',
            status='Completed',
            start_date=date.today() - timedelta(days=5),
            due_date=date.today() - timedelta(days=1)
        )
        self.task2 = Task.objects.create(
            title='Alpha Task 2',
            project=self.proj_in_progress,
            assigned_to=self.emp2,
            priority='Medium',
            status='In Progress',
            start_date=date.today() - timedelta(days=3),
            due_date=date.today() + timedelta(days=5)
        )

        # 5. Create tasks for Beta Project (1 completed task)
        self.task3 = Task.objects.create(
            title='Beta Task 1',
            project=self.proj_completed,
            assigned_to=self.emp1,
            priority='Low',
            status='Completed',
            start_date=date.today() - timedelta(days=20),
            due_date=date.today() - timedelta(days=10)
        )

        # 6. Create an Overdue task (due_date in past, status Pending)
        self.task_overdue = Task.objects.create(
            title='Overdue Task',
            project=self.proj_in_progress,
            assigned_to=self.emp2,
            priority='High',
            status='Pending',
            start_date=date.today() - timedelta(days=10),
            due_date=date.today() - timedelta(days=2) # Past due date
        )

    def test_dashboard_requires_authentication(self):
        """Unauthenticated user accessing dashboard is redirected to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard')}")

    def test_dashboard_renders_successfully_for_authenticated_user(self):
        """Authenticated user receives HTTP 200 and dashboard template is loaded."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'Admin Dashboard')

    def test_dashboard_displays_correct_database_counts(self):
        """Verify context dictionary contains exact ORM counts."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))

        # Projects counts
        self.assertEqual(response.context['total_projects'], 3)
        self.assertEqual(response.context['projects_in_progress'], 1)
        self.assertEqual(response.context['completed_projects'], 1)

        # Employees count
        self.assertEqual(response.context['total_employees'], 2)

        # Tasks counts
        # Total tasks = task1, task2, task3, task_overdue = 4
        self.assertEqual(response.context['total_tasks'], 4)
        self.assertEqual(response.context['pending_tasks'], 1)
        self.assertEqual(response.context['in_progress_tasks'], 1)
        self.assertEqual(response.context['completed_tasks'], 2)

    def test_overdue_task_calculation(self):
        """
        Overdue tasks must only count tasks whose due_date < today AND status != 'Completed'.
        - task1 (due in past, but status='Completed') -> NOT overdue
        - task3 (due in past, but status='Completed') -> NOT overdue
        - task2 (due in future, status='In Progress') -> NOT overdue
        - task_overdue (due in past, status='Pending') -> IS overdue
        Total overdue must equal exactly 1.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['overdue_tasks'], 1)

    def test_project_progress_calculation(self):
        """
        Test progress percentage calculation:
        - Alpha Project: 1 completed out of 3 tasks (task1, task2, task_overdue) = round(1/3 * 100) = 33%
        - Beta Project: 1 completed out of 1 task = 100%
        - Gamma Project: 0 tasks = 0% (safe handling, no ZeroDivisionError)
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        projects = {p.name: p for p in response.context['projects_with_progress']}

        self.assertEqual(projects['Alpha Project'].progress, 33)
        self.assertEqual(projects['Beta Project'].progress, 100)
        self.assertEqual(projects['Gamma Project (No Tasks)'].progress, 0)



class ProjectCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='projectmanager',
            password='Password123!',
            first_name='Project',
            last_name='Manager'
        )
        self.project = Project.objects.create(
            name='Initial Project',
            description='Test description',
            start_date=date.today(),
            deadline=date.today() + timedelta(days=10),
            status='Planning',
            created_by=self.user
        )

    def test_anonymous_users_redirected_to_login(self):
        urls = [
            reverse('projects:project_list'),
            reverse('projects:project_create'),
            reverse('projects:project_detail', args=[self.project.pk]),
            reverse('projects:project_update', args=[self.project.pk]),
            reverse('projects:project_delete', args=[self.project.pk]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_authenticated_user_can_view_project_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_list.html')
        self.assertContains(response, 'Initial Project')

    def test_project_list_search_filter(self):
        self.client.force_login(self.user)
        # Search match
        response = self.client.get(reverse('projects:project_list'), {'q': 'Initial'})
        self.assertContains(response, 'Initial Project')
        # Search non-match
        response = self.client.get(reverse('projects:project_list'), {'q': 'NonExistent'})
        self.assertNotContains(response, 'Initial Project')
        self.assertContains(response, 'No projects matching')

    def test_create_project_successfully(self):
        self.client.force_login(self.user)
        post_data = {
            'name': 'Brand New Portal',
            'description': 'A new development project',
            'start_date': str(date.today()),
            'deadline': str(date.today() + timedelta(days=30)),
            'status': 'In Progress',
        }
        response = self.client.post(reverse('projects:project_create'), post_data)
        new_project = Project.objects.get(name='Brand New Portal')
        self.assertRedirects(response, reverse('projects:project_detail', args=[new_project.pk]))
        self.assertEqual(new_project.created_by, self.user)
        self.assertEqual(new_project.status, 'In Progress')

    def test_create_project_invalid_dates_validation_error(self):
        self.client.force_login(self.user)
        # Deadline earlier than start date
        post_data = {
            'name': 'Invalid Date Project',
            'description': 'Invalid dates',
            'start_date': str(date.today()),
            'deadline': str(date.today() - timedelta(days=5)),
            'status': 'Planning',
        }
        response = self.client.post(reverse('projects:project_create'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(name='Invalid Date Project').exists())
        self.assertFormError(response.context['form'], 'deadline', 'Deadline cannot be earlier than start date.')

    def test_view_project_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('projects:project_detail', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_detail.html')
        self.assertContains(response, self.project.name)
        self.assertContains(response, self.project.description)

    def test_update_project_successfully(self):
        self.client.force_login(self.user)
        post_data = {
            'name': 'Updated Project Name',
            'description': 'Updated description',
            'start_date': str(self.project.start_date),
            'deadline': str(self.project.deadline),
            'status': 'Completed',
        }
        response = self.client.post(reverse('projects:project_update', args=[self.project.pk]), post_data)
        self.assertRedirects(response, reverse('projects:project_detail', args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated Project Name')
        self.assertEqual(self.project.status, 'Completed')
        # created_by remains unchanged
        self.assertEqual(self.project.created_by, self.user)

    def test_get_request_cannot_delete_project(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('projects:project_delete', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_confirm_delete.html')
        # Project must still exist in DB
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_post_request_deletes_project(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('projects:project_delete', args=[self.project.pk]))
        self.assertRedirects(response, reverse('projects:project_list'))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
