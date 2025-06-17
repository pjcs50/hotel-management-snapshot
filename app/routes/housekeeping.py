"""
Housekeeping routes module.

This module defines the routes for housekeeping operations.
"""

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

from app.utils.decorators import role_required
from app.services.dashboard_service import DashboardService
from app.services.housekeeping_service import HousekeepingService
from app.services.maintenance_service import MaintenanceService
from app.models.room import Room
from app.models.housekeeping_task import HousekeepingTask
from app.models.room_status_log import RoomStatusLog
from app.models.user import User
from app.models.booking import Booking
from db import db
from app.utils.room_state_machine import RoomStateMachine, RoomTransitionError

# Create blueprint
housekeeping_bp = Blueprint('housekeeping', __name__)


@housekeeping_bp.route('/dashboard')
@login_required
@role_required('housekeeping')
def dashboard():
    """Display housekeeping dashboard."""
    # Get housekeeping dashboard metrics
    try:
        service = DashboardService(db.session)  # Instantiate the service
        metrics = service.get_housekeeping_metrics()
        return render_template('housekeeping/dashboard.html', metrics=metrics)
    except Exception as e:
        # If there's an error, still attempt to render the template with an error message
        error_metrics = {
            "error": f"Error loading dashboard data: {str(e)}"
        }
        return render_template('housekeeping/dashboard.html', metrics=error_metrics)


@housekeeping_bp.route('/tasks')
@login_required
@role_required('housekeeping')
def tasks():
    """View and manage cleaning tasks."""
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

    # If staff member, only show their tasks by default
    if 'assigned_to' not in filters:
        filters['assigned_to'] = current_user.id

    housekeeping_service = HousekeepingService(db.session)
    tasks_pagination = housekeeping_service.get_all_housekeeping_tasks(filters, page, per_page)

    task_types = ['regular_cleaning', 'deep_cleaning', 'turnover', 'restocking', 'maintenance_followup']
    priorities = ['low', 'normal', 'high', 'urgent']
    statuses = ['pending', 'in_progress', 'completed', 'verified']

    return render_template(
        'housekeeping/tasks.html',
        tasks=tasks_pagination.items,
        pagination=tasks_pagination,
        filters=filters,
        task_types=task_types,
        priorities=priorities,
        statuses=statuses
    )


@housekeeping_bp.route('/tasks/<int:task_id>', methods=['GET', 'POST'])
@login_required
@role_required('housekeeping')
def task_detail(task_id):
    """View and update a task."""
    housekeeping_service = HousekeepingService(db.session)
    task = housekeeping_service.get_housekeeping_task(task_id)

    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('housekeeping.tasks'))

    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('notes', '')

        if action == 'start':
            housekeeping_service.mark_in_progress(task_id, notes)
            flash('Task marked as in progress', 'success')
        elif action == 'complete':
            housekeeping_service.complete_housekeeping_task(task_id, notes)
            flash('Task marked as completed', 'success')

        return redirect(url_for('housekeeping.task_detail', task_id=task_id))

    return render_template('housekeeping/task_detail.html', task=task)


@housekeeping_bp.route('/rooms-to-clean')
@login_required
@role_required('housekeeping')
def rooms_to_clean_view():
    """View rooms that need cleaning."""
    # Get rooms that need cleaning
    rooms = db.session.query(Room).filter(Room.status.in_(['dirty', 'checkout'])).order_by(Room.number).all()

    # Group rooms by floor
    rooms_by_floor = {}
    for room in rooms:
        floor = str(room.number)[0] if len(str(room.number)) > 1 else '1'
        if floor not in rooms_by_floor:
            rooms_by_floor[floor] = []
        rooms_by_floor[floor].append(room)

    return render_template('housekeeping/rooms_to_clean.html', rooms_by_floor=rooms_by_floor, total_rooms=len(rooms))


@housekeeping_bp.route('/checkout-rooms')
@login_required
@role_required('housekeeping')
def checkout_rooms_view():
    """View rooms with scheduled checkouts."""
    today = datetime.now().date()

    # Get bookings with checkout today
    checkout_bookings = (
        db.session.query(Booking)
        .filter(
            func.date(Booking.check_out_date) == today,
            Booking.status == 'checked_in'
        )
        .order_by(Booking.check_out_date)
        .all()
    )

    return render_template('housekeeping/checkout_rooms.html', bookings=checkout_bookings)


@housekeeping_bp.route('/maintenance-requests', methods=['GET', 'POST'])
@login_required
@role_required('housekeeping')
def maintenance_requests():
    """View and create maintenance requests."""
    maintenance_service = MaintenanceService(db.session)

    if request.method == 'POST':
        # Create a new maintenance request
        data = {
            'room_id': request.form.get('room_id', type=int),
            'issue_type': request.form.get('issue_type'),
            'description': request.form.get('description'),
            'priority': request.form.get('priority', 'normal'),
            'reported_by': current_user.id
        }

        if not all(key in data and data[key] for key in ['room_id', 'issue_type', 'description']):
            flash('Please fill out all required fields', 'danger')
        else:
            maintenance_service.create_maintenance_request(data)
            flash('Maintenance request created successfully', 'success')
            return redirect(url_for('housekeeping.maintenance_requests'))

    # Get all maintenance requests
    requests = maintenance_service.get_all_maintenance_requests().items

    # Get all rooms for the form
    rooms = db.session.query(Room).order_by(Room.number).all()

    return render_template(
        'housekeeping/maintenance_requests.html',
        requests=requests,
        rooms=rooms,
        issue_types=['plumbing', 'electrical', 'furniture', 'appliance', 'other'],
        priorities=['low', 'normal', 'high', 'urgent']
    )


@housekeeping_bp.route('/report-maintenance-issue', methods=['GET', 'POST'])
@login_required
@role_required('housekeeping')
def report_maintenance_issue():
    """Report a maintenance issue."""
    maintenance_service = MaintenanceService(db.session)

    if request.method == 'POST':
        # Create a new maintenance request
        data = {
            'room_id': request.form.get('room_id', type=int),
            'issue_type': request.form.get('issue_type'),
            'description': request.form.get('description'),
            'priority': request.form.get('priority', 'normal'),
            'reported_by': current_user.id
        }

        if not all(key in data and data[key] for key in ['room_id', 'issue_type', 'description']):
            flash('Please fill out all required fields', 'danger')
        else:
            maintenance_service.create_maintenance_request(data)
            flash('Maintenance issue reported successfully', 'success')
            return redirect(url_for('housekeeping.dashboard'))

    # Get all rooms for the form
    rooms = db.session.query(Room).order_by(Room.number).all()

    return render_template(
        'housekeeping/report_maintenance.html',
        rooms=rooms,
        issue_types=['plumbing', 'electrical', 'furniture', 'appliance', 'other'],
        priorities=['low', 'normal', 'high', 'urgent']
    )


@housekeeping_bp.route('/room-status', methods=['GET', 'POST'])
@login_required
@role_required('housekeeping')
def room_status():
    """Update room cleaning status with enhanced validation."""
    if request.method == 'POST':
        room_id = request.form.get('room_id', type=int)
        new_status = request.form.get('new_status')
        notes = request.form.get('notes', '')

        if not room_id or not new_status:
            flash('Room ID and new status are required', 'danger')
            return redirect(url_for('housekeeping.room_status'))

        room = db.session.query(Room).get(room_id)
        if not room:
            flash('Room not found', 'danger')
            return redirect(url_for('housekeeping.room_status'))

        try:
            # Use enhanced room state machine for validation
            state_machine = RoomStateMachine(db.session)
            old_status = room.status
            
            # Attempt to change status with validation
            updated_room = state_machine.change_room_status(
                room_id=room.id,
                new_status=new_status,
                user_id=current_user.id,
                notes=notes
            )
            
            flash(f'Room {room.number} status updated from {old_status} to {new_status}', 'success')
            
        except RoomTransitionError as e:
            flash(f'Invalid status change: {str(e)}', 'danger')
            return redirect(url_for('housekeeping.room_status'))
        except ValueError as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('housekeeping.room_status'))
        except Exception as e:
            db.session.rollback()
            flash(f'Unexpected error: {str(e)}', 'danger')
            return redirect(url_for('housekeeping.room_status'))

        return redirect(url_for('housekeeping.room_status'))

    # Get all rooms with enhanced status information
    rooms = db.session.query(Room).order_by(Room.number).all()
    
    # Add valid transitions for each room
    state_machine = RoomStateMachine(db.session)
    
    for room in rooms:
        room.valid_transitions = state_machine.get_valid_transitions(room.status)
        room.status_description = state_machine.get_status_description(room.status)

    # Get recent status changes
    recent_changes = (
        db.session.query(RoomStatusLog)
        .order_by(RoomStatusLog.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'housekeeping/room_status.html',
        rooms=rooms,
        recent_changes=recent_changes,
        all_statuses=Room.STATUS_CHOICES
    )


@housekeeping_bp.route('/cleaning-schedule')
@login_required
@role_required('housekeeping')
def cleaning_schedule():
    """View cleaning schedule."""
    # Get date range
    start_date = request.args.get('start_date')
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date()

    end_date = start_date + timedelta(days=6)  # Show a week

    # Get all housekeeping tasks in date range
    housekeeping_service = HousekeepingService(db.session)

    # Get checkouts in date range for turnover tasks
    checkouts = (
        db.session.query(Booking)
        .filter(
            func.date(Booking.check_out_date) >= start_date,
            func.date(Booking.check_out_date) <= end_date,
            Booking.status.in_(['confirmed', 'checked_in'])
        )
        .order_by(Booking.check_out_date)
        .all()
    )

    # Get pending tasks for date range
    tasks = (
        db.session.query(HousekeepingTask)
        .filter(
            func.date(HousekeepingTask.due_date) >= start_date,
            func.date(HousekeepingTask.due_date) <= end_date,
            HousekeepingTask.status.in_(['pending', 'in_progress'])
        )
        .order_by(HousekeepingTask.due_date)
        .all()
    )

    # Organize tasks by day
    days = []
    current_date = start_date
    while current_date <= end_date:
        day_tasks = [t for t in tasks if t.due_date.date() == current_date]
        day_checkouts = [b for b in checkouts if b.check_out_date.date() == current_date]

        days.append({
            'date': current_date,
            'tasks': day_tasks,
            'checkouts': day_checkouts,
            'total': len(day_tasks) + len(day_checkouts)
        })

        current_date += timedelta(days=1)

    # Add a helper function to get current date for template
    def now():
        return datetime.now()

    return render_template(
        'housekeeping/cleaning_schedule.html',
        days=days,
        start_date=start_date,
        end_date=end_date,
        prev_week=start_date - timedelta(days=7),
        next_week=start_date + timedelta(days=7),
        now=now
    )


@housekeeping_bp.route('/inventory')
@login_required
@role_required('housekeeping')
def inventory():
    """Manage housekeeping inventory."""
    # Simple inventory management for now
    inventory_items = [
        {'id': 1, 'name': 'Towels', 'quantity': 120, 'min_quantity': 50, 'last_restocked': '2024-05-10'},
        {'id': 2, 'name': 'Bed Sheets', 'quantity': 80, 'min_quantity': 40, 'last_restocked': '2024-05-15'},
        {'id': 3, 'name': 'Toilet Paper', 'quantity': 200, 'min_quantity': 100, 'last_restocked': '2024-05-18'},
        {'id': 4, 'name': 'Soap Bars', 'quantity': 150, 'min_quantity': 75, 'last_restocked': '2024-05-12'},
        {'id': 5, 'name': 'Shampoo Bottles', 'quantity': 100, 'min_quantity': 50, 'last_restocked': '2024-05-14'},
        {'id': 6, 'name': 'Cleaning Solution', 'quantity': 30, 'min_quantity': 10, 'last_restocked': '2024-05-05'},
        {'id': 7, 'name': 'Laundry Detergent', 'quantity': 25, 'min_quantity': 10, 'last_restocked': '2024-05-08'},
        {'id': 8, 'name': 'Pillowcases', 'quantity': 90, 'min_quantity': 45, 'last_restocked': '2024-05-16'}
    ]

    # Identify items that need to be restocked
    low_stock_items = [item for item in inventory_items if item['quantity'] < item['min_quantity']]

    return render_template(
        'housekeeping/inventory.html',
        inventory_items=inventory_items,
        low_stock_items=low_stock_items
    )


@housekeeping_bp.route('/lost-and-found')
@login_required
@role_required('housekeeping')
def view_lost_and_found():
    """View lost and found items."""
    # Simple lost and found implementation for now
    lost_items = [
        {'id': 1, 'name': 'Gold Watch', 'room': '101', 'found_date': '2024-05-15', 'status': 'unclaimed', 'found_by': 'John Smith'},
        {'id': 2, 'name': 'Wallet', 'room': '203', 'found_date': '2024-05-16', 'status': 'claimed', 'found_by': 'Maria Garcia'},
        {'id': 3, 'name': 'Phone Charger', 'room': '305', 'found_date': '2024-05-17', 'status': 'unclaimed', 'found_by': 'John Smith'},
        {'id': 4, 'name': 'Sunglasses', 'room': '402', 'found_date': '2024-05-18', 'status': 'unclaimed', 'found_by': 'Maria Garcia'},
        {'id': 5, 'name': 'Passport', 'room': '205', 'found_date': '2024-05-19', 'status': 'claimed', 'found_by': 'David Johnson'}
    ]

    return render_template(
        'housekeeping/lost_and_found.html',
        lost_items=lost_items
    )


@housekeeping_bp.route('/assign-tasks', methods=['GET', 'POST'])
@login_required
@role_required('housekeeping')
def assign_tasks():
    """Assign cleaning tasks to housekeeping staff with enhanced validation."""
    from app.services.housekeeping_service import HousekeepingError
    
    housekeeping_service = HousekeepingService(db.session)

    if request.method == 'POST':
        # Process task assignment form
        task_id = request.form.get('task_id', type=int)
        staff_id = request.form.get('staff_id', type=int)

        if not task_id or not staff_id:
            flash('Task ID and Staff ID are required', 'danger')
            return redirect(url_for('housekeeping.assign_tasks'))

        try:
            # Use enhanced assignment validation
            updated_task = housekeeping_service.assign_housekeeping_task(task_id, staff_id)
            
            # Get staff member name for confirmation
            staff_member = db.session.query(User).get(staff_id)
            staff_name = staff_member.username if staff_member else f"ID {staff_id}"
            
            flash(f'Task #{task_id} successfully assigned to {staff_name}', 'success')
            
        except ValueError as e:
            flash(f'Error: {str(e)}', 'danger')
        except HousekeepingError as e:
            flash(f'Assignment failed: {str(e)}', 'warning')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'danger')

        return redirect(url_for('housekeeping.assign_tasks'))

    # Get unassigned tasks
    unassigned_tasks = housekeeping_service.get_all_housekeeping_tasks(
        filters={'status': 'pending', 'assigned_to': None}
    ).items

    # Get available housekeeping staff (active users with housekeeping role)
    available_staff = db.session.query(User).filter(
        User.role.in_(['housekeeping', 'manager']),
        User.is_active == True
    ).all()

    # Get current task assignments for staff workload display
    staff_workload = {}
    for staff in available_staff:
        active_tasks = db.session.query(HousekeepingTask).filter(
            HousekeepingTask.assigned_to == staff.id,
            HousekeepingTask.status.in_(['pending', 'in_progress'])
        ).count()
        staff_workload[staff.id] = active_tasks

    return render_template(
        'housekeeping/assign_tasks.html',
        unassigned_tasks=unassigned_tasks,
        available_staff=available_staff,
        staff_workload=staff_workload
    )
