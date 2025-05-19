"""
Manager routes module.

This module defines the routes for manager operations.
"""

from flask import Blueprint, jsonify, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
import io
from sqlalchemy import func, select
from werkzeug.exceptions import Conflict

from app.utils.decorators import role_required
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService
from app.services.staff_performance_service import StaffPerformanceService
from app.services.seasonal_rate_service import SeasonalRateService
from app.services.waitlist_service import WaitlistService
from app.services.analytics_service import AnalyticsService
from app.services.maintenance_service import MaintenanceService
from app.services.housekeeping_service import HousekeepingService
from app.models.user import User
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.pricing import Pricing
from app.forms.seasonal_rate_form import SeasonalRateForm
from db import db

# Create blueprint
manager_bp = Blueprint('manager', __name__)


@manager_bp.route('/dashboard')
@login_required
@role_required('manager')
def dashboard():
    """Display manager dashboard."""
    from flask import g
    
    # Check if metrics are already cached for this request
    if hasattr(g, 'dashboard_metrics'):
        return render_template('manager/dashboard.html', metrics=g.dashboard_metrics)
    
    dashboard_service = DashboardService(db.session)
    analytics_service = AnalyticsService(db.session)
    
    try:
        # Get manager metrics
        metrics = dashboard_service.get_manager_metrics()
        
        # Enrich with additional analytics data
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Add revenue by room type from analytics service
        revenue_data = analytics_service.get_revenue_by_room_type(current_year, current_month)
        metrics['room_type_revenue'] = {label: value for label, value in zip(revenue_data['labels'], revenue_data['datasets'][0]['data'])}
        
        # Cache the metrics
        g.dashboard_metrics = metrics
        
        return render_template('manager/dashboard.html', metrics=metrics)
    except Exception as e:
        error_metrics = {
            "error": f"Error loading dashboard data: {str(e)}"
        }
        return render_template('manager/dashboard.html', metrics=error_metrics)


@manager_bp.route('/reports')
@login_required
@role_required('manager')
def reports():
    """Generate reports page."""
    report_service = ReportService(db.session)
    today = datetime.now()
    start_date = request.args.get('start_date', (today.replace(day=1)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    report_type = request.args.get('report_type', 'occupancy')
    try:
        if report_type == 'occupancy':
            report_data = report_service.get_occupancy_report(start_date, end_date)
            title = "Occupancy Report"
        elif report_type == 'revenue':
            report_data = report_service.get_revenue_report(start_date, end_date)
            title = "Revenue Report"
        elif report_type == 'staff':
            report_data = report_service.get_staff_activity_report(start_date, end_date)
            title = "Staff Activity Report"
        else:
            report_data = report_service.get_occupancy_report(start_date, end_date)
            title = "Occupancy Report"
        return render_template(
            'manager/reports.html',
            report_data=report_data,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            title=title
        )
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        return render_template(
            'manager/reports.html',
            report_data=None,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            title="Report Error"
        )


@manager_bp.route('/reports/export')
@login_required
@role_required('manager')
def export_report():
    """Export report as CSV, Excel or PDF."""
    report_service = ReportService(db.session)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('report_type', 'occupancy')
    export_format = request.args.get('format', 'csv')
    
    try:
        if report_type == 'occupancy':
            report_data = report_service.get_occupancy_report(start_date, end_date)
            filename = f"occupancy_report_{start_date}_to_{end_date}"
            title = "Occupancy Report"
        elif report_type == 'revenue':
            report_data = report_service.get_revenue_report(start_date, end_date)
            filename = f"revenue_report_{start_date}_to_{end_date}"
            title = "Revenue Report"
        elif report_type == 'staff':
            report_data = report_service.get_staff_activity_report(start_date, end_date)
            filename = f"staff_report_{start_date}_to_{end_date}"
            title = "Staff Activity Report"
        else:
            report_data = report_service.get_occupancy_report(start_date, end_date)
            filename = f"occupancy_report_{start_date}_to_{end_date}"
            title = "Occupancy Report"
        
        if export_format == 'csv':
            output = report_service.export_to_csv(report_data, title)
            mimetype = 'text/csv'
            extension = 'csv'
        elif export_format == 'excel':
            output = report_service.export_to_excel(report_data, title)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extension = 'xlsx'
        elif export_format == 'pdf':
            try:
                output = report_service.export_to_pdf(report_data, title)
                mimetype = 'application/pdf'
                extension = 'pdf'
            except ImportError:
                flash("PDF export requires additional dependencies. Falling back to CSV format.", "warning")
                output = report_service.export_to_csv(report_data, title)
                mimetype = 'text/csv'
                extension = 'csv'
        else:
            output = report_service.export_to_csv(report_data, title)
            mimetype = 'text/csv'
            extension = 'csv'
        
        return send_file(
            io.BytesIO(output),
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"{filename}.{extension}"
        )
    except Exception as e:
        flash(f"Error exporting report: {str(e)}", "danger")
        return redirect(url_for('manager.reports', 
                                report_type=report_type, 
                                start_date=start_date, 
                                end_date=end_date))


@manager_bp.route('/staff')
@login_required
@role_required('manager')
def staff():
    """Manage staff members."""
    # Get filter parameters
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '')
    
    # Base query - only get staff roles (not customers)
    query = User.query.filter(
        User.role.in_(['receptionist', 'housekeeping', 'manager'])
    )
    
    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if status_filter:
        is_active = (status_filter == 'active')
        query = query.filter(User.is_active == is_active)
    
    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) | 
            (User.email.ilike(f'%{search_query}%'))
        )
    
    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.order_by(User.username).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all available roles for the filter dropdown
    staff_roles = ['receptionist', 'housekeeping', 'manager']
    
    # Count staff by role for pie chart
    role_counts = db.session.query(User.role, func.count(User.id))\
        .filter(User.role.in_(staff_roles))\
        .group_by(User.role).all()
    
    staff_role_data = {role: count for role, count in role_counts}
    
    # Mock performance data - in a real app, this would come from the database
    performance_data = []
    for user in pagination.items[:5]:  # Just show for first 5 users in the list
        performance_data.append({
            'username': user.username,
            'role': user.role,
            'tasks_completed': 0,  # Placeholder
            'rating': 0  # Placeholder
        })
    
    # Mock activity logs - in a real app, this would come from the database
    activity_logs = []
    
    return render_template(
        'manager/staff.html',
        staff_members=pagination.items,
        pagination=pagination,
        roles=staff_roles,
        staff_roles=staff_role_data,
        performance_data=performance_data,
        activity_logs=activity_logs,
        current_filters={
            'role': role_filter,
            'status': status_filter,
            'search': search_query
        }
    )


@manager_bp.route('/staff-requests')
@login_required
@role_required('manager')
def staff_requests():
    """View and manage staff registration requests."""
    from app.models.user import User
    from app.models.staff_request import StaffRequest
    
    # Get all pending staff requests
    pending_requests = db.session.query(StaffRequest, User)\
        .join(User, StaffRequest.user_id == User.id)\
        .filter(StaffRequest.status == 'pending')\
        .order_by(StaffRequest.created_at.desc()).all()
    
    # Get users with pending role requests (in case they don't have a staff_request record)
    pending_role_users = User.query.filter(User.role_requested.isnot(None)).all()
    
    # Combine users with pending roles but no staff request
    combined_requests = list(pending_requests)
    for user in pending_role_users:
        # Check if this user already has a staff request
        if not any(request.user_id == user.id for request, _ in pending_requests):
            # Create a virtual request object since there's no actual StaffRequest record
            class VirtualRequest:
                def __init__(self, user):
                    self.id = None  # No database ID
                    self.user_id = user.id
                    self.role_requested = user.role_requested
                    self.status = 'pending'
                    self.created_at = user.updated_at  # Use user's update time as request time
                    self.notes = ''
            
            # Add to the list as a tuple (request, user) to match the format from the DB query
            combined_requests.append((VirtualRequest(user), user))
    
    return render_template(
        'manager/staff_requests.html',
        pending_requests=combined_requests
    )


@manager_bp.route('/staff-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@role_required('manager')
def approve_staff_request(request_id):
    """Approve a staff registration request."""
    from app.models.staff_request import StaffRequest
    from app.services.user_service import UserService
    
    try:
        # Use the improved service method for handling approval
        user_service = UserService(db.session)
        staff_request = user_service.approve_staff_request(
            request_id=request_id,
            admin_user_id=current_user.id,
            notes="Approved by manager"
        )
        
        # Get user for the flash message
        user = User.query.get(staff_request.user_id)
        flash(f'Staff request for {user.username} has been approved successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving staff request: {str(e)}', 'danger')
    
    return redirect(url_for('manager.staff_requests'))


@manager_bp.route('/staff-requests/<int:request_id>/deny', methods=['POST'])
@login_required
@role_required('manager')
def deny_staff_request(request_id):
    """Deny a staff registration request."""
    from app.models.staff_request import StaffRequest
    from app.services.user_service import UserService
    
    try:
        # Use the improved service method for handling denial
        user_service = UserService(db.session)
        staff_request = user_service.deny_staff_request(
            request_id=request_id,
            admin_user_id=current_user.id,
            notes="Denied by manager"
        )
        
        # Get user for the flash message
        user = User.query.get(staff_request.user_id)
        flash(f'Staff request for {user.username} has been denied.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error denying staff request: {str(e)}', 'danger')
    
    return redirect(url_for('manager.staff_requests'))


@manager_bp.route('/pricing', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def pricing():
    """Manage room type pricing."""
    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('base_rate_'):
                try:
                    room_type_id = int(key.split('_')[-1])
                    new_base_rate = float(value)
                    
                    room_type = db.session.get(RoomType, room_type_id)
                    if not room_type:
                        flash(f"RoomType with ID {room_type_id} not found.", "danger")
                        continue

                    room_type.base_rate = new_base_rate
                    
                    # Now update the corresponding Pricing object
                    pricing_obj = db.session.execute(
                        select(Pricing).filter_by(room_type_id=room_type.id)
                    ).scalar_one_or_none()

                    if not pricing_obj:
                        # Create one if it doesn't exist, though it should
                        pricing_obj = Pricing(room_type_id=room_type.id)
                        db.session.add(pricing_obj)
                    
                    # Get the submitted weekend and peak prices for this room_type_id
                    weekend_price_key = f'weekend_price_{room_type_id}'
                    peak_price_key = f'peak_price_{room_type_id}'

                    if weekend_price_key in request.form:
                        try:
                            weekend_price = float(request.form[weekend_price_key])
                            if new_base_rate > 0: # Avoid division by zero
                                pricing_obj.weekend_multiplier = round(weekend_price / new_base_rate, 2)
                            else:
                                pricing_obj.weekend_multiplier = 1.0 # Default or error
                        except ValueError:
                            flash(f"Invalid weekend price for RoomType {room_type_id}.", "warning")
                    
                    if peak_price_key in request.form:
                        try:
                            peak_price = float(request.form[peak_price_key])
                            if new_base_rate > 0: # Avoid division by zero
                                pricing_obj.peak_season_multiplier = round(peak_price / new_base_rate, 2)
                            else:
                                pricing_obj.peak_season_multiplier = 1.0 # Default or error
                        except ValueError:
                            flash(f"Invalid peak price for RoomType {room_type_id}.", "warning")

                except ValueError:
                    flash(f"Invalid value submitted for {key}.", "danger")
                except Exception as e:
                    flash(f"Error updating pricing for {key}: {str(e)}", "danger")
        
        try:
            db.session.commit()
            flash('Room prices updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving pricing updates: {str(e)}', 'danger')
            
        return redirect(url_for('manager.pricing'))

    # GET request
    room_types_with_pricing = db.session.execute(
        select(RoomType, Pricing)
        .outerjoin(Pricing, RoomType.id == Pricing.room_type_id)
        .order_by(RoomType.name)
    ).all()
    
    # The result of .all() when selecting multiple models is a list of Row objects
    # Each Row object can be accessed by index or by model class/name
    # We need to prepare a list of dictionaries or custom objects for the template
    
    display_data = []
    for row in room_types_with_pricing:
        room_type = row[0] # Access RoomType from the Row
        pricing_info = row[1] # Access Pricing from the Row (can be None)
        
        current_weekend_price = room_type.base_rate * (pricing_info.weekend_multiplier if pricing_info else 1.0)
        current_peak_price = room_type.base_rate * (pricing_info.peak_season_multiplier if pricing_info else 1.0)
        
        display_data.append({
            'id': room_type.id,
            'name': room_type.name,
            'base_rate': room_type.base_rate,
            'weekend_multiplier': pricing_info.weekend_multiplier if pricing_info else 1.0,
            'peak_season_multiplier': pricing_info.peak_season_multiplier if pricing_info else 1.0,
            'current_weekend_price': current_weekend_price,
            'current_peak_price': current_peak_price,
            'has_pricing_rules': pricing_info is not None
        })
        
    return render_template('manager/pricing.html', room_types_data=display_data)


@manager_bp.route('/staff/<int:staff_id>')
@login_required
@role_required('manager')
def view_staff(staff_id):
    """View staff member details."""
    # Get the staff member
    staff = User.query.get_or_404(staff_id)
    
    # Only allow viewing staff roles
    if staff.role not in ['receptionist', 'housekeeping', 'manager']:
        flash('You can only view staff members.', 'warning')
        return redirect(url_for('manager.staff'))
    
    # Mock activity data - in a real app, this would come from the database
    activity_data = {
        'logins': 0,
        'actions': 0,
        'last_login': 'Never'
    }
    
    # Mock performance metrics - in a real app, this would come from the database
    performance_metrics = {
        'tasks_completed': 0,
        'avg_response_time': 0,
        'rating': 0
    }
    
    return render_template(
        'manager/staff_details.html',
        staff=staff,
        activity_data=activity_data,
        performance_metrics=performance_metrics
    )


@manager_bp.route('/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit_staff(staff_id):
    """Edit staff member details."""
    # Get the staff member
    staff = User.query.get_or_404(staff_id)
    
    # Only allow editing staff roles
    if staff.role not in ['receptionist', 'housekeeping', 'manager']:
        flash('You can only edit staff members.', 'warning')
        return redirect(url_for('manager.staff'))
    
    # Protect against editing other managers (only admins should be able to edit managers)
    if staff.role == 'manager' and staff.id != current_user.id:
        flash('You cannot edit other managers.', 'warning')
        return redirect(url_for('manager.staff'))
        
    # Create form for editing
    from wtforms import Form, StringField, SelectField, BooleanField, validators
    
    class StaffForm(Form):
        username = StringField('Username', [validators.Length(min=3, max=25)])
        email = StringField('Email', [validators.Email()])
        role = SelectField('Role', choices=[
            ('receptionist', 'Receptionist'),
            ('housekeeping', 'Housekeeping')
        ])
        is_active = BooleanField('Active')
        
    # Current manager can edit their own role, but not others
    if staff.id == current_user.id:
        StaffForm.role.choices.append(('manager', 'Manager'))
    
    # Process form submission
    if request.method == 'POST':
        form = StaffForm(request.form)
        
        if form.validate():
            # Update staff member
            staff.username = form.username.data
            staff.email = form.email.data
            staff.is_active = form.is_active.data
            
            # Only update role if it's valid for this manager to change
            if form.role.data != 'manager' or staff.id == current_user.id:
                staff.role = form.role.data
            
            try:
                db.session.commit()
                flash('Staff member updated successfully.', 'success')
                return redirect(url_for('manager.view_staff', staff_id=staff.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating staff member: {str(e)}', 'danger')
    else:
        # Initialize form with staff data
        form = StaffForm(obj=staff)
    
    return render_template(
        'manager/edit_staff.html',
        form=form,
        staff=staff
    )


@manager_bp.route('/virtual-staff-requests/<int:user_id>/approve', methods=['POST'])
@login_required
@role_required('manager')
def approve_virtual_staff_request(user_id):
    """Approve a virtual staff request (where no StaffRequest record exists)."""
    from app.models.staff_request import StaffRequest
    from app.services.user_service import UserService
    
    # Find the user
    user = User.query.get_or_404(user_id)
    
    try:
        # Create a proper staff request record with transaction handling
        staff_request = StaffRequest(
            user_id=user.id,
            role_requested=user.role_requested,
            status='pending',
            created_at=datetime.now(timezone.utc),
            notes='Auto-created from virtual request'
        )
        db.session.add(staff_request)
        db.session.commit()
        
        # Now approve through the service
        user_service = UserService(db.session)
        user_service.approve_staff_request(
            request_id=staff_request.id,
            admin_user_id=current_user.id,
            notes="Virtual request approved by manager"
        )
        
        flash(f'Virtual staff request for {user.username} has been approved successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving virtual staff request: {str(e)}', 'danger')
    
    return redirect(url_for('manager.staff_requests'))


@manager_bp.route('/virtual-staff-requests/<int:user_id>/deny', methods=['POST'])
@login_required
@role_required('manager')
def deny_virtual_staff_request(user_id):
    """Deny a virtual staff request (where no StaffRequest record exists)."""
    from app.models.staff_request import StaffRequest
    from app.services.user_service import UserService
    
    # Find the user
    user = User.query.get_or_404(user_id)
    
    try:
        # Create a proper staff request record with transaction handling
        staff_request = StaffRequest(
            user_id=user.id,
            role_requested=user.role_requested,
            status='pending',
            created_at=datetime.now(timezone.utc),
            notes='Auto-created from virtual request'
        )
        db.session.add(staff_request)
        db.session.commit()
        
        # Now deny through the service
        user_service = UserService(db.session)
        user_service.deny_staff_request(
            request_id=staff_request.id,
            admin_user_id=current_user.id,
            notes="Virtual request denied by manager"
        )
        
        flash(f'Virtual staff request for {user.username} has been denied.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error denying virtual staff request: {str(e)}', 'danger')
    
    return redirect(url_for('manager.staff_requests'))


@manager_bp.route('/rates')
@login_required
@role_required('manager')
def rates():
    """Display list of seasonal rates."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    seasonal_rate_service = SeasonalRateService(db.session)
    rates_pagination = seasonal_rate_service.get_all_seasonal_rates(page, per_page)
    
    return render_template(
        'manager/rates/index.html', 
        rates=rates_pagination.items,
        pagination=rates_pagination
    )


@manager_bp.route('/rates/new', methods=['GET'])
@login_required
@role_required('manager')
def new_rate():
    """Display form to create a new seasonal rate."""
    form = SeasonalRateForm()
    
    # Populate room type choices
    room_types = RoomType.query.all()
    form.room_type_id.choices = [(rt.id, rt.name) for rt in room_types]
    
    return render_template('manager/rates/form.html', form=form, is_new=True)


@manager_bp.route('/rates', methods=['POST'])
@login_required
@role_required('manager')
def create_rate():
    """Create a new seasonal rate."""
    form = SeasonalRateForm()
    
    # Populate room type choices for validation
    room_types = RoomType.query.all()
    form.room_type_id.choices = [(rt.id, rt.name) for rt in room_types]
    
    if form.validate_on_submit():
        seasonal_rate_service = SeasonalRateService(db.session)
        
        data = {
            'name': form.name.data,
            'room_type_id': form.room_type_id.data,
            'start_date': form.start_date.data,
            'end_date': form.end_date.data,
            'rate_multiplier': form.rate_multiplier.data
        }
        
        try:
            seasonal_rate = seasonal_rate_service.create_seasonal_rate(data)
            flash(f'Seasonal rate "{seasonal_rate.name}" created successfully', 'success')
            return redirect(url_for('manager.rates'))
        except Conflict as e:
            flash(str(e), 'danger')
    
    # If validation fails or there's a conflict, return to the form
    return render_template('manager/rates/form.html', form=form, is_new=True)


@manager_bp.route('/rates/<int:rate_id>/edit', methods=['GET'])
@login_required
@role_required('manager')
def edit_rate(rate_id):
    """Display form to edit a seasonal rate."""
    seasonal_rate_service = SeasonalRateService(db.session)
    seasonal_rate = seasonal_rate_service.get_seasonal_rate(rate_id)
    
    if not seasonal_rate:
        flash('Seasonal rate not found', 'danger')
        return redirect(url_for('manager.rates'))
    
    form = SeasonalRateForm(obj=seasonal_rate)
    
    # Populate room type choices
    room_types = RoomType.query.all()
    form.room_type_id.choices = [(rt.id, rt.name) for rt in room_types]
    
    return render_template('manager/rates/form.html', form=form, is_new=False, rate_id=rate_id)


@manager_bp.route('/rates/<int:rate_id>', methods=['POST'])
@login_required
@role_required('manager')
def update_rate(rate_id):
    """Update an existing seasonal rate."""
    seasonal_rate_service = SeasonalRateService(db.session)
    seasonal_rate = seasonal_rate_service.get_seasonal_rate(rate_id)
    
    if not seasonal_rate:
        flash('Seasonal rate not found', 'danger')
        return redirect(url_for('manager.rates'))
    
    form = SeasonalRateForm()
    
    # Populate room type choices for validation
    room_types = RoomType.query.all()
    form.room_type_id.choices = [(rt.id, rt.name) for rt in room_types]
    
    if form.validate_on_submit():
        data = {
            'name': form.name.data,
            'room_type_id': form.room_type_id.data,
            'start_date': form.start_date.data,
            'end_date': form.end_date.data,
            'rate_multiplier': form.rate_multiplier.data
        }
        
        try:
            updated_rate = seasonal_rate_service.update_seasonal_rate(rate_id, data)
            if updated_rate:
                flash(f'Seasonal rate "{updated_rate.name}" updated successfully', 'success')
                return redirect(url_for('manager.rates'))
            else:
                flash('Error updating seasonal rate', 'danger')
        except Conflict as e:
            flash(str(e), 'danger')
    
    # If validation fails or there's a conflict, return to the form
    return render_template('manager/rates/form.html', form=form, is_new=False, rate_id=rate_id)


@manager_bp.route('/rates/<int:rate_id>/delete', methods=['POST'])
@login_required
@role_required('manager')
def delete_rate(rate_id):
    """Delete a seasonal rate."""
    seasonal_rate_service = SeasonalRateService(db.session)
    seasonal_rate = seasonal_rate_service.get_seasonal_rate(rate_id)
    
    if not seasonal_rate:
        flash('Seasonal rate not found', 'danger')
    else:
        seasonal_rate_service.delete_seasonal_rate(rate_id)
        flash(f'Seasonal rate "{seasonal_rate.name}" deleted successfully', 'success')
    
    return redirect(url_for('manager.rates'))


@manager_bp.route('/waitlist')
@login_required
@role_required('manager')
def waitlist():
    """Display list of waitlist entries."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    status = request.args.get('status', None)
    
    waitlist_service = WaitlistService(db.session)
    entries_pagination = waitlist_service.get_all_waitlist_entries(status, page, per_page)
    
    # Get counts by room type for the dashboard widget
    room_type_counts = waitlist_service.get_waitlist_counts_by_room_type()
    
    return render_template(
        'manager/waitlist/index.html', 
        entries=entries_pagination.items,
        pagination=entries_pagination,
        status_filter=status,
        room_type_counts=room_type_counts
    )


@manager_bp.route('/waitlist/<int:entry_id>')
@login_required
@role_required('manager')
def view_waitlist_entry(entry_id):
    """View details of a waitlist entry."""
    waitlist_service = WaitlistService(db.session)
    entry = waitlist_service.get_waitlist_entry(entry_id)
    
    if not entry:
        flash('Waitlist entry not found', 'danger')
        return redirect(url_for('manager.waitlist'))
    
    return render_template('manager/waitlist/view.html', entry=entry)


@manager_bp.route('/waitlist/<int:entry_id>/promote', methods=['POST'])
@login_required
@role_required('manager')
def promote_waitlist_entry(entry_id):
    """Promote a waitlist entry to a booking."""
    waitlist_service = WaitlistService(db.session)
    entry = waitlist_service.get_waitlist_entry(entry_id)
    
    if not entry:
        flash('Waitlist entry not found', 'danger')
        return redirect(url_for('manager.waitlist'))
    
    if entry.status != 'waiting':
        flash(f'Cannot promote entry with status: {entry.status}', 'warning')
        return redirect(url_for('manager.view_waitlist_entry', entry_id=entry_id))
    
    try:
        entry, booking = waitlist_service.promote_waitlist_entry(entry_id)
        
        if entry:
            flash('Customer has been successfully promoted from the waitlist', 'success')
        else:
            flash('Error promoting customer from waitlist', 'danger')
            
    except Exception as e:
        flash(f'Error promoting waitlist entry: {str(e)}', 'danger')
    
    return redirect(url_for('manager.waitlist'))


@manager_bp.route('/waitlist/<int:entry_id>/expire', methods=['POST'])
@login_required
@role_required('manager')
def expire_waitlist_entry(entry_id):
    """Mark a waitlist entry as expired."""
    waitlist_service = WaitlistService(db.session)
    entry = waitlist_service.get_waitlist_entry(entry_id)
    
    if not entry:
        flash('Waitlist entry not found', 'danger')
        return redirect(url_for('manager.waitlist'))
    
    if entry.status != 'waiting':
        flash(f'Cannot expire entry with status: {entry.status}', 'warning')
        return redirect(url_for('manager.view_waitlist_entry', entry_id=entry_id))
    
    reason = request.form.get('reason', 'Manually expired by manager')
    
    try:
        entry = waitlist_service.expire_waitlist_entry(entry_id, reason)
        
        if entry:
            flash('Waitlist entry has been marked as expired', 'success')
        else:
            flash('Error expiring waitlist entry', 'danger')
            
    except Exception as e:
        flash(f'Error expiring waitlist entry: {str(e)}', 'danger')
    
    return redirect(url_for('manager.waitlist'))


@manager_bp.route('/waitlist/process-cancellations', methods=['POST'])
@login_required
@role_required('manager')
def process_waitlist_cancellations():
    """Process all recent cancellations and notify waitlisted customers."""
    # In a real application, this would process actual cancellations
    # For this example, we'll just show a success message
    
    flash('All recent cancellations have been processed and matching waitlist customers have been notified', 'success')
    return redirect(url_for('manager.waitlist'))


# Add analytics routes
@manager_bp.route('/analytics')
@login_required
@role_required('manager')
def analytics():
    """Display analytics dashboard."""
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', None, type=int)
    
    return render_template(
        'manager/analytics/index.html',
        year=year,
        month=month
    )


@manager_bp.route('/analytics/data')
@login_required
@role_required('manager')
def analytics_data():
    """Get analytics data for AJAX requests."""
    analytics_service = AnalyticsService(db.session)
    
    chart_type = request.args.get('chart', None)
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', None, type=int)
    
    if chart_type == 'occupancy':
        data = analytics_service.get_monthly_occupancy(year)
    elif chart_type == 'revenue':
        data = analytics_service.get_revenue_by_room_type(year, month)
    elif chart_type == 'top_customers':
        limit = request.args.get('limit', 5, type=int)
        data = analytics_service.get_top_customers(limit)
    elif chart_type == 'booking_sources':
        data = analytics_service.get_booking_source_distribution()
    elif chart_type == 'forecast':
        days = request.args.get('days', 30, type=int)
        data = analytics_service.get_forecast_data(days)
    else:
        data = {'error': 'Invalid chart type'}
    
    return jsonify(data)


# Add maintenance routes
@manager_bp.route('/maintenance')
@login_required
@role_required('manager')
def maintenance():
    """Display list of maintenance requests."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filter parameters
    filters = {}
    if 'status' in request.args and request.args.get('status'):
        filters['status'] = request.args.get('status')
    if 'priority' in request.args and request.args.get('priority'):
        filters['priority'] = request.args.get('priority')
    if 'issue_type' in request.args and request.args.get('issue_type'):
        filters['issue_type'] = request.args.get('issue_type')
    if 'room_id' in request.args and request.args.get('room_id'):
        filters['room_id'] = int(request.args.get('room_id'))
    if 'q' in request.args and request.args.get('q'):
        filters['q'] = request.args.get('q')
    
    maintenance_service = MaintenanceService(db.session)
    requests_pagination = maintenance_service.get_all_maintenance_requests(filters, page, per_page)
    
    # Get stats for the dashboard
    stats = maintenance_service.get_maintenance_stats()
    
    # Get rooms and staff for forms
    rooms = db.session.query(Room).order_by(Room.number).all()
    maintenance_staff = db.session.query(User).filter(User.role == 'maintenance').all()
    
    return render_template(
        'manager/maintenance/index.html', 
        requests=requests_pagination.items,
        pagination=requests_pagination,
        filters=filters,
        stats=stats,
        rooms=rooms,
        maintenance_staff=maintenance_staff
    )


@manager_bp.route('/maintenance/new', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def new_maintenance_request():
    """Create a new maintenance request."""
    if request.method == 'POST':
        # Extract form data
        data = {
            'room_id': int(request.form.get('room_id')),
            'reported_by': current_user.id,
            'issue_type': request.form.get('issue_type'),
            'description': request.form.get('description'),
            'priority': request.form.get('priority', 'medium'),
            'notes': request.form.get('notes', '')
        }
        
        if request.form.get('assigned_to'):
            data['assigned_to'] = int(request.form.get('assigned_to'))
        
        # Create maintenance request
        maintenance_service = MaintenanceService(db.session)
        request_obj = maintenance_service.create_maintenance_request(data)
        
        if request_obj:
            flash('Maintenance request created successfully', 'success')
            return redirect(url_for('manager.maintenance'))
        else:
            flash('Error creating maintenance request', 'danger')
    
    # GET request - show form
    rooms = db.session.query(Room).order_by(Room.number).all()
    maintenance_staff = db.session.query(User).filter(User.role == 'maintenance').all()
    
    return render_template(
        'manager/maintenance/form.html',
        rooms=rooms,
        maintenance_staff=maintenance_staff,
        is_new=True
    )


@manager_bp.route('/maintenance/<int:request_id>')
@login_required
@role_required('manager')
def view_maintenance_request(request_id):
    """View details of a maintenance request."""
    maintenance_service = MaintenanceService(db.session)
    request_obj = maintenance_service.get_maintenance_request(request_id)
    
    if not request_obj:
        flash('Maintenance request not found', 'danger')
        return redirect(url_for('manager.maintenance'))
    
    maintenance_staff = db.session.query(User).filter(User.role == 'maintenance').all()
    
    return render_template(
        'manager/maintenance/view.html', 
        request=request_obj,
        maintenance_staff=maintenance_staff
    )


@manager_bp.route('/maintenance/<int:request_id>/update', methods=['POST'])
@login_required
@role_required('manager')
def update_maintenance_request(request_id):
    """Update a maintenance request."""
    maintenance_service = MaintenanceService(db.session)
    request_obj = maintenance_service.get_maintenance_request(request_id)
    
    if not request_obj:
        flash('Maintenance request not found', 'danger')
        return redirect(url_for('manager.maintenance'))
    
    # Extract form data
    data = {}
    
    if 'status' in request.form:
        data['status'] = request.form.get('status')
    
    if 'priority' in request.form:
        data['priority'] = request.form.get('priority')
    
    if 'assigned_to' in request.form and request.form.get('assigned_to'):
        data['assigned_to'] = int(request.form.get('assigned_to'))
    
    if 'notes' in request.form:
        data['notes'] = request.form.get('notes')
    
    # Update maintenance request
    updated_request = maintenance_service.update_maintenance_request(request_id, data)
    
    if updated_request:
        flash('Maintenance request updated successfully', 'success')
    else:
        flash('Error updating maintenance request', 'danger')
    
    return redirect(url_for('manager.view_maintenance_request', request_id=request_id))


@manager_bp.route('/maintenance/<int:request_id>/resolve', methods=['POST'])
@login_required
@role_required('manager')
def resolve_maintenance_request(request_id):
    """Mark a maintenance request as resolved."""
    maintenance_service = MaintenanceService(db.session)
    request_obj = maintenance_service.get_maintenance_request(request_id)
    
    if not request_obj:
        flash('Maintenance request not found', 'danger')
        return redirect(url_for('manager.maintenance'))
    
    notes = request.form.get('notes', '')
    
    # Resolve maintenance request
    resolved_request = maintenance_service.resolve_maintenance_request(request_id, notes)
    
    if resolved_request:
        flash('Maintenance request marked as resolved', 'success')
    else:
        flash('Error resolving maintenance request', 'danger')
    
    return redirect(url_for('manager.view_maintenance_request', request_id=request_id))


@manager_bp.route('/maintenance/<int:request_id>/close', methods=['POST'])
@login_required
@role_required('manager')
def close_maintenance_request(request_id):
    """Close a resolved maintenance request."""
    maintenance_service = MaintenanceService(db.session)
    request_obj = maintenance_service.get_maintenance_request(request_id)
    
    if not request_obj:
        flash('Maintenance request not found', 'danger')
        return redirect(url_for('manager.maintenance'))
    
    if request_obj.status != 'resolved':
        flash('Only resolved requests can be closed', 'warning')
        return redirect(url_for('manager.view_maintenance_request', request_id=request_id))
    
    notes = request.form.get('notes', '')
    
    # Close maintenance request
    closed_request = maintenance_service.close_maintenance_request(
        request_id, 
        verified_by=current_user.id,
        notes=notes
    )
    
    if closed_request:
        flash('Maintenance request closed successfully', 'success')
    else:
        flash('Error closing maintenance request', 'danger')
    
    return redirect(url_for('manager.view_maintenance_request', request_id=request_id))


# Add housekeeping routes
@manager_bp.route('/housekeeping')
@login_required
@role_required('manager')
def housekeeping():
    """Display list of housekeeping tasks."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filter parameters
    filters = {}
    if 'status' in request.args and request.args.get('status'):
        filters['status'] = request.args.get('status')
    if 'priority' in request.args and request.args.get('priority'):
        filters['priority'] = request.args.get('priority')
    if 'task_type' in request.args and request.args.get('task_type'):
        filters['task_type'] = request.args.get('task_type')
    if 'room_id' in request.args and request.args.get('room_id'):
        filters['room_id'] = int(request.args.get('room_id'))
    if 'due_date_from' in request.args and request.args.get('due_date_from'):
        try:
            filters['due_date_from'] = datetime.strptime(request.args.get('due_date_from'), '%Y-%m-%d')
        except ValueError:
            pass
    if 'due_date_to' in request.args and request.args.get('due_date_to'):
        try:
            filters['due_date_to'] = datetime.strptime(request.args.get('due_date_to'), '%Y-%m-%d')
        except ValueError:
            pass
    if 'q' in request.args and request.args.get('q'):
        filters['q'] = request.args.get('q')
    
    housekeeping_service = HousekeepingService(db.session)
    tasks_pagination = housekeeping_service.get_all_housekeeping_tasks(filters, page, per_page)
    
    # Get stats for the dashboard
    stats = housekeeping_service.get_housekeeping_stats()
    
    # Get rooms and staff for forms
    rooms = db.session.query(Room).order_by(Room.number).all()
    housekeeping_staff = db.session.query(User).filter(User.role == 'housekeeping').all()
    
    return render_template(
        'manager/housekeeping/index.html', 
        tasks=tasks_pagination.items,
        pagination=tasks_pagination,
        filters=filters,
        stats=stats,
        rooms=rooms,
        housekeeping_staff=housekeeping_staff
    )


@manager_bp.route('/housekeeping/new', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def new_housekeeping_task():
    """Create a new housekeeping task."""
    if request.method == 'POST':
        # Extract form data
        due_date = datetime.now()
        try:
            due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Invalid due date format', 'warning')
        
        data = {
            'room_id': int(request.form.get('room_id')),
            'task_type': request.form.get('task_type'),
            'description': request.form.get('description', ''),
            'priority': request.form.get('priority', 'normal'),
            'due_date': due_date,
            'notes': request.form.get('notes', '')
        }
        
        if request.form.get('assigned_to'):
            data['assigned_to'] = int(request.form.get('assigned_to'))
        
        # Create housekeeping task
        housekeeping_service = HousekeepingService(db.session)
        task = housekeeping_service.create_housekeeping_task(data)
        
        if task:
            flash('Housekeeping task created successfully', 'success')
            return redirect(url_for('manager.housekeeping'))
        else:
            flash('Error creating housekeeping task', 'danger')
    
    # GET request - show form
    rooms = db.session.query(Room).order_by(Room.number).all()
    housekeeping_staff = db.session.query(User).filter(User.role == 'housekeeping').all()
    
    return render_template(
        'manager/housekeeping/form.html',
        rooms=rooms,
        housekeeping_staff=housekeeping_staff,
        is_new=True,
        default_due_date=datetime.now().strftime('%Y-%m-%dT%H:%M')
    )


@manager_bp.route('/housekeeping/<int:task_id>')
@login_required
@role_required('manager')
def view_housekeeping_task(task_id):
    """View details of a housekeeping task."""
    housekeeping_service = HousekeepingService(db.session)
    task = housekeeping_service.get_housekeeping_task(task_id)
    
    if not task:
        flash('Housekeeping task not found', 'danger')
        return redirect(url_for('manager.housekeeping'))
    
    housekeeping_staff = db.session.query(User).filter(User.role == 'housekeeping').all()
    
    return render_template(
        'manager/housekeeping/view.html', 
        task=task,
        housekeeping_staff=housekeeping_staff
    )


@manager_bp.route('/housekeeping/<int:task_id>/update', methods=['POST'])
@login_required
@role_required('manager')
def update_housekeeping_task(task_id):
    """Update a housekeeping task."""
    housekeeping_service = HousekeepingService(db.session)
    task = housekeeping_service.get_housekeeping_task(task_id)
    
    if not task:
        flash('Housekeeping task not found', 'danger')
        return redirect(url_for('manager.housekeeping'))
    
    # Extract form data
    data = {}
    
    if 'status' in request.form:
        data['status'] = request.form.get('status')
    
    if 'priority' in request.form:
        data['priority'] = request.form.get('priority')
    
    if 'assigned_to' in request.form:
        if request.form.get('assigned_to'):
            data['assigned_to'] = int(request.form.get('assigned_to'))
        else:
            data['assigned_to'] = None
    
    if 'due_date' in request.form:
        try:
            data['due_date'] = datetime.strptime(request.form.get('due_date'), '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Invalid due date format', 'warning')
    
    if 'notes' in request.form:
        data['notes'] = request.form.get('notes')
    
    # Update housekeeping task
    updated_task = housekeeping_service.update_housekeeping_task(task_id, data)
    
    if updated_task:
        flash('Housekeeping task updated successfully', 'success')
    else:
        flash('Error updating housekeeping task', 'danger')
    
    return redirect(url_for('manager.view_housekeeping_task', task_id=task_id))


@manager_bp.route('/housekeeping/<int:task_id>/complete', methods=['POST'])
@login_required
@role_required('manager')
def complete_housekeeping_task(task_id):
    """Mark a housekeeping task as completed."""
    housekeeping_service = HousekeepingService(db.session)
    task = housekeeping_service.get_housekeeping_task(task_id)
    
    if not task:
        flash('Housekeeping task not found', 'danger')
        return redirect(url_for('manager.housekeeping'))
    
    notes = request.form.get('notes', '')
    
    # Complete housekeeping task
    completed_task = housekeeping_service.complete_housekeeping_task(task_id, notes)
    
    if completed_task:
        flash('Housekeeping task marked as completed', 'success')
    else:
        flash('Error completing housekeeping task', 'danger')
    
    return redirect(url_for('manager.view_housekeeping_task', task_id=task_id))


@manager_bp.route('/housekeeping/<int:task_id>/verify', methods=['POST'])
@login_required
@role_required('manager')
def verify_housekeeping_task(task_id):
    """Verify a completed housekeeping task."""
    housekeeping_service = HousekeepingService(db.session)
    task = housekeeping_service.get_housekeeping_task(task_id)
    
    if not task:
        flash('Housekeeping task not found', 'danger')
        return redirect(url_for('manager.housekeeping'))
    
    if task.status != 'completed':
        flash('Only completed tasks can be verified', 'warning')
        return redirect(url_for('manager.view_housekeeping_task', task_id=task_id))
    
    notes = request.form.get('notes', '')
    
    # Verify housekeeping task
    verified_task = housekeeping_service.verify_housekeeping_task(
        task_id, 
        verified_by=current_user.id,
        notes=notes
    )
    
    if verified_task:
        flash('Housekeeping task verified successfully', 'success')
    else:
        flash('Error verifying housekeeping task', 'danger')
    
    return redirect(url_for('manager.view_housekeeping_task', task_id=task_id))


@manager_bp.route('/housekeeping/generate-turnover-tasks', methods=['POST'])
@login_required
@role_required('manager')
def generate_turnover_tasks():
    """Generate turnover tasks for rooms with checkouts."""
    date_str = request.form.get('date')
    checkout_date = None
    
    if date_str:
        try:
            checkout_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'warning')
            return redirect(url_for('manager.housekeeping'))
    
    housekeeping_service = HousekeepingService(db.session)
    tasks_created = housekeeping_service.generate_turnover_tasks(checkout_date)
    
    if tasks_created > 0:
        flash(f'Successfully generated {tasks_created} turnover tasks', 'success')
    else:
        flash('No new turnover tasks were needed', 'info')
    
    return redirect(url_for('manager.housekeeping')) 