"""
Room routes module.

This module defines the routes for room management operations.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

from db import db
from app.models.room import Room
from app.models.room_type import RoomType
from app.services.room_service import RoomService, DuplicateRoomNumberError
from app.utils.decorators import staff_required

# Create blueprint
room_bp = Blueprint('room', __name__)


@room_bp.route('/rooms')
@login_required
@staff_required
def list_rooms():
    """Display a list of all rooms."""
    rooms = Room.query.all()
    return render_template('room/list.html', rooms=rooms)


@room_bp.route('/rooms/<int:room_id>')
@login_required
@staff_required
def view_room(room_id):
    """Display details for a specific room."""
    room = Room.query.get_or_404(room_id)
    return render_template('room/view.html', room=room)


@room_bp.route('/rooms/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_room():
    """Create a new room."""
    room_types = RoomType.query.all()
    
    if request.method == 'POST':
        room_number = request.form.get('number')
        room_type_id = request.form.get('room_type_id')
        status = request.form.get('status', Room.STATUS_AVAILABLE)
        
        room_service = RoomService(db.session)
        
        try:
            room = room_service.create_room(
                number=room_number,
                room_type_id=room_type_id,
                status=status
            )
            
            flash(f'Room {room.number} created successfully.', 'success')
            return redirect(url_for('room.view_room', room_id=room.id))
        
        except DuplicateRoomNumberError:
            flash(f'Room number {room_number} already exists.', 'danger')
        
        except ValueError as e:
            flash(str(e), 'danger')
    
    return render_template('room/create.html', room_types=room_types, room_statuses=Room.STATUS_CHOICES)


@room_bp.route('/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_room(room_id):
    """Edit an existing room."""
    room = Room.query.get_or_404(room_id)
    room_types = RoomType.query.all()
    
    if request.method == 'POST':
        room_number = request.form.get('number')
        room_type_id = request.form.get('room_type_id')
        status = request.form.get('status')
        
        room_service = RoomService(db.session)
        
        try:
            room = room_service.update_room(
                room_id=room.id,
                number=room_number,
                room_type_id=room_type_id,
                status=status
            )
            
            flash(f'Room {room.number} updated successfully.', 'success')
            return redirect(url_for('room.view_room', room_id=room.id))
        
        except DuplicateRoomNumberError:
            flash(f'Room number {room_number} already exists.', 'danger')
        
        except ValueError as e:
            flash(str(e), 'danger')
    
    return render_template('room/edit.html', room=room, room_types=room_types, room_statuses=Room.STATUS_CHOICES)


@room_bp.route('/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_room(room_id):
    """Delete a room."""
    room = Room.query.get_or_404(room_id)
    
    # Check if the room has bookings
    if room.bookings:
        flash('Cannot delete room with existing bookings.', 'danger')
        return redirect(url_for('room.view_room', room_id=room.id))
    
    room_number = room.number
    db.session.delete(room)
    db.session.commit()
    
    flash(f'Room {room_number} deleted successfully.', 'success')
    return redirect(url_for('room.list_rooms'))


@room_bp.route('/rooms/<int:room_id>/change-status', methods=['POST'])
@login_required
@staff_required
def change_room_status(room_id):
    """Change a room's status."""
    room = Room.query.get_or_404(room_id)
    new_status = request.form.get('status')
    
    room_service = RoomService(db.session)
    
    try:
        room = room_service.change_room_status(
            room_id=room.id,
            new_status=new_status,
            user_id=current_user.id
        )
        
        flash(f'Room {room.number} status changed to {room.status}.', 'success')
    
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('room.view_room', room_id=room.id))


@room_bp.route('/rooms/<int:room_id>/mark-cleaned', methods=['POST'])
@login_required
@staff_required
def mark_room_cleaned(room_id):
    """Mark a room as cleaned."""
    room_service = RoomService(db.session)
    
    try:
        room = room_service.mark_room_cleaned(
            room_id=room_id,
            user_id=current_user.id
        )
        
        flash(f'Room {room.number} marked as cleaned.', 'success')
    
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('room.view_room', room_id=room.id))


@room_bp.route('/api/rooms/available')
@login_required
def api_available_rooms():
    """API endpoint to get available rooms."""
    from datetime import datetime
    from app.services.booking_service import BookingService
    
    # Get date parameters from query string
    check_in_str = request.args.get('check_in_date')
    check_out_str = request.args.get('check_out_date')
    room_type_id = request.args.get('room_type_id', type=int)
    
    # Parse dates if provided
    check_in_date = None
    check_out_date = None
    
    try:
        if check_in_str:
            check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        if check_out_str:
            check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Use BookingService to get available rooms with date filtering
    booking_service = BookingService(db.session)
    rooms = booking_service.get_available_rooms(
        room_type_id=room_type_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date
    )
    
    return jsonify({
        'rooms': [{
            'id': room.id,
            'number': room.number,
            'room_type': room.room_type.name,
            'rate': float(room.room_type.base_rate),
            'status': room.status,
            'capacity': room.room_type.capacity
        } for room in rooms]
    }) 