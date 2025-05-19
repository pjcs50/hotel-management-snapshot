"""
Unit tests for user account related forms.
"""
import pytest
from flask_wtf import FlaskForm # For context if running outside Flask app context
from werkzeug.datastructures import MultiDict

from app.forms.user_forms import ChangePasswordForm

# Helper to create a form with context if needed for some validators
# For basic WTForms, often not needed just for instantiation and validate()
class BasicForm(FlaskForm):
    pass

@pytest.fixture
def form_data():
    return {
        'current_password': 'old_password123',
        'new_password': 'new_Password123!',
        'confirm_new_password': 'new_Password123!',
        'csrf_token': 'test-csrf-token' # Assuming CSRF is handled/mocked
    }

def test_change_password_form_valid(form_data, app):
    """Test ChangePasswordForm with valid data."""
    with app.app_context():
        form = ChangePasswordForm(MultiDict(form_data)) # WTForms expects MultiDict for form data
        assert form.validate(), f"Form errors: {form.errors}"

def test_change_password_form_missing_current_password(form_data, app):
    """Test ChangePasswordForm with missing current password."""
    form_data.pop('current_password')
    with app.app_context():
        form = ChangePasswordForm(MultiDict(form_data))
        assert not form.validate()
        assert 'current_password' in form.errors
        assert "Current password is required." in form.errors['current_password'][0]

def test_change_password_form_missing_new_password(form_data, app):
    """Test ChangePasswordForm with missing new password."""
    form_data.pop('new_password')
    with app.app_context():
        form = ChangePasswordForm(MultiDict(form_data))
        assert not form.validate()
        assert 'new_password' in form.errors
        assert "New password is required." in form.errors['new_password'][0]

def test_change_password_form_missing_confirm_new_password(form_data, app):
    """Test ChangePasswordForm with missing confirm new password."""
    form_data.pop('confirm_new_password')
    with app.app_context():
        form = ChangePasswordForm(MultiDict(form_data))
        assert not form.validate()
        assert 'confirm_new_password' in form.errors
        assert "Please confirm your new password." in form.errors['confirm_new_password'][0]

def test_change_password_form_new_password_too_short(form_data, app):
    """Test ChangePasswordForm with a new password that is too short."""
    form_data['new_password'] = 'short'
    form_data['confirm_new_password'] = 'short'
    with app.app_context():
        form = ChangePasswordForm(MultiDict(form_data))
        assert not form.validate()
        assert 'new_password' in form.errors
        assert "New password must be at least 8 characters long." in form.errors['new_password'][0]

def test_change_password_form_passwords_mismatch(form_data, app):
    """Test ChangePasswordForm with new password and confirmation not matching."""
    form_data['confirm_new_password'] = 'different_Password123!'
    with app.app_context():
        form = ChangePasswordForm(MultiDict(form_data))
        assert not form.validate()
        assert 'confirm_new_password' in form.errors
        assert "New passwords must match." in form.errors['confirm_new_password'][0]

# To run these tests, you might need a minimal Flask app context for CSRF, or disable CSRF for tests.
# For simplicity, I'm assuming CSRF is handled or we're testing form logic directly.
# If using Flask-Testing, form instantiation might be `self.form = ChangePasswordForm(formdata=form_data)`
# within a test class method, which handles context. 