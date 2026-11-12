from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        # Create a test user for authentication tests
        self.username = 'testuser'
        self.password = 'StrongPass123!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='testuser@example.com',
            first_name='Alex',
            last_name='Morgan'
        )

    def test_login_page_renders_successfully(self):
        """Test that the login page returns HTTP 200 on GET and renders login form."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Project Monitoring System')
        self.assertContains(response, 'Sign In')

    def test_valid_login_redirects_and_authenticates(self):
        """Test valid credentials log in user and redirect to the protected dashboard page."""
        response = self.client.post(reverse('accounts:login'), {
            'username': self.username,
            'password': self.password,
        })
        # Should redirect to 'dashboard' (URL '/')
        self.assertRedirects(response, reverse('dashboard'))
        # User session should now be authenticated
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_invalid_login_shows_error(self):
        """Test invalid credentials fail, show error, and do not create authenticated session."""
        response = self.client.post(reverse('accounts:login'), {
            'username': self.username,
            'password': 'WrongPassword123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Invalid username or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_authenticated_user_redirected_away_from_login(self):
        """Already logged in users should be redirected when visiting login page."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_anonymous_user_can_access_public_homepage(self):
        """Test anonymous user can access public homepage with Login and Register links."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, 'Web-Based Integrated Project-Monitoring Platform')
        self.assertContains(response, reverse('accounts:login'))
        self.assertContains(response, reverse('register'))

    def test_logout_clears_session(self):
        """Test POST logout terminates session and redirects to public homepage."""
        self.client.force_login(self.user)
        # Verify authenticated before logout
        self.assertIn('_auth_user_id', self.client.session)

        # POST to logout
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('home'))
        # Verify session is cleared
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_via_get_method_rejected(self):
        """GET request to logout must return 405 Method Not Allowed due to @require_POST."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_cannot_access_protected_page(self):
        """Anonymous user trying to access protected dashboard page is redirected to login."""
        response = self.client.get(reverse('dashboard'))
        expected_redirect = f"{reverse('accounts:login')}?next={reverse('dashboard')}"
        self.assertRedirects(response, expected_redirect)

    def test_authenticated_user_can_access_protected_page(self):
        """Authenticated user can access protected dashboard page directly (HTTP 200)."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertContains(response, self.username)

from datetime import date
from django.contrib.auth.hashers import check_password
from accounts.models import Employee


class EmployeeManagementTests(TestCase):
    def setUp(self):
        # Admin / Staff user
        self.staff_user = User.objects.create_user(
            username='staffadmin',
            password='StaffPassword123!',
            is_staff=True,
            first_name='Admin',
            last_name='Staff'
        )
        self.staff_employee = Employee.objects.create(
            user=self.staff_user,
            employee_id='STAFF001',
            department='Management',
            designation='Admin Director',
            date_joined=date.today()
        )

        # Standard non-staff user
        self.regular_user = User.objects.create_user(
            username='regularemployee',
            password='RegularPassword123!',
            is_staff=False,
            first_name='Bob',
            last_name='Builder'
        )
        self.regular_employee = Employee.objects.create(
            user=self.regular_user,
            employee_id='EMP200',
            department='Engineering',
            designation='Developer',
            date_joined=date.today()
        )

    def test_anonymous_users_redirected_to_login(self):
        urls = [
            reverse('accounts:employee_list'),
            reverse('accounts:employee_create'),
            reverse('accounts:employee_detail', args=[self.regular_employee.pk]),
            reverse('accounts:employee_update', args=[self.regular_employee.pk]),
            reverse('accounts:employee_delete', args=[self.regular_employee.pk]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_authenticated_non_staff_users_cannot_create_edit_delete(self):
        self.client.force_login(self.regular_user)
        # Attempting create
        resp_create = self.client.get(reverse('accounts:employee_create'))
        self.assertRedirects(resp_create, f"{reverse('accounts:login')}?next={reverse('accounts:employee_create')}", fetch_redirect_response=False)

        # Attempting edit
        resp_edit = self.client.get(reverse('accounts:employee_update', args=[self.regular_employee.pk]))
        self.assertRedirects(resp_edit, f"{reverse('accounts:login')}?next={reverse('accounts:employee_update', args=[self.regular_employee.pk])}", fetch_redirect_response=False)

        # Attempting delete
        resp_del = self.client.post(reverse('accounts:employee_delete', args=[self.regular_employee.pk]))
        self.assertRedirects(resp_del, f"{reverse('accounts:login')}?next={reverse('accounts:employee_delete', args=[self.regular_employee.pk])}", fetch_redirect_response=False)
        self.assertTrue(Employee.objects.filter(pk=self.regular_employee.pk).exists())

    def test_staff_users_can_access_employee_list(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('accounts:employee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/employee_list.html')
        self.assertContains(response, 'Bob Builder')
        self.assertContains(response, 'EMP200')

    def test_staff_users_can_create_employee_with_linked_user(self):
        self.client.force_login(self.staff_user)
        post_data = {
            'username': 'newcoder',
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'email': 'alice@example.com',
            'password': 'SuperSecurePassword999!',
            'employee_id': 'EMP301',
            'phone': '1234567890',
            'department': 'DevOps',
            'designation': 'Cloud Engineer',
            'date_joined': str(date.today()),
        }
        response = self.client.post(reverse('accounts:employee_create'), post_data)
        self.assertEqual(response.status_code, 302)

        # Verify employee and user exist and are linked
        created_emp = Employee.objects.get(employee_id='EMP301')
        self.assertEqual(created_emp.user.username, 'newcoder')
        self.assertEqual(created_emp.user.first_name, 'Alice')
        self.assertEqual(created_emp.department, 'DevOps')
        self.assertRedirects(response, reverse('accounts:employee_detail', args=[created_emp.pk]))

    def test_password_stored_as_hash_and_verified(self):
        self.client.force_login(self.staff_user)
        raw_password = 'MySecretPassword123#'
        post_data = {
            'username': 'hashcheckuser',
            'password': raw_password,
            'employee_id': 'EMP302',
            'department': 'Security',
            'designation': 'SecOps',
            'date_joined': str(date.today()),
        }
        self.client.post(reverse('accounts:employee_create'), post_data)
        user = User.objects.get(username='hashcheckuser')

        # Password must NOT be stored as raw text
        self.assertNotEqual(user.password, raw_password)
        # Password hash must verify with check_password
        self.assertTrue(check_password(raw_password, user.password))

    def test_duplicate_usernames_rejected(self):
        self.client.force_login(self.staff_user)
        post_data = {
            'username': self.regular_user.username,  # Duplicate username
            'password': 'SomePass123!',
            'employee_id': 'EMP999',
            'department': 'Security',
            'designation': 'SecOps',
            'date_joined': str(date.today()),
        }
        response = self.client.post(reverse('accounts:employee_create'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Employee.objects.filter(employee_id='EMP999').exists())
        self.assertFormError(response.context['form'], 'username', 'A user with this username already exists.')

    def test_employee_details_display_correctly(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('accounts:employee_detail', args=[self.regular_employee.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/employee_detail.html')
        self.assertContains(response, 'EMP200')
        self.assertContains(response, '@regularemployee')
        self.assertContains(response, 'Engineering')

    def test_staff_users_can_update_employee_and_linked_user(self):
        self.client.force_login(self.staff_user)
        update_data = {
            'first_name': 'Robert',
            'last_name': 'Builder Updated',
            'email': 'robert.builder@example.com',
            'employee_id': 'EMP200',
            'phone': '9998887777',
            'department': 'Platform Engineering',
            'designation': 'Lead Architect',
            'date_joined': str(self.regular_employee.date_joined),
        }
        response = self.client.post(
            reverse('accounts:employee_update', args=[self.regular_employee.pk]),
            update_data
        )
        self.assertRedirects(response, reverse('accounts:employee_detail', args=[self.regular_employee.pk]))
        self.regular_employee.refresh_from_db()
        self.assertEqual(self.regular_employee.user.first_name, 'Robert')
        self.assertEqual(self.regular_employee.department, 'Platform Engineering')
        self.assertEqual(self.regular_employee.phone, '9998887777')

    def test_updating_employee_does_not_change_password(self):
        self.client.force_login(self.staff_user)
        initial_password_hash = self.regular_user.password
        update_data = {
            'first_name': 'Bob',
            'last_name': 'Builder',
            'email': 'bob@example.com',
            'employee_id': 'EMP200',
            'department': 'Engineering',
            'designation': 'Senior Developer',
            'date_joined': str(self.regular_employee.date_joined),
        }
        self.client.post(
            reverse('accounts:employee_update', args=[self.regular_employee.pk]),
            update_data
        )
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.password, initial_password_hash)

    def test_get_request_cannot_create_or_delete_employee(self):
        self.client.force_login(self.staff_user)
        # GET request to create should just render form without creating record
        resp_create = self.client.get(reverse('accounts:employee_create'))
        self.assertEqual(resp_create.status_code, 200)
        self.assertTemplateUsed(resp_create, 'accounts/employee_form.html')

        # GET request to delete should render confirmation page and NOT delete record
        resp_del = self.client.get(reverse('accounts:employee_delete', args=[self.regular_employee.pk]))
        self.assertEqual(resp_del.status_code, 200)
        self.assertTemplateUsed(resp_del, 'accounts/employee_confirm_delete.html')
        self.assertTrue(Employee.objects.filter(pk=self.regular_employee.pk).exists())

    def test_post_request_can_delete_employee(self):
        self.client.force_login(self.staff_user)
        emp_pk = self.regular_employee.pk
        user_pk = self.regular_user.pk
        response = self.client.post(reverse('accounts:employee_delete', args=[emp_pk]))
        self.assertRedirects(response, reverse('accounts:employee_list'))
        self.assertFalse(Employee.objects.filter(pk=emp_pk).exists())
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    def test_search_works_correctly(self):
        self.client.force_login(self.staff_user)
        # Search by ID
        resp_id = self.client.get(reverse('accounts:employee_list'), {'q': 'EMP200'})
        self.assertContains(resp_id, 'EMP200')
        self.assertNotContains(resp_id, 'STAFF001')

        # Search by Department
        resp_dept = self.client.get(reverse('accounts:employee_list'), {'q': 'Engineering'})
        self.assertContains(resp_dept, 'EMP200')
        self.assertNotContains(resp_dept, 'STAFF001')

        # Search non-match
        resp_none = self.client.get(reverse('accounts:employee_list'), {'q': 'NonExistent'})
        self.assertContains(resp_none, 'No employees matching')



class RegistrationTests(TestCase):
    def test_registration_page_renders_successfully(self):
        """Test public registration page loads with form and fields."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        self.assertContains(response, 'Create an Account')

    def test_authenticated_user_redirected_away_from_register(self):
        """Already logged in user visiting /register/ is redirected to dashboard."""
        user = User.objects.create_user(username='reguser', password='Password123!')
        self.client.force_login(user)
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_successful_registration_creates_user_and_logs_in(self):
        """Valid registration creates non-staff User, hashes password, logs user in, and redirects to dashboard."""
        post_data = {
            'username': 'john_new',
            'first_name': 'John',
            'last_name': 'New',
            'email': 'john.new@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
        }
        response = self.client.post(reverse('register'), post_data)
        self.assertRedirects(response, reverse('dashboard'))

        # Verify user exists in database
        user = User.objects.get(username='john_new')
        self.assertEqual(user.first_name, 'John')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        # Verify password hash
        self.assertNotEqual(user.password, 'SecurePassword123!')
        self.assertTrue(check_password('SecurePassword123!', user.password))
        # Verify user is logged in
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_duplicate_username_rejected(self):
        """Attempting to register an already taken username is rejected with form error."""
        User.objects.create_user(username='existinguser', password='Password123!')
        post_data = {
            'username': 'existinguser',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
        }
        response = self.client.post(reverse('register'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'A user with this username already exists.')

    def test_registration_password_mismatch_rejected(self):
        """Passwords that do not match are rejected with form error and no user is created."""
        post_data = {
            'username': 'mismatchuser',
            'password': 'Password123!',
            'password_confirm': 'DifferentPassword456!',
        }
        response = self.client.post(reverse('register'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'password_confirm', 'Passwords do not match.')
        self.assertFalse(User.objects.filter(username='mismatchuser').exists())
