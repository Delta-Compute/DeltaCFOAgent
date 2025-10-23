# Authentication & User Sessions Implementation Plan

**Project:** DeltaCFOAgent - Add Login/Sessions
**Date:** October 22, 2025
**Status:** 📋 PLANNING PHASE - Awaiting User Approval

---

## Overview

Add user authentication and session management to the DeltaCFOAgent platform. This will secure all endpoints, track user actions, and enable multi-user support with role-based access control.

## Current State Analysis

### What Exists
✅ Flask app with secret key configured (`app.secret_key`)
✅ PostgreSQL database with connection manager
✅ Session import in app_db.py (but not used)
✅ Multiple business entities defined
✅ User interaction tracking table (but no user_id foreign key)

### What's Missing
❌ Users table in database
❌ Authentication service/library
❌ Login/logout routes and UI
❌ Password hashing implementation
❌ Session management logic
❌ Protected route decorators
❌ User registration flow
❌ Role-based access control

## Design Decisions

### 1. Authentication Approach

**Option A: Flask-Login (Recommended) ✅**
- Industry standard for Flask apps
- Simple session-based authentication
- Built-in decorators (@login_required)
- Easy to extend with roles
- Well documented

**Option B: JWT Tokens**
- Stateless authentication
- Good for APIs/mobile apps
- More complex implementation
- Overkill for this use case

**Decision: Use Flask-Login for simplicity and Flask best practices**

### 2. Password Security

**Approach: Werkzeug password hashing ✅**
- Built-in with Flask
- Uses PBKDF2 by default
- Secure and tested
- Simple API: `generate_password_hash()`, `check_password_hash()`

### 3. User Roles

**Proposed Roles:**
1. **Admin** - Full access to everything
   - Manage users
   - View/edit all entities
   - Configure system settings
   - Access all dashboards

2. **Manager** - Full business access
   - View/edit all transactions
   - Upload receipts/invoices
   - Access all dashboards
   - Cannot manage users

3. **Accountant** - Financial operations
   - View/edit transactions
   - Upload receipts/invoices
   - Access dashboards
   - Cannot configure system

4. **Viewer** - Read-only access
   - View dashboards
   - View transactions (read-only)
   - Cannot edit or upload

### 4. Multi-Tenancy Strategy

**Entity-Based Access Control:**
- Users can be assigned to specific business entities
- Admins see all entities
- Others see only their assigned entities
- Configurable per user in database

**Example:**
- User "Alice" → Delta LLC only
- User "Bob" → Delta Mining Paraguay S.A. only
- Admin "Charlie" → All entities

### 5. Session Management

**Strategy:**
- Server-side sessions (Flask default)
- Session stored in secure cookie
- 24-hour session timeout (configurable)
- "Remember Me" option for 30 days
- Logout clears session

---

## Implementation Tasks

### Phase 1: Database Schema (Tasks 1-3)

#### Task 1: Create Users Table
**Difficulty:** Easy | **Time:** 30 minutes

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'viewer',  -- admin, manager, accountant, viewer
    active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)  -- Who created this user
);

-- Indexes for performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(active);
```

**Files to modify:**
- `postgres_unified_schema.sql` - Add users table
- New migration script: `migrations/001_add_users_table.sql`

#### Task 2: Create User-Entity Associations Table
**Difficulty:** Easy | **Time:** 20 minutes

```sql
CREATE TABLE user_entity_access (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    entity_name VARCHAR(100) NOT NULL,  -- Must match business_entities.name
    access_level VARCHAR(20) DEFAULT 'read',  -- read, write, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, entity_name)
);

-- Index for quick lookups
CREATE INDEX idx_user_entity_user ON user_entity_access(user_id);
CREATE INDEX idx_user_entity_entity ON user_entity_access(entity_name);
```

**Purpose:** Control which business entities each user can access

#### Task 3: Update Existing Tables with User Tracking
**Difficulty:** Easy | **Time:** 30 minutes

Add `user_id` columns to existing tables:

```sql
-- Track who created/modified transactions
ALTER TABLE transactions ADD COLUMN created_by INTEGER REFERENCES users(id);
ALTER TABLE transactions ADD COLUMN updated_by INTEGER REFERENCES users(id);

-- Track who uploaded receipts (for future receipt table)
-- Will be added when receipts migrate to database

-- Update user_interactions table
ALTER TABLE user_interactions ADD COLUMN user_id INTEGER REFERENCES users(id);

-- Track invoice actions
ALTER TABLE invoices ADD COLUMN created_by INTEGER REFERENCES users(id);
ALTER TABLE invoices ADD COLUMN updated_by INTEGER REFERENCES users(id);
```

**Files to modify:**
- New migration script: `migrations/002_add_user_tracking.sql`

---

### Phase 2: Authentication Service (Tasks 4-6)

#### Task 4: Create User Authentication Service
**Difficulty:** Medium | **Time:** 1.5 hours

**File:** `web_ui/services/auth_service.py`

```python
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """User authentication service"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def create_user(self, username: str, email: str, password: str,
                   full_name: str = None, role: str = 'viewer',
                   created_by: int = None) -> Dict[str, Any]:
        """Create a new user with hashed password"""

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user by username/password"""

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID for session management"""

    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password"""

    def reset_password(self, email: str) -> str:
        """Generate password reset token (future: email it)"""

    def get_user_entities(self, user_id: int) -> list:
        """Get list of entities user can access"""

    def check_entity_access(self, user_id: int, entity_name: str,
                           access_level: str = 'read') -> bool:
        """Check if user has access to specific entity"""
```

**Key Features:**
- Password hashing with Werkzeug
- User CRUD operations
- Entity access checking
- Last login tracking
- Password reset capability

#### Task 5: Create User Model Class (Flask-Login Integration)
**Difficulty:** Easy | **Time:** 30 minutes

**File:** `web_ui/models/user.py`

```python
from flask_login import UserMixin

class User(UserMixin):
    """User model for Flask-Login"""

    def __init__(self, user_id, username, email, full_name, role, active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.role = role
        self.active = active

    def get_id(self):
        return str(self.id)

    def is_active(self):
        return self.active

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role in ['admin', 'manager']

    def can_edit(self):
        return self.role in ['admin', 'manager', 'accountant']

    def can_view_entity(self, entity_name):
        # Check user_entity_access table
        pass
```

#### Task 6: Set Up Flask-Login
**Difficulty:** Easy | **Time:** 30 minutes

**File:** `web_ui/app_db.py` (modifications)

```python
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from models.user import User
from services.auth_service import AuthService

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect here if not authenticated
login_manager.login_message = 'Please log in to access this page.'

# Initialize auth service
auth_service = AuthService(db_manager)

@login_manager.user_loader
def load_user(user_id):
    """Load user from database for Flask-Login"""
    user_data = auth_service.get_user_by_id(int(user_id))
    if user_data:
        return User(
            user_id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data['full_name'],
            role=user_data['role'],
            active=user_data['active']
        )
    return None
```

---

### Phase 3: Login/Logout UI (Tasks 7-9)

#### Task 7: Create Login Page
**Difficulty:** Medium | **Time:** 1 hour

**File:** `web_ui/templates/login.html`

**Features:**
- Clean, modern login form
- Username and password fields
- "Remember Me" checkbox
- Error message display
- Forgot password link (placeholder for now)
- Responsive design matching existing UI

**UI Mockup:**
```
┌─────────────────────────────────────┐
│                                     │
│         DeltaCFO Agent              │
│         Financial Dashboard         │
│                                     │
│    ┌─────────────────────────┐     │
│    │  Username               │     │
│    ├─────────────────────────┤     │
│    │  ___________________    │     │
│    │                         │     │
│    │  Password               │     │
│    ├─────────────────────────┤     │
│    │  ___________________    │     │
│    │                         │     │
│    │  ☐ Remember Me          │     │
│    │                         │     │
│    │  [     Login     ]      │     │
│    │                         │     │
│    │  Forgot password?       │     │
│    └─────────────────────────┘     │
│                                     │
└─────────────────────────────────────┘
```

#### Task 8: Create Login/Logout Routes
**Difficulty:** Easy | **Time:** 45 minutes

**File:** `web_ui/app_db.py` (add routes)

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user_data = auth_service.authenticate_user(username, password)

        if user_data:
            user = User(
                user_id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                full_name=user_data['full_name'],
                role=user_data['role']
            )
            login_user(user, remember=remember)
            auth_service.update_last_login(user.id)

            # Redirect to next page or homepage
            next_page = request.args.get('next')
            return redirect(next_page or url_for('homepage'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
```

#### Task 9: Add User Profile Page
**Difficulty:** Easy | **Time:** 45 minutes

**File:** `web_ui/templates/profile.html`

**Features:**
- Display user information
- Change password form
- View assigned entities
- View role and permissions
- Last login timestamp

**Route:**
```python
@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_entities = auth_service.get_user_entities(current_user.id)
    return render_template('profile.html',
                         user=current_user,
                         entities=user_entities)

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))

    success = auth_service.change_password(current_user.id, old_password, new_password)

    if success:
        flash('Password changed successfully', 'success')
    else:
        flash('Current password is incorrect', 'error')

    return redirect(url_for('profile'))
```

---

### Phase 4: Protect Existing Routes (Tasks 10-11)

#### Task 10: Add @login_required to All Routes
**Difficulty:** Easy | **Time:** 1 hour

**Strategy:**
1. Add `@login_required` decorator to all routes except:
   - `/login` (obviously)
   - `/health` (for monitoring)
   - `/static/*` (CSS/JS files)

2. Public vs Protected routes:
   - **Public:** `/login`, `/health`, `/static`
   - **Protected:** Everything else

**Example modifications:**
```python
@app.route('/')
@login_required  # ← ADD THIS
def homepage():
    """Business overview homepage"""
    ...

@app.route('/dashboard')
@login_required  # ← ADD THIS
def dashboard():
    """Main dashboard page"""
    ...

@app.route('/api/transactions')
@login_required  # ← ADD THIS
def api_transactions():
    """API endpoint to get filtered transactions"""
    ...
```

**Files to modify:**
- `web_ui/app_db.py` - Add decorator to ~50+ routes
- Can use a before_request hook as alternative for API routes

#### Task 11: Create Role-Based Decorators
**Difficulty:** Medium | **Time:** 45 minutes

**File:** `web_ui/auth_decorators.py`

```python
from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """Require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized
        if current_user.role != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    """Require manager or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role not in ['admin', 'manager']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def can_edit_required(f):
    """Require edit permissions (admin, manager, or accountant)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role not in ['admin', 'manager', 'accountant']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def entity_access_required(access_level='read'):
    """Require access to specific entity"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            entity = request.args.get('entity') or request.form.get('entity')
            if not entity:
                return f(*args, **kwargs)  # No entity filter = show all (if admin)

            if current_user.role == 'admin':
                return f(*args, **kwargs)  # Admins see everything

            # Check user has access to this entity
            if not auth_service.check_entity_access(current_user.id, entity, access_level):
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

**Usage examples:**
```python
@app.route('/admin/users')
@admin_required  # Only admins
def admin_users():
    """User management page"""
    ...

@app.route('/api/update_transaction', methods=['POST'])
@can_edit_required  # Admins, managers, and accountants
def update_transaction():
    """Update transaction endpoint"""
    ...
```

---

### Phase 5: User Management (Tasks 12-13)

#### Task 12: Create User Management Page (Admin Only)
**Difficulty:** Medium | **Time:** 1.5 hours

**File:** `web_ui/templates/admin/users.html`

**Features:**
- List all users in a table
- Add new user form
- Edit user (change role, active status)
- Delete user (with confirmation)
- Assign entities to users
- Search/filter users

**Table columns:**
- Username
- Email
- Full Name
- Role
- Active Status
- Last Login
- Created Date
- Actions (Edit, Delete)

**Route:**
```python
@app.route('/admin/users')
@admin_required
def admin_users():
    """User management page"""
    users = auth_service.get_all_users()
    entities = get_all_business_entities()
    return render_template('admin/users.html', users=users, entities=entities)

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    """Create new user"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    role = request.form.get('role')

    try:
        user = auth_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            created_by=current_user.id
        )
        flash(f'User {username} created successfully', 'success')
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'error')

    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete user"""
    if user_id == current_user.id:
        flash('Cannot delete your own account', 'error')
    else:
        auth_service.delete_user(user_id)
        flash('User deleted successfully', 'success')

    return redirect(url_for('admin_users'))
```

#### Task 13: Create Entity Assignment Interface
**Difficulty:** Medium | **Time:** 1 hour

**File:** `web_ui/templates/admin/user_entities.html`

**Features:**
- Checkboxes for each entity
- Access level dropdown (read, write, admin)
- Save button
- Visual indication of current assignments

**Route:**
```python
@app.route('/admin/users/<int:user_id>/entities', methods=['GET', 'POST'])
@admin_required
def admin_user_entities(user_id):
    """Manage user entity access"""
    if request.method == 'POST':
        # Get selected entities from form
        entity_access = {}
        for entity_name in request.form.getlist('entities'):
            access_level = request.form.get(f'access_{entity_name}', 'read')
            entity_access[entity_name] = access_level

        auth_service.update_user_entities(user_id, entity_access)
        flash('Entity access updated', 'success')
        return redirect(url_for('admin_users'))

    user = auth_service.get_user_by_id(user_id)
    current_access = auth_service.get_user_entities(user_id)
    all_entities = get_all_business_entities()

    return render_template('admin/user_entities.html',
                         user=user,
                         current_access=current_access,
                         all_entities=all_entities)
```

---

### Phase 6: Filter Data by User Access (Tasks 14-15)

#### Task 14: Add Entity Filtering to Transaction Queries
**Difficulty:** Medium | **Time:** 1 hour

**Modify:** Database queries in `web_ui/app_db.py`

**Strategy:**
```python
def get_user_entity_filter(user_id):
    """Get SQL WHERE clause for user's entities"""
    if current_user.role == 'admin':
        return ""  # Admins see everything

    user_entities = auth_service.get_user_entities(user_id)
    if not user_entities:
        return "AND 1=0"  # No access = no data

    entity_list = ','.join([f"'{e}'" for e in user_entities])
    return f"AND entity IN ({entity_list})"

# Update API endpoint
@app.route('/api/transactions')
@login_required
def api_transactions():
    """API endpoint to get filtered transactions with pagination"""
    try:
        # ... existing filter code ...

        # ADD USER ENTITY FILTERING
        entity_filter = get_user_entity_filter(current_user.id)

        # Build query
        query = f"""
            SELECT * FROM transactions
            WHERE 1=1
            {entity_filter}  -- ← ADD THIS
            {date_filter}
            {entity_param_filter}
            {category_filter}
            {search_filter}
            {archive_filter}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """

        # ... rest of code ...
```

**Files to modify:**
- All transaction query functions
- Dashboard statistics queries
- Invoice queries
- Receipt queries

#### Task 15: Add User Context to Navigation
**Difficulty:** Easy | **Time:** 30 minutes

**Modify:** All template files to show user info in header

**Template changes:**
```html
<!-- Add to all templates in header -->
<div class="user-menu">
    <span class="user-name">{{ current_user.full_name or current_user.username }}</span>
    <span class="user-role">({{ current_user.role }})</span>
    <a href="{{ url_for('profile') }}">Profile</a>
    {% if current_user.is_admin() %}
        <a href="{{ url_for('admin_users') }}">Users</a>
    {% endif %}
    <a href="{{ url_for('logout') }}">Logout</a>
</div>
```

**CSS styling:**
```css
.user-menu {
    position: absolute;
    top: 10px;
    right: 20px;
    display: flex;
    gap: 15px;
    align-items: center;
}

.user-name {
    font-weight: bold;
}

.user-role {
    color: #666;
    font-size: 0.9em;
}
```

---

### Phase 7: Testing & Security (Tasks 16-18)

#### Task 16: Create Initial Admin User Script
**Difficulty:** Easy | **Time:** 30 minutes

**File:** `create_admin_user.py`

```python
#!/usr/bin/env python3
"""
Create initial admin user for DeltaCFOAgent
Run this script once after setting up authentication
"""

import os
import sys
from getpass import getpass

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import DatabaseManager
from services.auth_service import AuthService

def create_admin():
    print("=" * 60)
    print("DeltaCFOAgent - Create Admin User")
    print("=" * 60)

    username = input("Username: ")
    email = input("Email: ")
    full_name = input("Full Name: ")
    password = getpass("Password: ")
    confirm_password = getpass("Confirm Password: ")

    if password != confirm_password:
        print("❌ Passwords do not match")
        sys.exit(1)

    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)

    try:
        db_manager = DatabaseManager()
        auth_service = AuthService(db_manager)

        user = auth_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role='admin'
        )

        print(f"\n✅ Admin user '{username}' created successfully!")
        print(f"   Email: {email}")
        print(f"   Role: admin")
        print(f"\nYou can now log in at: http://localhost:5001/login")

    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_admin()
```

**Usage:**
```bash
python create_admin_user.py
```

#### Task 17: Write Authentication Tests
**Difficulty:** Medium | **Time:** 1.5 hours

**File:** `web_ui/test_auth.py`

**Test Cases:**
1. User creation with password hashing
2. User authentication (valid/invalid credentials)
3. Password change functionality
4. Entity access checking
5. Role-based access control
6. Login/logout flow
7. Session management
8. Protected route access

```python
import unittest
from services.auth_service import AuthService
from database import DatabaseManager

class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.db_manager = DatabaseManager()
        self.auth_service = AuthService(self.db_manager)

    def test_create_user(self):
        """Test user creation with password hashing"""
        user = self.auth_service.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="Test User",
            role="viewer"
        )
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'testuser')
        # Password should be hashed
        self.assertNotEqual(user['password_hash'], 'password123')

    def test_authenticate_valid_user(self):
        """Test authentication with valid credentials"""
        # Create user first
        self.auth_service.create_user(
            username="authuser",
            email="auth@example.com",
            password="password123"
        )

        # Authenticate
        user = self.auth_service.authenticate_user("authuser", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'authuser')

    def test_authenticate_invalid_password(self):
        """Test authentication with invalid password"""
        user = self.auth_service.authenticate_user("authuser", "wrongpassword")
        self.assertIsNone(user)

    # ... more tests ...
```

#### Task 18: Security Review & Hardening
**Difficulty:** Medium | **Time:** 1 hour

**Security Checklist:**

1. **Password Security**
   - ✅ Use Werkzeug password hashing
   - ✅ Minimum password length (8 characters)
   - ⚠️ Add password complexity requirements
   - ⚠️ Implement rate limiting on login attempts
   - ⚠️ Lock account after 5 failed attempts

2. **Session Security**
   - ✅ Secure cookie settings
   - ✅ Session timeout (24 hours)
   - ⚠️ CSRF protection on forms
   - ⚠️ Regenerate session ID after login

3. **SQL Injection Prevention**
   - ✅ Already using parameterized queries
   - ✅ Continue using throughout

4. **XSS Prevention**
   - ✅ Flask auto-escapes templates
   - ⚠️ Review any `|safe` filters

5. **Access Control**
   - ✅ Role-based decorators
   - ✅ Entity-based filtering
   - ⚠️ Log all access attempts
   - ⚠️ Audit trail for sensitive actions

**File:** `web_ui/app_db.py` (security improvements)

```python
# Add CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Secure session cookies
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)

# Rate limiting on login
from flask_limiter import Limiter
limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute
def login():
    # ... existing code ...
```

---

### Phase 8: Documentation & Deployment (Tasks 19-20)

#### Task 19: Update Documentation
**Difficulty:** Easy | **Time:** 45 minutes

**Files to create/update:**

1. **AUTH_IMPLEMENTATION.md** - Complete authentication documentation
2. **USER_GUIDE.md** - How to use login/user management
3. **ADMIN_GUIDE.md** - How to manage users and permissions
4. **SECURITY.md** - Security best practices and considerations
5. **CLAUDE.md** - Update with authentication info

**Content includes:**
- Authentication architecture overview
- User roles and permissions matrix
- How to create users
- How to assign entity access
- Password policies
- Session management details
- Security best practices
- Troubleshooting guide

#### Task 20: Update Deployment Guide
**Difficulty:** Easy | **Time:** 30 minutes

**File:** `DEPLOYMENT_GUIDE.md` (update)

**Add sections:**
1. **Initial Setup:**
   - Run database migrations
   - Create admin user
   - Set FLASK_SECRET_KEY environment variable

2. **Environment Variables:**
   ```bash
   FLASK_SECRET_KEY=your-secret-key-here  # Required for sessions
   SESSION_TIMEOUT_HOURS=24               # Optional (default: 24)
   PASSWORD_MIN_LENGTH=8                  # Optional (default: 8)
   ```

3. **First-Time Setup:**
   ```bash
   # Apply authentication migrations
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/001_add_users_table.sql
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/002_add_user_tracking.sql

   # Create initial admin user
   python create_admin_user.py

   # Start application
   cd web_ui && python app_db.py
   ```

4. **Production Checklist:**
   - [ ] Set strong SECRET_KEY (not default)
   - [ ] Enable HTTPS only
   - [ ] Configure session timeout
   - [ ] Enable CSRF protection
   - [ ] Set up rate limiting
   - [ ] Review password policies
   - [ ] Test all roles and permissions

---

## Summary

### Tasks Breakdown

**Phase 1: Database Schema (3 tasks)**
1. Create users table
2. Create user-entity associations table
3. Update existing tables with user tracking

**Phase 2: Authentication Service (3 tasks)**
4. Create user authentication service
5. Create user model class
6. Set up Flask-Login

**Phase 3: Login/Logout UI (3 tasks)**
7. Create login page
8. Create login/logout routes
9. Add user profile page

**Phase 4: Protect Routes (2 tasks)**
10. Add @login_required to all routes
11. Create role-based decorators

**Phase 5: User Management (2 tasks)**
12. Create user management page (admin)
13. Create entity assignment interface

**Phase 6: Data Filtering (2 tasks)**
14. Add entity filtering to queries
15. Add user context to navigation

**Phase 7: Testing & Security (3 tasks)**
16. Create initial admin user script
17. Write authentication tests
18. Security review & hardening

**Phase 8: Documentation (2 tasks)**
19. Update documentation
20. Update deployment guide

**Total: 20 tasks**

### Time Estimate

- **Phase 1:** 1.5 hours
- **Phase 2:** 2.5 hours
- **Phase 3:** 2.5 hours
- **Phase 4:** 2 hours
- **Phase 5:** 2.5 hours
- **Phase 6:** 1.5 hours
- **Phase 7:** 3 hours
- **Phase 8:** 1.5 hours

**Total Estimated Time: ~17 hours**

### Dependencies to Add

```txt
# Add to requirements.txt
flask-login>=0.6.3        # User session management
flask-wtf>=1.2.1          # CSRF protection
flask-limiter>=3.5.0      # Rate limiting
email-validator>=2.1.0    # Email validation
```

### New Files

1. `migrations/001_add_users_table.sql`
2. `migrations/002_add_user_tracking.sql`
3. `web_ui/services/auth_service.py`
4. `web_ui/models/user.py`
5. `web_ui/auth_decorators.py`
6. `web_ui/templates/login.html`
7. `web_ui/templates/profile.html`
8. `web_ui/templates/admin/users.html`
9. `web_ui/templates/admin/user_entities.html`
10. `web_ui/test_auth.py`
11. `create_admin_user.py`
12. `AUTH_IMPLEMENTATION.md`
13. `USER_GUIDE.md`
14. `ADMIN_GUIDE.md`
15. `SECURITY.md`

### Modified Files

1. `web_ui/app_db.py` (major changes - add routes, decorators)
2. `postgres_unified_schema.sql` (add users tables)
3. `requirements.txt` (add auth dependencies)
4. `CLAUDE.md` (update with auth info)
5. `DEPLOYMENT_GUIDE.md` (add auth setup)
6. All template files (add user menu in header)

---

## Next Steps

**Awaiting your approval to proceed with:**

1. ✅ Approve this plan as-is
2. 📝 Request modifications/changes
3. ❓ Ask questions about specific tasks
4. 🚀 Begin implementation

**Questions to consider:**

1. Do you want password reset via email? (adds complexity)
2. Do you want 2FA/MFA? (adds significant complexity)
3. Should we support OAuth (Google/Microsoft login)? (adds complexity)
4. What should be the default session timeout? (24 hours recommended)
5. Do you want audit logging of all user actions? (recommended)

Please review and let me know if you'd like me to proceed or make any changes to this plan!
