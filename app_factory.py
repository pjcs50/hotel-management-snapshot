"""
Flask application factory for the Hotel Management System.

This module initializes the Flask application and registers all
required extensions and blueprints.
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks.auto_checkout import auto_check_out_overdue

from config import get_config
from db import init_db, db

# Initialize extensions
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()
csrf = CSRFProtect()
scheduler = BackgroundScheduler()


def create_app(config_class=None):
    """Create and configure the Flask application."""
    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        app.config.from_object(get_config())
    elif isinstance(config_class, dict):
        app.config.from_mapping(config_class) # Use from_mapping for dicts
    else:
        app.config.from_object(config_class) # Assume it's an object (e.g., class)

    # Initialize extensions
    init_db(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    if app.testing:
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.jinja_env.auto_reload = True

    # Setup login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Make datetime available in all templates
    app.jinja_env.globals['datetime'] = datetime

    # Add hasattr to Jinja2 globals
    app.jinja_env.globals['hasattr'] = hasattr

    # Add app.config to Jinja2 globals
    app.jinja_env.globals['config'] = app.config

    # Define and register nl2br filter
    def nl2br(value):
        import re
        from markupsafe import Markup
        return Markup(re.sub(r'\r\n|\r|\n', '<br>\n', str(value)))

    app.jinja_env.filters['nl2br'] = nl2br

    # Register user loader
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Configure logging
    if not app.testing:
        # CHANGE: Only setup logging if LOG_FILE is set
        if app.config.get("LOG_FILE"):
            setup_logging(app)
        else:
            # Setup basic console logging
            app.logger.setLevel(getattr(logging, app.config.get("LOG_LEVEL", "INFO")))
            app.logger.info("Hotel Management System startup with console logging")

    # Register blueprints
    register_blueprints(app)

    # Ensure test accounts exist (after database initialization)
    with app.app_context():
        try:
            # Import here to avoid circular imports
            from app.utils.test_accounts import ensure_test_accounts_exist, log_test_credentials
            
            # Ensure test accounts are available
            if ensure_test_accounts_exist():
                if not app.testing:  # Only log in non-testing mode
                    log_test_credentials()
            else:
                app.logger.warning("Failed to ensure test accounts exist")
                
        except Exception as e:
            app.logger.error(f"Error setting up test accounts: {e}")

    # Add a simple index route to resolve url_for('index')
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            # Attempt to redirect to a role-specific dashboard
            # Fallback to a generic one if role or dashboard is not standard
            role_dashboard_map = {
                "customer": "customer.dashboard",
                "receptionist": "receptionist.dashboard",
                "manager": "manager.dashboard",
                "housekeeping": "housekeeping.dashboard",
                "admin": "admin.dashboard",
            }
            # Check if current_user has a role and if that role is in our map
            if hasattr(current_user, 'role') and current_user.role in role_dashboard_map:
                try:
                    return redirect(url_for(role_dashboard_map[current_user.role]))
                except Exception: # Catch potential BuildError if a dashboard doesn't exist
                    # Fallback for roles that might not have a 'dashboard' or if current_user.role is None/empty
                    pass # Let it fall through to a more generic redirect or login

            # Generic fallback if specific role dashboard isn't found or user has no clear role dashboard
            # This could be auth.login or another safe page. For now, let's try customer.dashboard or login.
            try:
                return redirect(url_for('customer.dashboard')) # Example fallback
            except Exception:
                return redirect(url_for('auth.login')) # Safest fallback

        return redirect(url_for('auth.login'))

    # Start scheduler for background tasks
    if not app.testing and not scheduler.running:
        scheduler.start()
        scheduler.add_job(auto_check_out_overdue, 'cron', hour=0, minute=0)

    # Shell context for flask cli
    @app.shell_context_processor
    def make_shell_context():
        """
        Add database instance and models to flask shell context.

        This allows direct access to db and models in shell with:
        $ flask shell
        """
        # Import models here to avoid circular imports
        from app.models import User, Customer, Room, RoomType, Booking

        # Return dictionary of objects available in shell context
        return {
            "db": db,
            "User": User,
            "Customer": Customer,
            "Room": Room,
            "RoomType": RoomType,
            "Booking": Booking
        }

    # Context processor to make variables available in all templates
    @app.context_processor
    def inject_user_info():
        """Inject user information into all templates."""
        return {
            'current_user': current_user
        }

    return app


def register_blueprints(app):
    """Register Flask blueprints."""
    # Import blueprints here to avoid circular imports
    from app.routes.auth import auth_bp
    from app.routes.room import room_bp
    from app.routes.customer import customer_bp
    from app.routes.receptionist import receptionist_bp
    from app.routes.manager import manager_bp
    from app.routes.housekeeping import housekeeping_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.payment import payment_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(room_bp, url_prefix="/rooms")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(receptionist_bp, url_prefix="/receptionist")
    app.register_blueprint(manager_bp, url_prefix="/manager")
    app.register_blueprint(housekeeping_bp, url_prefix="/housekeeping")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(payment_bp, url_prefix="/payment")


def setup_logging(app):
    """Configure logging for the application."""
    log_level = getattr(logging, app.config["LOG_LEVEL"])
    log_file = app.config["LOG_FILE"]

    # CHANGE: Add check for empty log_file and ensure directory exists
    if not log_file:
        log_file = "app.log"

    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=10  # 10MB  # Keep 10 backup files
    )
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )
    handler.setFormatter(formatter)

    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.info("Hotel Management System startup")
