"""
WaddleBot Router Module - py4web implementation
Handles command routing, processing, and execution coordination
"""

import os
from py4web import action, Field, DAL, HTTP, request, response
from py4web.core import Fixture

# Configure authentication
from py4web.utils.auth import Auth
from py4web.utils.mailer import Mailer
from py4web.utils.form import FormStyleBulma

from .models import db

# Configure mailer (for password resets, etc.)
mailer = Mailer(
    server=os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
    sender=os.environ.get('SMTP_SENDER', 'noreply@waddlebot.com'),
    username=os.environ.get('SMTP_USERNAME'),
    password=os.environ.get('SMTP_PASSWORD'),
    tls=True,
    ssl=True
)

# Configure authentication
auth = Auth(
    db,
    mailer=mailer,
    registration_requires_confirmation=False,
    registration_requires_approval=True,
    login_after_registration=False
)

# Set form style
auth.param.formstyle = FormStyleBulma

# Define auth tables
auth.define_tables()

# Configure admin user creation
def create_admin_user():
    """Create default admin user if none exists"""
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@waddlebot.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'changeme123')
    
    # Check if admin user exists
    admin_user = db(db.auth_user.email == admin_email).select().first()
    
    if not admin_user:
        # Create admin user
        user_id = auth.register(
            email=admin_email,
            password=admin_password,
            first_name='Admin',
            last_name='User'
        )
        
        if user_id:
            # Approve the user
            db(db.auth_user.id == user_id).update(
                registration_key='',
                registration_id=''
            )
            db.commit()
            print(f"Created admin user: {admin_email}")

# Create admin user on startup
try:
    create_admin_user()
except Exception as e:
    print(f"Error creating admin user: {e}")

from .controllers import router, api, health

__version__ = "1.0.0"
__all__ = ["router", "api", "health", "db", "auth", "mailer"]