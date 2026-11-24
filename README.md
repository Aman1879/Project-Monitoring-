# ORVEXA — Web-Based Integrated Project-Monitoring Platform

> **Manage Smarter. Achieve More.** &bull; *A Premium SaaS Project & Task Management Platform*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-blue?style=for-the-badge&logo=render)](https://project-monitoring-7hqn.onrender.com/)

**ORVEXA** is a full-featured web-based project monitoring and task management application built using **Django**, **Python**, **Bootstrap 5**, and **SQLite**.

Designed for teams, administrators, and project managers to plan projects, assign tasks, track employee workloads, monitor deadlines, and visualize progress through an interactive real-time dashboard.

🌐 **Live Deployed Website**: [https://project-monitoring-7hqn.onrender.com/](https://project-monitoring-7hqn.onrender.com/)

---

## 🚀 Key Features
 
### 1. Dashboard & Real-Time Analytics
- **Live Statistics**: Total projects, projects in progress, completed projects, active employees, total tasks, pending tasks, in-progress tasks, completed tasks, and overdue tasks.
- **Overdue Task Tracking**: Automatically calculates tasks past their due date that have not been completed.
- **Recent Activities**: Instant overview of recently updated projects and tasks with status badges.

### 2. Project Management (Full CRUD)
- **Create, Read, Update, and Delete** projects.
- Attributes: Project title, detailed description, start date, deadline, status (*Planning*, *In Progress*, *Completed*, *On Hold*), and creator.
- Search and filter projects by name, description, or status.
- Dedicated project detail view showing overall progress and all associated tasks.
- Inline task creation directly from the project detail page.

### 3. Employee Management (Full CRUD & Account Linking)
- Linked directly to Django's built-in `User` model via One-to-One relationship.
- Stores employee ID, phone number, department, designation, date joined, and account credentials.
- Staff-only access control for adding, editing, and deleting employees.
- Profile overview displaying assigned tasks, active workload, and completed task history.
- Search employees by username, full name, employee ID, department, or designation.

### 4. Task Management & Workload Allocation (Full CRUD)
- Assign tasks to specific projects and employees.
- Priority levels: *Low*, *Medium*, *High*, *Urgent*.
- Task statuses: *Pending*, *In Progress*, *Completed*.
- Date validation: Prevents due dates from being scheduled earlier than start dates.
- Multi-filter task list: Filter simultaneously by search query, project, priority, and status.
- **Role-based Task Permissions**:
  - Staff / Managers can create, update all fields, and delete tasks.
  - Assigned employees can view their tasks and update their task status as work progresses.

### 5. Authentication & Access Control
- Public landing page at `/` introducing the platform and features.
- User self-registration at `/register/`.
- Secure session-based authentication with CSRF protection and password hashing (PBKDF2).
- Automatic redirection to authenticated dashboard upon login.
- Protected views using `@login_required` and `@user_passes_test` decorators.

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Django 5.x
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **CSS Framework**: Bootstrap 5.3 (via CDN) & Bootstrap Icons
- **Architecture**: Model-View-Template (MVT)

---

## 📁 Project Structure

```text
Django Proj/
├── accounts/               # Employee profiles, User auth, registration & forms
│   ├── migrations/
│   ├── models.py           # Employee model (OneToOne with User)
│   ├── views.py            # Login, logout, register, employee CRUD views
│   ├── forms.py            # UserLoginForm, UserRegistrationForm, EmployeeForms
│   ├── urls.py
│   └── tests.py
├── projects/               # Projects module & core dashboard
│   ├── migrations/
│   ├── models.py           # Project model
│   ├── views.py            # Public home, dashboard, project CRUD views
│   ├── forms.py            # ProjectForm
│   ├── urls.py
│   └── tests.py
├── tasks/                  # Task management and status workflow
│   ├── migrations/
│   ├── models.py           # Task model (FK to Project & Employee)
│   ├── views.py            # Task CRUD & employee status update views
│   ├── forms.py            # TaskForm, TaskStatusUpdateForm
│   ├── urls.py
│   └── tests.py
├── project_monitoring/     # Project settings and root URL configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/                 # Static assets (CSS, JS)
│   ├── css/style.css
│   └── js/script.js
├── templates/              # HTML templates
│   ├── base.html
│   ├── home.html           # Public landing page
│   ├── dashboard.html      # Authenticated statistics dashboard
│   ├── accounts/           # Auth & employee templates
│   ├── projects/           # Project CRUD templates
│   ├── tasks/              # Task CRUD templates
│   └── includes/           # Reusable components (navbar, sidebar)
├── manage.py
├── README.md
└── .gitignore
```

---

## ⚙️ Installation & Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Aman1879/Project-Monitoring-.git
cd Project-Monitoring-
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Django
```bash
pip install django
```

### 4. Apply Database Migrations
```bash
python manage.py migrate
```

### 5. Create a Superuser (Administrator)
```bash
python manage.py createsuperuser
```
Follow the interactive prompt to set a username, email, and password.

### 6. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🌐 Deployment on Render

- **Live URL**: [https://project-monitoring-7hqn.onrender.com/](https://project-monitoring-7hqn.onrender.com/)

This project is configured for deployment on [Render](https://render.com) using Gunicorn and WhiteNoise.

In your Render Web Service settings:
- **Environment**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --no-input
  ```
- **Start Command**:
  ```bash
  python manage.py migrate && gunicorn project_monitoring.wsgi:application
  ```
- **Environment Variables**:
  - `PYTHON_VERSION`: `3.12.0`
  - `DEBUG`: `False`
  - `SECRET_KEY`: *(Generate in Render or provide a secure key)*
  - `ALLOWED_HOSTS`: `.onrender.com`

---

## 🧪 Running Automated Tests

The platform includes a test suite with 59 automated test cases covering model relationships, form validations, role-based view permissions, and CRUD operations:

```bash
python manage.py test
```

To run tests for a specific application:
```bash
python manage.py test accounts
python manage.py test projects
python manage.py test tasks
```

---

## 👤 Author

- **GitHub**: [@Aman1879](https://github.com/Aman1879)

