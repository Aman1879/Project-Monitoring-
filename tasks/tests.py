from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from accounts.models import Employee
from projects.models import Project
from tasks.models import Task


class ModelRelationshipTests(TestCase):
    def setUp(self):
        # 1. Create a user
        self.user = User.objects.create_user(
            username='johndoe',
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe'
        )

        # 2. Create an employee linked to the user
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id='EMP001',
            phone='9876543210',
            department='Engineering',
            designation='Software Engineer',
            date_joined=date.today()
        )

        # 3. Create a project
        self.project = Project.objects.create(
            name='Campus Portal',
            description='Project monitoring platform',
            start_date=date.today(),
            deadline=date.today() + timedelta(days=30),
            status='In Progress',
            created_by=self.user
        )

    def test_employee_creation_and_str(self):
        self.assertEqual(str(self.employee), 'John Doe (EMP001)')
        self.assertEqual(self.user.employee_profile, self.employee)

    def test_project_creation_and_str(self):
        self.assertEqual(str(self.project), 'Campus Portal')
        self.assertEqual(self.project.created_by, self.user)

    def test_task_creation_and_relationships(self):
        task = Task.objects.create(
            title='Design Database Schema',
            description='Create ER diagram and models',
            project=self.project,
            assigned_to=self.employee,
            priority='High',
            status='Pending',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=5)
        )
        self.assertEqual(str(task), 'Design Database Schema (Campus Portal)')
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.assigned_to, self.employee)
        # Test reverse relationships
        self.assertIn(task, self.project.tasks.all())
        self.assertIn(task, self.employee.tasks.all())

    def test_task_invalid_due_date_validation(self):
        # Due date earlier than start date must raise ValidationError
        invalid_task = Task(
            title='Invalid Task Dates',
            project=self.project,
            assigned_to=self.employee,
            start_date=date.today(),
            due_date=date.today() - timedelta(days=2)
        )
        with self.assertRaises(ValidationError):
            invalid_task.clean()

    def test_dashboard_page_renders_successfully(self):
        self.client.force_login(self.user)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertTemplateUsed(response, 'includes/navbar.html')
        self.assertTemplateUsed(response, 'includes/sidebar.html')
        self.assertContains(response, 'Project Monitoring System')
        self.assertContains(response, 'TrackPoint')



class TaskManagementTests(TestCase):
    def setUp(self):
        # 1. Staff Admin User & Employee
        self.staff_user = User.objects.create_user(
            username='taskadmin',
            password='Password123!',
            is_staff=True,
            first_name='Admin',
            last_name='Staff'
        )
        self.staff_emp = Employee.objects.create(
            user=self.staff_user,
            employee_id='TADMIN01',
            department='Administration',
            designation='Project Director'
        )

        # 2. Regular Employee 1
        self.emp1_user = User.objects.create_user(
            username='worker_one',
            password='Password123!',
            is_staff=False,
            first_name='Worker',
            last_name='One'
        )
        self.emp1 = Employee.objects.create(
            user=self.emp1_user,
            employee_id='EMP100',
            department='Backend',
            designation='Engineer'
        )

        # 3. Regular Employee 2
        self.emp2_user = User.objects.create_user(
            username='worker_two',
            password='Password123!',
            is_staff=False,
            first_name='Worker',
            last_name='Two'
        )
        self.emp2 = Employee.objects.create(
            user=self.emp2_user,
            employee_id='EMP200',
            department='Frontend',
            designation='Designer'
        )

        # 4. Project
        self.project = Project.objects.create(
            name='Core Infrastructure',
            description='Infrastructure project',
            start_date=date.today(),
            deadline=date.today() + timedelta(days=60),
            status='In Progress',
            created_by=self.staff_user
        )

        # 5. Task 1 assigned to Employee 1
        self.task1 = Task.objects.create(
            title='Backend Database API',
            description='Build REST API endpoints',
            project=self.project,
            assigned_to=self.emp1,
            priority='High',
            status='Pending',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=10)
        )

        # 6. Task 2 assigned to Employee 2
        self.task2 = Task.objects.create(
            title='Frontend UI Mockup',
            description='Build responsive layout',
            project=self.project,
            assigned_to=self.emp2,
            priority='Medium',
            status='In Progress',
            start_date=date.today(),
            due_date=date.today() + timedelta(days=15)
        )

    def test_anonymous_user_redirected_to_login(self):
        urls = [
            reverse('tasks:task_list'),
            reverse('tasks:task_create'),
            reverse('tasks:task_detail', args=[self.task1.pk]),
            reverse('tasks:task_update', args=[self.task1.pk]),
            reverse('tasks:task_delete', args=[self.task1.pk]),
            reverse('tasks:task_update_status', args=[self.task1.pk]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_staff_users_can_view_all_tasks(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tasks/task_list.html')
        self.assertContains(response, 'Backend Database API')
        self.assertContains(response, 'Frontend UI Mockup')

    def test_staff_users_can_create_tasks(self):
        self.client.force_login(self.staff_user)
        post_data = {
            'title': 'Setup CI/CD Pipeline',
            'description': 'Automated testing and build scripts',
            'project': self.project.pk,
            'assigned_to': self.emp1.pk,
            'priority': 'High',
            'status': 'Pending',
            'start_date': str(date.today()),
            'due_date': str(date.today() + timedelta(days=7)),
        }
        response = self.client.post(reverse('tasks:task_create'), post_data)
        created_task = Task.objects.get(title='Setup CI/CD Pipeline')
        self.assertRedirects(response, reverse('tasks:task_detail', args=[created_task.pk]))
        self.assertEqual(created_task.assigned_to, self.emp1)
        self.assertEqual(created_task.priority, 'High')

    def test_staff_users_can_update_tasks(self):
        self.client.force_login(self.staff_user)
        update_data = {
            'title': 'Backend Database API v2',
            'description': 'Enhanced description',
            'project': self.project.pk,
            'assigned_to': self.emp2.pk,  # Reassign to emp2
            'priority': 'Low',
            'status': 'Completed',
            'start_date': str(self.task1.start_date),
            'due_date': str(self.task1.due_date),
        }
        response = self.client.post(reverse('tasks:task_update', args=[self.task1.pk]), update_data)
        self.assertRedirects(response, reverse('tasks:task_detail', args=[self.task1.pk]))
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.title, 'Backend Database API v2')
        self.assertEqual(self.task1.assigned_to, self.emp2)
        self.assertEqual(self.task1.status, 'Completed')

    def test_staff_users_can_delete_tasks_using_post(self):
        self.client.force_login(self.staff_user)
        task_pk = self.task1.pk
        response = self.client.post(reverse('tasks:task_delete', args=[task_pk]))
        self.assertRedirects(response, reverse('tasks:task_list'))
        self.assertFalse(Task.objects.filter(pk=task_pk).exists())

    def test_get_request_cannot_delete_task(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('tasks:task_delete', args=[self.task1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tasks/task_confirm_delete.html')
        self.assertTrue(Task.objects.filter(pk=self.task1.pk).exists())

    def test_task_due_date_validation_works(self):
        self.client.force_login(self.staff_user)
        # Due date before start date
        post_data = {
            'title': 'Invalid Dates Task',
            'project': self.project.pk,
            'assigned_to': self.emp1.pk,
            'priority': 'Medium',
            'status': 'Pending',
            'start_date': str(date.today()),
            'due_date': str(date.today() - timedelta(days=3)),
        }
        response = self.client.post(reverse('tasks:task_create'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'due_date', 'Due date cannot be earlier than start date.')
        self.assertFalse(Task.objects.filter(title='Invalid Dates Task').exists())

    def test_task_can_be_assigned_to_an_employee(self):
        self.assertEqual(self.task1.assigned_to, self.emp1)
        self.assertEqual(self.task1.assigned_to.user.username, 'worker_one')

    def test_regular_employees_only_see_their_assigned_tasks(self):
        # Worker 1 logs in
        self.client.force_login(self.emp1_user)
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 200)
        # Worker 1 should see task1
        self.assertContains(response, 'Backend Database API')
        # Worker 1 should NOT see task2
        self.assertNotContains(response, 'Frontend UI Mockup')

    def test_regular_employees_cannot_view_another_employees_task(self):
        # Worker 1 tries to view task2 (assigned to Worker 2)
        self.client.force_login(self.emp1_user)
        response = self.client.get(reverse('tasks:task_detail', args=[self.task2.pk]))
        self.assertEqual(response.status_code, 403)

    def test_regular_employees_can_update_their_own_task_status(self):
        # Worker 1 updates status of task1 from Pending to Completed
        self.client.force_login(self.emp1_user)
        post_data = {'status': 'Completed'}
        response = self.client.post(reverse('tasks:task_update_status', args=[self.task1.pk]), post_data)
        self.assertRedirects(response, reverse('tasks:task_detail', args=[self.task1.pk]))
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.status, 'Completed')

    def test_regular_employees_cannot_update_another_employees_task_status(self):
        # Worker 1 tries to update task2 (assigned to Worker 2)
        self.client.force_login(self.emp1_user)
        post_data = {'status': 'Completed'}
        response = self.client.post(reverse('tasks:task_update_status', args=[self.task2.pk]), post_data)
        self.assertEqual(response.status_code, 403)

    def test_regular_employees_cannot_edit_full_task_details(self):
        # Worker 1 tries to access full edit view
        self.client.force_login(self.emp1_user)
        response = self.client.get(reverse('tasks:task_update', args=[self.task1.pk]))
        self.assertEqual(response.status_code, 403)

    def test_task_filters_and_search_work(self):
        self.client.force_login(self.staff_user)
        # Search by title
        resp_q = self.client.get(reverse('tasks:task_list'), {'q': 'Database'})
        self.assertContains(resp_q, 'Backend Database API')
        self.assertNotContains(resp_q, 'Frontend UI Mockup')

        # Filter by priority
        resp_prio = self.client.get(reverse('tasks:task_list'), {'priority': 'High'})
        self.assertContains(resp_prio, 'Backend Database API')
        self.assertNotContains(resp_prio, 'Frontend UI Mockup')

        # Filter by status
        resp_status = self.client.get(reverse('tasks:task_list'), {'status': 'In Progress'})
        self.assertContains(resp_status, 'Frontend UI Mockup')
        self.assertNotContains(resp_status, 'Backend Database API')
