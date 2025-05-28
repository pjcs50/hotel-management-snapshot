"""
Admin routes module.

This module defines the routes for admin operations.
"""

from datetime import datetime, timedelta
import io
import csv
from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request, send_file, Response, render_template_string
from flask_login import login_required, current_user
from sqlalchemy import func, desc, extract, case, and_, or_

from app.utils.decorators import role_required
from app.services.dashboard_service import DashboardService
from app.services.user_service import UserService
from app.services.report_service import ReportService
from db import db

# Create blueprint
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    """Display admin dashboard."""
    # Get admin dashboard metrics
    try:
        dashboard_service = DashboardService(db.session)
        metrics = dashboard_service.get_admin_metrics()
        return render_template('admin/dashboard.html', metrics=metrics)
    except Exception as e:
        # If there's an error, still attempt to render the template with an error message
        error_metrics = {
            "error": f"Error loading dashboard data: {str(e)}"
        }
        return render_template('admin/dashboard.html', metrics=error_metrics)


@admin_bp.route('/approve-role/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def approve_role(user_id):
    """Approve a role request from a user."""
    user_service = UserService(db.session)
    from app.models.user import User
    from app.models.staff_request import StaffRequest
    
    # Find the user and their staff request
    user = User.query.get_or_404(user_id)
    staff_request = StaffRequest.query.filter_by(user_id=user_id, status='pending').first()
    
    if not user.role_requested:
        flash('This user does not have a pending role request.', 'warning')
        return redirect(url_for('admin.dashboard'))
    
    try:
        notes = None
        if request.method == 'POST':
            notes = request.form.get('notes')
        
        if staff_request:
            # If there's a staff request record, approve it
            user_service.approve_staff_request(staff_request.id, current_user.id, notes)
        else:
            # Otherwise just update the user's role directly
            user.role = user.role_requested
            user.role_requested = None
            user.is_active = True
            db.session.commit()
        
        flash(f'Role request for {user.username} has been approved.', 'success')
    except Exception as e:
        flash(f'Error approving role request: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/deny-role/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def deny_role(user_id):
    """Deny a role request from a user."""
    user_service = UserService(db.session)
    from app.models.user import User
    from app.models.staff_request import StaffRequest
    
    # Find the user and their staff request
    user = User.query.get_or_404(user_id)
    staff_request = StaffRequest.query.filter_by(user_id=user_id, status='pending').first()
    
    if not user.role_requested:
        flash('This user does not have a pending role request.', 'warning')
        return redirect(url_for('admin.dashboard'))
    
    try:
        notes = None
        if request.method == 'POST':
            notes = request.form.get('notes')
        
        if staff_request:
            # If there's a staff request record, deny it
            user_service.deny_staff_request(staff_request.id, current_user.id, notes)
        else:
            # Otherwise just update the user's role directly
            user.role_requested = None
            db.session.commit()
        
        flash(f'Role request for {user.username} has been denied.', 'info')
    except Exception as e:
        flash(f'Error denying role request: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    """Manage users."""
    from app.models.user import User
    
    # Get filter parameters
    role_filter = request.args.get('role', '')
    search_query = request.args.get('q', '')
    
    # Base query
    query = User.query
    
    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) | 
            (User.email.ilike(f'%{search_query}%'))
        )
    
    # Get all users
    users_list = query.order_by(User.created_at.desc()).all()
    
    # Get all available roles for the filter dropdown
    available_roles = db.session.query(User.role).distinct().all()
    roles = [role[0] for role in available_roles]
    
    return render_template(
        'admin/users.html', 
        users=users_list, 
        roles=roles,
        current_role=role_filter,
        search_query=search_query
    )


@admin_bp.route('/roles')
@login_required
@role_required('admin')
def roles():
    """Manage user roles."""
    from app.models.user import User
    from app.models.staff_request import StaffRequest
    
    # Get all role requests
    pending_requests = StaffRequest.query.filter_by(status='pending').all()
    
    # Count users by role for statistics
    role_counts = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    role_stats = {role: count for role, count in role_counts}
    
    # Get pending role requests from users table as well (in case they don't have a staff_request record)
    pending_role_users = User.query.filter(User.role_requested.isnot(None)).all()
    
    # Combine users with pending roles but no staff request
    for user in pending_role_users:
        # Check if this user already has a staff request
        if not any(request.user_id == user.id for request in pending_requests):
            # Create a virtual request object with the necessary attributes
            class VirtualRequest:
                def __init__(self, user):
                    self.id = None  # No database ID
                    self.user_id = user.id
                    self.role_requested = user.role_requested
                    self.status = 'pending'
                    self.user = user
            
            # Add to the list
            pending_requests.append(VirtualRequest(user))
    
    return render_template(
        'admin/roles.html',
        pending_requests=pending_requests,
        role_stats=role_stats
    )


@admin_bp.route('/guests')
@login_required
@role_required('admin')
def guests():
    """Manage guest information."""
    from app.models.customer import Customer
    from app.models.user import User
    
    # Get filter parameters
    search_query = request.args.get('q', '')
    
    # Base query - join with users to get email
    query = db.session.query(Customer, User).join(User, Customer.user_id == User.id)
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(
            or_(
                Customer.name.ilike(f'%{search_query}%'),
                Customer.phone.ilike(f'%{search_query}%'),
                Customer.address.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )
    
    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(Customer.name).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'admin/guests.html',
        pagination=pagination,
        search_query=search_query
    )


@admin_bp.route('/guests/<int:customer_id>')
@login_required
@role_required('admin')
def guest_details(customer_id):
    """View detailed information about a guest."""
    from app.models.customer import Customer
    from app.models.booking import Booking
    
    # Get the customer and their bookings
    customer = Customer.query.get_or_404(customer_id)
    bookings = Booking.query.filter_by(customer_id=customer_id).order_by(Booking.check_in_date.desc()).all()
    
    # Calculate some stats
    total_bookings = len(bookings)
    total_nights = sum(booking.nights for booking in bookings if booking.status != Booking.STATUS_CANCELLED)
    completed_stays = sum(1 for booking in bookings if booking.status == Booking.STATUS_CHECKED_OUT)
    cancelled_bookings = sum(1 for booking in bookings if booking.status == Booking.STATUS_CANCELLED)
    
    return render_template(
        'admin/guest_details.html',
        customer=customer,
        bookings=bookings,
        stats={
            'total_bookings': total_bookings,
            'total_nights': total_nights,
            'completed_stays': completed_stays,
            'cancelled_bookings': cancelled_bookings
        }
    )


@admin_bp.route('/reservations')
@login_required
@role_required('admin')
def reservations():
    """Manage reservations."""
    from app.models.booking import Booking
    from app.models.customer import Customer
    from app.models.room import Room
    from app.models.room_type import RoomType
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    room_type_id = request.args.get('room_type_id', '')
    search_query = request.args.get('q', '')
    
    # Parse dates if provided
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None
    except ValueError:
        date_from_obj = None
        date_to_obj = None
    
    # Base query - include all relations we need
    query = db.session.query(Booking, Customer, Room, RoomType)\
        .join(Customer, Booking.customer_id == Customer.id)\
        .join(Room, Booking.room_id == Room.id)\
        .join(RoomType, Room.room_type_id == RoomType.id)
    
    # Apply filters
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    
    if date_from_obj:
        # Find bookings where check-in date is on or after date_from
        query = query.filter(Booking.check_in_date >= date_from_obj)
    
    if date_to_obj:
        # Find bookings where check-out date is on or before date_to
        query = query.filter(Booking.check_out_date <= date_to_obj)
    
    if room_type_id:
        try:
            room_type_id_int = int(room_type_id)
            query = query.filter(Room.room_type_id == room_type_id_int)
        except ValueError:
            pass
    
    if search_query:
        query = query.filter(
            or_(
                Customer.name.ilike(f'%{search_query}%'),
                Room.number.ilike(f'%{search_query}%')
            )
        )
    
    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(Booking.check_in_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all available room types for the filter dropdown
    room_types = RoomType.query.all()
    
    # Get all available booking statuses for the filter dropdown
    statuses = Booking.STATUS_CHOICES
    
    return render_template(
        'admin/reservations.html',
        pagination=pagination,
        room_types=room_types,
        statuses=statuses,
        filters={
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'room_type_id': room_type_id,
            'search_query': search_query
        }
    )


@admin_bp.route('/reservations/<int:booking_id>')
@login_required
@role_required('admin')
def reservation_details(booking_id):
    """View detailed information about a reservation."""
    from app.models.booking import Booking
    
    # Get the booking with all related information
    booking = Booking.query.get_or_404(booking_id)
    
    return render_template(
        'admin/reservation_details.html',
        booking=booking
    )


@admin_bp.route('/reservations/check-in/<int:booking_id>', methods=['POST'])
@login_required
@role_required('admin')
def check_in_reservation(booking_id):
    """Check in a guest for their reservation."""
    from app.models.booking import Booking
    from app.services.booking_service import BookingService
    
    booking = Booking.query.get_or_404(booking_id)
    booking_service = BookingService(db.session)
    
    try:
        # Verify booking is in a valid state for check-in
        if booking.status != Booking.STATUS_RESERVED:
            flash(f"Cannot check in reservation in {booking.status} status. Only RESERVED bookings can be checked in.", "warning")
            return redirect(url_for('admin.reservation_details', booking_id=booking_id))
            
        # Process check-in
        booking_service.check_in(booking_id)
        db.session.commit()
        flash(f"Guest checked in successfully for room {booking.room.number}.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(f"Error checking in guest: {str(e)}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Unexpected error checking in guest: {str(e)}", "danger")
    
    return redirect(url_for('admin.reservation_details', booking_id=booking_id))


@admin_bp.route('/reservations/check-out/<int:booking_id>', methods=['POST'])
@login_required
@role_required('admin')
def check_out_reservation(booking_id):
    """Check out a guest from their reservation."""
    from app.models.booking import Booking
    from app.services.booking_service import BookingService
    
    booking = Booking.query.get_or_404(booking_id)
    booking_service = BookingService(db.session)
    
    try:
        # Verify booking is in a valid state for check-out
        if booking.status != Booking.STATUS_CHECKED_IN:
            flash(f"Cannot check out reservation in {booking.status} status. Only CHECKED_IN bookings can be checked out.", "warning")
            return redirect(url_for('admin.reservation_details', booking_id=booking_id))
            
        # Process check-out
        booking_service.check_out(booking_id)
        db.session.commit()
        flash(f"Guest checked out successfully from room {booking.room.number}.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(f"Error checking out guest: {str(e)}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Unexpected error checking out guest: {str(e)}", "danger")
    
    return redirect(url_for('admin.reservation_details', booking_id=booking_id))


@admin_bp.route('/reservations/cancel/<int:booking_id>', methods=['POST'])
@login_required
@role_required('admin')
def cancel_reservation(booking_id):
    """Cancel a reservation."""
    from app.models.booking import Booking
    from app.services.booking_service import BookingService
    
    booking = Booking.query.get_or_404(booking_id)
    booking_service = BookingService(db.session)
    
    try:
        # Verify booking is in a valid state for cancellation
        if booking.status == Booking.STATUS_CHECKED_IN:
            flash("Cannot cancel a reservation that is already checked in. Please check out the guest first.", "warning")
            return redirect(url_for('admin.reservation_details', booking_id=booking_id))
        elif booking.status in [Booking.STATUS_CHECKED_OUT, Booking.STATUS_CANCELLED]:
            flash(f"This reservation is already in {booking.status} status.", "warning")
            return redirect(url_for('admin.reservation_details', booking_id=booking_id))
            
        # Process cancellation
        booking_service.cancel_booking(booking_id)
        db.session.commit()
        flash(f"Reservation for room {booking.room.number} cancelled successfully.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(f"Error cancelling reservation: {str(e)}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Unexpected error cancelling reservation: {str(e)}", "danger")
    
    return redirect(url_for('admin.reservation_details', booking_id=booking_id))


@admin_bp.route('/reservations/print/<int:booking_id>')
@login_required
@role_required('admin')
def print_reservation(booking_id):
    """Print a reservation receipt."""
    from app.models.booking import Booking
    
    booking = Booking.query.get_or_404(booking_id)
    
    # In a real application, you would generate a printable PDF here
    # For now, just redirect with a flash message
    flash("Print functionality is not yet implemented.", "warning")
    return redirect(url_for('admin.reservation_details', booking_id=booking_id))


@admin_bp.route('/reservations/email/<int:booking_id>')
@login_required
@role_required('admin')
def email_reservation(booking_id):
    """Email a reservation confirmation."""
    from app.models.booking import Booking
    
    booking = Booking.query.get_or_404(booking_id)
    
    # In a real application, you would send an email here
    # For now, just redirect with a flash message
    flash("Email functionality is not yet implemented.", "warning")
    return redirect(url_for('admin.reservation_details', booking_id=booking_id))


@admin_bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    """Generate reports page."""
    today = datetime.now()
    start_date = request.args.get('start_date', (today.replace(day=1)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    report_type = request.args.get('report_type', 'occupancy')
    try:
        report_service = ReportService(db.session)
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
            
        # Check if report_data is None before rendering template
        if report_data is None:
            flash("No data available for the selected period", "warning")
            report_data = {
                'revenue_summary': {'total_revenue': 0, 'room_revenue': 0},
                'occupancy_summary': {'average_occupancy_rate': 0, 'peak_occupancy_date': '', 'peak_occupancy_rate': 0, 'total_room_nights': 0},
                'booking_summary': {'total_bookings': 0, 'new_bookings': 0, 'cancelled_bookings': 0, 'completed_stays': 0},
                'room_type_revenue': {},
                'daily_occupancy': {}
            }
            
        return render_template(
            'admin/reports.html',
            report_data=report_data,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            title=title,
            current_year=int(start_date[:4]),
            current_month=int(start_date[5:7])
        )
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        # Create an empty report_data structure to avoid None errors
        report_data = {
            'revenue_summary': {'total_revenue': 0, 'room_revenue': 0},
            'occupancy_summary': {'average_occupancy_rate': 0, 'peak_occupancy_date': '', 'peak_occupancy_rate': 0, 'total_room_nights': 0},
            'booking_summary': {'total_bookings': 0, 'new_bookings': 0, 'cancelled_bookings': 0, 'completed_stays': 0},
            'room_type_revenue': {},
            'daily_occupancy': {}
        }
        return render_template(
            'admin/reports.html',
            report_data=report_data,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            title="Report Error",
            current_year=int(start_date[:4]),
            current_month=int(start_date[5:7])
        )


@admin_bp.route('/reports/export')
@login_required
@role_required('admin')
def export_report():
    """Export report data."""
    # Get parameters
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    format_type = request.args.get('format', 'excel')
    
    # Define month names for display
    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    # Create a ReportService instance
    report_service = ReportService(db.session)
    
    try:
        # Get report data
        report_data = report_service.get_monthly_report(year, month)
        
        # Generate the month name for the filename
        month_name = month_names[month - 1]
        filename = f"hotel_report_{month_name}_{year}"
        
        if format_type == 'html':
            html_content = render_template_string('''
                <html>
                <head>
                    <title>{{ filename }}</title>
                    <style>
                        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 32px; background: #f8f9fa; color: #222; }
                        h1 { color: #2c3e50; margin-bottom: 0.5em; }
                        h2 { color: #007bff; margin-top: 2em; margin-bottom: 0.5em; }
                        table { border-collapse: collapse; width: 100%; margin-bottom: 2em; background: #fff; box-shadow: 0 2px 8px #0001; }
                        th, td { border: 1px solid #dee2e6; padding: 10px 16px; text-align: left; }
                        th { background: #007bff; color: #fff; font-weight: 600; }
                        tr:nth-child(even) { background: #f2f2f2; }
                        .section { margin-bottom: 2em; }
                    </style>
                </head>
                <body>
                <h1>{{ filename }}</h1>
                <div class="section">
                    <h2>Revenue Summary</h2>
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Total Revenue</td><td>${{ report_data['revenue_summary']['total_revenue'] }}</td></tr>
                        <tr><td>Room Revenue</td><td>${{ report_data['revenue_summary']['room_revenue'] }}</td></tr>
                    </table>
                </div>
                <div class="section">
                    <h2>Booking Summary</h2>
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Total Bookings</td><td>{{ report_data['booking_summary']['total_bookings'] }}</td></tr>
                        <tr><td>New Bookings</td><td>{{ report_data['booking_summary']['new_bookings'] }}</td></tr>
                        <tr><td>Cancelled Bookings</td><td>{{ report_data['booking_summary']['cancelled_bookings'] }}</td></tr>
                        <tr><td>Completed Stays</td><td>{{ report_data['booking_summary']['completed_stays'] }}</td></tr>
                    </table>
                </div>
                <div class="section">
                    <h2>Occupancy Summary</h2>
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Average Occupancy Rate</td><td>{{ report_data['occupancy_summary']['average_occupancy_rate'] }}%</td></tr>
                        <tr><td>Peak Occupancy Date</td><td>{{ report_data['occupancy_summary']['peak_occupancy_date'] }}</td></tr>
                        <tr><td>Peak Occupancy Rate</td><td>{{ report_data['occupancy_summary']['peak_occupancy_rate'] }}%</td></tr>
                        <tr><td>Total Room Nights</td><td>{{ report_data['occupancy_summary']['total_room_nights'] }}</td></tr>
                    </table>
                </div>
                <div class="section">
                    <h2>Room Type Revenue</h2>
                    <table>
                        <tr><th>Room Type</th><th>Revenue</th><th>Percentage</th></tr>
                        {% for room_type, data in report_data['room_type_revenue'].items() %}
                        <tr><td>{{ room_type }}</td><td>${{ data['revenue'] }}</td><td>{{ data['percentage'] }}%</td></tr>
                        {% endfor %}
                    </table>
                </div>
                <div class="section">
                    <h2>Daily Occupancy</h2>
                    <table>
                        <tr><th>Date</th><th>Occupancy Rate (%)</th></tr>
                        {% for date, rate in report_data['daily_occupancy'].items() %}
                        <tr><td>{{ date }}</td><td>{{ rate }}%</td></tr>
                        {% endfor %}
                    </table>
                </div>
                </body></html>
            ''', filename=filename, report_data=report_data)
            return Response(
                html_content,
                mimetype="text/html",
                headers={"Content-Disposition": f"attachment;filename={filename}.html"}
            )
            
        elif format_type == 'csv':
            # Create a CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['Hotel Monthly Report', f'{month_name} {year}'])
            writer.writerow([])
            
            # Write revenue summary
            writer.writerow(['Revenue Summary'])
            writer.writerow(['Category', 'Amount'])
            writer.writerow(['Total Revenue', f"${report_data['revenue_summary']['total_revenue']:.2f}"])
            writer.writerow(['Room Revenue', f"${report_data['revenue_summary']['room_revenue']:.2f}"])
            
            # Write occupancy summary
            writer.writerow([])
            writer.writerow(['Occupancy Summary'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Average Occupancy Rate', f"{report_data['occupancy_summary']['average_occupancy_rate']:.2f}%"])
            writer.writerow(['Peak Occupancy Date', report_data['occupancy_summary']['peak_occupancy_date']])
            writer.writerow(['Peak Occupancy Rate', f"{report_data['occupancy_summary']['peak_occupancy_rate']:.2f}%"])
            writer.writerow(['Total Room Nights', report_data['occupancy_summary']['total_room_nights']])
            
            # Write booking summary
            writer.writerow([])
            writer.writerow(['Booking Summary'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Bookings', report_data['booking_summary']['total_bookings']])
            writer.writerow(['New Bookings', report_data['booking_summary']['new_bookings']])
            writer.writerow(['Cancelled Bookings', report_data['booking_summary']['cancelled_bookings']])
            writer.writerow(['Completed Stays', report_data['booking_summary']['completed_stays']])
            
            # Write room type revenue
            writer.writerow([])
            writer.writerow(['Room Type Revenue'])
            writer.writerow(['Room Type', 'Revenue', 'Percentage'])
            for room_type, data in report_data['room_type_revenue'].items():
                writer.writerow([room_type, f"${data['revenue']:.2f}", f"{data['percentage']:.2f}%"])
            
            # Set the file pointer at the beginning
            output.seek(0)
            
            return Response(
                output,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment;filename={filename}.csv"}
            )
            
        elif format_type == 'excel':
            # For Excel, we'll use pandas which is more robust for Excel files
            try:
                import pandas as pd
                from io import BytesIO
                
                # Create an Excel writer with multiple sheets
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Add a title sheet
                    title_data = {
                        'Title': [f'Hotel Monthly Report - {month_name} {year}', '']
                    }
                    title_df = pd.DataFrame(title_data)
                    title_df.to_excel(writer, sheet_name='Report Info', index=False)
                    
                    # Format the title sheet
                    title_sheet = writer.sheets['Report Info']
                    title_sheet.set_column(0, 0, 50)
                    title_format = writer.book.add_format({
                        'bold': True,
                        'font_size': 16
                    })
                    title_sheet.write('A1', f'Hotel Monthly Report - {month_name} {year}', title_format)
                    title_sheet.write('A2', f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                    
                    # Summary sheet
                    summary_data = {
                        'Metric': [
                            'Total Revenue', 'Room Revenue', 
                            'Average Occupancy Rate', 'Peak Occupancy Date', 'Peak Occupancy Rate',
                            'Total Room Nights', 'Total Bookings', 'New Bookings',
                            'Cancelled Bookings', 'Completed Stays'
                        ],
                        'Value': [
                            f"${report_data['revenue_summary']['total_revenue']:.2f}",
                            f"${report_data['revenue_summary']['room_revenue']:.2f}",
                            f"{report_data['occupancy_summary']['average_occupancy_rate']:.2f}%",
                            report_data['occupancy_summary']['peak_occupancy_date'],
                            f"{report_data['occupancy_summary']['peak_occupancy_rate']:.2f}%",
                            report_data['occupancy_summary']['total_room_nights'],
                            report_data['booking_summary']['total_bookings'],
                            report_data['booking_summary']['new_bookings'],
                            report_data['booking_summary']['cancelled_bookings'],
                            report_data['booking_summary']['completed_stays']
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Room Type Revenue sheet
                    room_type_data = {
                        'Room Type': [],
                        'Revenue': [],
                        'Percentage': []
                    }
                    for room_type, data in report_data['room_type_revenue'].items():
                        room_type_data['Room Type'].append(room_type)
                        room_type_data['Revenue'].append(f"${data['revenue']:.2f}")
                        room_type_data['Percentage'].append(f"{data['percentage']:.2f}%")
                    
                    room_type_df = pd.DataFrame(room_type_data)
                    room_type_df.to_excel(writer, sheet_name='Room Type Revenue', index=False)
                    
                    # Daily occupancy sheet
                    daily_data = {
                        'Date': list(report_data['daily_occupancy'].keys()),
                        'Occupancy Rate': [f"{rate:.2f}%" for rate in report_data['daily_occupancy'].values()]
                    }
                    daily_df = pd.DataFrame(daily_data)
                    daily_df.to_excel(writer, sheet_name='Daily Occupancy', index=False)
                    
                    # Format the sheets
                    workbook = writer.book
                    header_format = workbook.add_format({
                        'bold': True,
                        'text_wrap': True,
                        'valign': 'top',
                        'fg_color': '#D7E4BC',
                        'border': 1
                    })
                    
                    for sheet_name in writer.sheets:
                        worksheet = writer.sheets[sheet_name]
                        for col_num, value in enumerate(writer.sheets[sheet_name].get_row_data(0)):
                            worksheet.set_column(col_num, col_num, 18)
                            if sheet_name != 'Report Info':  # Skip the title sheet
                                worksheet.write(0, col_num, value, header_format)
                
                output.seek(0)
                
                return send_file(
                    output,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    as_attachment=True,
                    download_name=f"{filename}.xlsx"
                )
                
            except ImportError as e:
                missing_module = str(e).split("'")[1] if "'" in str(e) else "pandas or xlsxwriter"
                flash(f"Excel export requires {missing_module}. Please install it using 'pip install {missing_module}'. Defaulting to CSV.", "warning")
                return redirect(url_for('admin.export_report', month=month, year=year, format='csv'))
        
        else:
            # PDF format
            try:
                # Check if reportlab is available first
                try:
                    import reportlab
                    from reportlab.lib import colors
                    from reportlab.lib.pagesizes import letter, landscape
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib.units import inch
                    from io import BytesIO
                except ImportError as e:
                    missing_module = str(e).split("'")[1] if "'" in str(e) else "reportlab"
                    flash(f"PDF export requires {missing_module}. Please install it using 'pip install {missing_module}'. Defaulting to CSV.", "warning")
                    return redirect(url_for('admin.export_report', month=month, year=year, format='csv'))
                
                from flask import make_response
                
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, 
                                        leftMargin=0.5*inch, rightMargin=0.5*inch,
                                        topMargin=0.5*inch, bottomMargin=0.5*inch)
                styles = getSampleStyleSheet()
                
                # Custom styles
                styles.add(ParagraphStyle(name='CustomTitle', 
                                         parent=styles['Title'],
                                         fontSize=16,
                                         alignment=1,  # Center
                                         spaceAfter=12))
                styles.add(ParagraphStyle(name='CustomHeading2',
                                         parent=styles['Heading2'],
                                         fontSize=14,
                                         spaceAfter=10))
                
                elements = []
                
                # Title and date
                title = Paragraph(f"Hotel Monthly Report - {month_name} {year}", styles['CustomTitle'])
                elements.append(title)
                
                date_generated = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                          styles['Normal'])
                elements.append(date_generated)
                elements.append(Spacer(1, 20))
                
                # Revenue summary
                revenue_title = Paragraph("Revenue Summary", styles['CustomHeading2'])
                elements.append(revenue_title)
                elements.append(Spacer(1, 10))
                
                revenue_data = [
                    ['Category', 'Amount'],
                    ['Total Revenue', f"${report_data['revenue_summary']['total_revenue']:.2f}"],
                    ['Room Revenue', f"${report_data['revenue_summary']['room_revenue']:.2f}"]
                ]
                
                revenue_table = Table(revenue_data, [200, 200])
                revenue_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                    ('BACKGROUND', (0, 1), (1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ]))
                
                elements.append(revenue_table)
                elements.append(Spacer(1, 20))
                
                # Occupancy summary
                occupancy_title = Paragraph("Occupancy Summary", styles['CustomHeading2'])
                elements.append(occupancy_title)
                elements.append(Spacer(1, 10))
                
                occupancy_data = [
                    ['Metric', 'Value'],
                    ['Average Occupancy Rate', f"{report_data['occupancy_summary']['average_occupancy_rate']:.2f}%"],
                    ['Peak Occupancy Date', report_data['occupancy_summary']['peak_occupancy_date']],
                    ['Peak Occupancy Rate', f"{report_data['occupancy_summary']['peak_occupancy_rate']:.2f}%"],
                    ['Total Room Nights', str(report_data['occupancy_summary']['total_room_nights'])]
                ]
                
                occupancy_table = Table(occupancy_data, [200, 200])
                occupancy_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                    ('BACKGROUND', (0, 1), (1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ]))
                
                elements.append(occupancy_table)
                elements.append(Spacer(1, 20))
                
                # Booking summary
                booking_title = Paragraph("Booking Summary", styles['CustomHeading2'])
                elements.append(booking_title)
                elements.append(Spacer(1, 10))
                
                booking_data = [
                    ['Metric', 'Value'],
                    ['Total Bookings', str(report_data['booking_summary']['total_bookings'])],
                    ['New Bookings', str(report_data['booking_summary']['new_bookings'])],
                    ['Cancelled Bookings', str(report_data['booking_summary']['cancelled_bookings'])],
                    ['Completed Stays', str(report_data['booking_summary']['completed_stays'])]
                ]
                
                booking_table = Table(booking_data, [200, 200])
                booking_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                    ('BACKGROUND', (0, 1), (1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ]))
                
                elements.append(booking_table)
                elements.append(Spacer(1, 20))
                
                # Room type revenue
                room_type_title = Paragraph("Room Type Revenue", styles['CustomHeading2'])
                elements.append(room_type_title)
                elements.append(Spacer(1, 10))
                
                room_type_data = [
                    ['Room Type', 'Revenue', 'Percentage']
                ]
                for room_type, data in report_data['room_type_revenue'].items():
                    room_type_data.append([
                        room_type, 
                        f"${data['revenue']:.2f}", 
                        f"{data['percentage']:.2f}%"
                    ])
                
                room_type_table = Table(room_type_data, [150, 150, 100])
                room_type_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (2, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (2, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (2, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (2, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (2, 0), 12),
                    ('BACKGROUND', (0, 1), (2, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
                ]))
                
                elements.append(room_type_table)
                
                # Build PDF
                doc.build(elements)
                buffer.seek(0)
                
                response = make_response(buffer.getvalue())
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename={filename}.pdf'
                return response
                
            except ImportError as e:
                # More detailed error message with specific missing module
                missing_module = str(e).split("'")[1] if "'" in str(e) else "reportlab"
                flash(f"PDF export requires {missing_module}. Please install it using 'pip install {missing_module}'. Defaulting to CSV.", "warning")
                return redirect(url_for('admin.export_report', month=month, year=year, format='csv'))
            except Exception as e:
                # Handle other exceptions during PDF generation
                flash(f"Error generating PDF: {str(e)}. Defaulting to CSV.", "warning")
                return redirect(url_for('admin.export_report', month=month, year=year, format='csv'))
    
    except Exception as e:
        flash(f"Error exporting report: {str(e)}", "danger")
        return redirect(url_for('admin.reports', month=month, year=year))


@admin_bp.route('/settings')
@login_required
@role_required('admin')
def settings():
    """Manage system settings."""
    return jsonify({
        "message": "System Settings - Not yet implemented"
    })


@admin_bp.route('/logs')
@login_required
@role_required('admin')
def logs():
    """View system logs."""
    import os
    from datetime import datetime
    
    # Path to the log file
    log_file = os.path.join(os.getcwd(), 'app.log')
    
    # Default values
    log_content = []
    error_message = None
    
    # Read log file if it exists
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                # Read last 500 lines (for performance reasons)
                log_content = f.readlines()[-500:]
            
            # Format log entries for display
            formatted_logs = []
            for line in log_content:
                # Try to parse the log line
                try:
                    # Assume format like: 2025-05-17 16:36:40,993 INFO sqlalchemy.engine.Engine BEGIN (implicit)
                    parts = line.split(' ', 2)
                    date_str = parts[0]
                    time_str = parts[1].split(',')[0]
                    rest = parts[2] if len(parts) > 2 else ""
                    
                    level_parts = rest.split(' ', 1)
                    level = level_parts[0] if level_parts else ""
                    message = level_parts[1] if len(level_parts) > 1 else ""
                    
                    formatted_logs.append({
                        'timestamp': f"{date_str} {time_str}",
                        'level': level,
                        'message': message.strip()
                    })
                except Exception:
                    # If parsing fails, include the raw line
                    formatted_logs.append({
                        'timestamp': 'Unknown',
                        'level': 'UNKNOWN',
                        'message': line.strip()
                    })
        except Exception as e:
            error_message = f"Error reading log file: {str(e)}"
    else:
        error_message = "Log file not found."
    
    return render_template(
        'admin/logs.html',
        logs=formatted_logs,
        error=error_message,
        last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


@admin_bp.route('/backup')
@login_required
@role_required('admin')
def backup():
    """Backup system data."""
    return jsonify({
        "message": "System Backup - Not yet implemented"
    })


@admin_bp.route('/toggle-user-status/<int:user_id>')
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    """Toggle a user's active status."""
    from app.models.user import User
    
    # Find the user
    user = User.query.get_or_404(user_id)
    
    # Don't allow deactivating the current admin
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for('admin.users'))
    
    # Toggle the status
    user.is_active = not user.is_active
    
    status_text = "activated" if user.is_active else "deactivated"
    
    try:
        db.session.commit()
        flash(f"User {user.username} has been {status_text}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating user status: {str(e)}", "danger")
    
    return redirect(url_for('admin.users')) 