from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import Employee


class EmployeeCreationForm(forms.Form):
    """
    Form to create both a Django User and linked Employee profile together.
    Securely hashes the password using user.set_password().
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. jsmith'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Smith'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. jsmith@example.com'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter strong password'})
    )
    employee_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP101'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +1 555-0199'})
    )
    department = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Software Engineering'})
    )
    designation = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Backend Developer'})
    )
    date_joined = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id', '').strip()
        if Employee.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError('An employee with this Employee ID already exists.')
        return employee_id

    def save(self):
        """
        Creates User and Employee records atomically in a single database transaction.
        """
        with transaction.atomic():
            # 1. Create User and securely hash password
            user = User(
                username=self.cleaned_data['username'],
                email=self.cleaned_data.get('email', ''),
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', '')
            )
            user.set_password(self.cleaned_data['password'])
            user.save()

            # 2. Create linked Employee profile
            employee = Employee.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                phone=self.cleaned_data.get('phone', ''),
                department=self.cleaned_data['department'],
                designation=self.cleaned_data['designation'],
                date_joined=self.cleaned_data['date_joined']
            )
            return employee


class EmployeeUpdateForm(forms.Form):
    """
    Form for updating an existing Employee and linked User details.
    Does NOT modify the user's password.
    """
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Smith'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. jsmith@example.com'})
    )
    employee_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP101'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +1 555-0199'})
    )
    department = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Software Engineering'})
    )
    designation = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Backend Developer'})
    )
    date_joined = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['employee_id'].initial = self.instance.employee_id
            self.fields['phone'].initial = self.instance.phone
            self.fields['department'].initial = self.instance.department
            self.fields['designation'].initial = self.instance.designation
            self.fields['date_joined'].initial = self.instance.date_joined

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id', '').strip()
        query = Employee.objects.filter(employee_id=employee_id)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError('An employee with this Employee ID already exists.')
        return employee_id

    def save(self):
        """
        Updates both the linked User and Employee records in a single database transaction.
        """
        with transaction.atomic():
            # 1. Update linked User record
            user = self.instance.user
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.save()

            # 2. Update Employee record
            employee = self.instance
            employee.employee_id = self.cleaned_data['employee_id']
            employee.phone = self.cleaned_data.get('phone', '')
            employee.department = self.cleaned_data['department']
            employee.designation = self.cleaned_data['designation']
            employee.date_joined = self.cleaned_data['date_joined']
            employee.save()

            return employee




class UserRegistrationForm(forms.Form):
    """
    Public user registration form.
    Validates username uniqueness and password matching, hashes password with set_password(),
    and ensures registered users cannot register with staff or superuser privileges.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name (optional)'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name (optional)'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address (optional)'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a secure password'})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter your password'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        return cleaned_data

    def save(self):
        """
        Creates the User, securely hashes the password, and ensures non-staff/non-superuser flags.
        """
        user = User(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            email=self.cleaned_data.get('email', '')
        )
        user.set_password(self.cleaned_data['password'])
        user.is_staff = False
        user.is_superuser = False
        user.save()
        return user
