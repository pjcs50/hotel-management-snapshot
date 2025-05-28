"""
API routes module.

This module defines the API endpoints for the hotel booking system.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from db import db
from app.models.room import Room
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.room_status_log import RoomStatusLog
from app.models.booking_log import BookingLog
from app.services.booking_service import BookingService, RoomNotAvailableError
from app.services.room_service import RoomService
from app.services.customer_service import CustomerService
from app.utils.decorators import role_required

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/availability', methods=['GET'])
def get_availability():
    """
    Get room availability for a date range.

    Query parameters:
    - check_in_date: Start date (YYYY-MM-DD)
    - check_out_date: End date (YYYY-MM-DD)
    - room_type_id: Optional room type ID to filter by

    Returns:
        JSON with available rooms
    """
    booking_service = BookingService(db.session)

    # Get query parameters
    check_in_date_str = request.args.get('check_in_date')
    check_out_date_str = request.args.get('check_out_date')
    room_type_id = request.args.get('room_type_id')

    # Validate and parse dates
    try:
        if check_in_date_str:
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
        else:
            check_in_date = datetime.now().date()

        if check_out_date_str:
            check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()
        else:
            check_out_date = check_in_date + timedelta(days=1)

        if room_type_id:
            room_type_id = int(room_type_id)
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format or room type ID'
        }), 400

    # Validate date range
    if check_in_date >= check_out_date:
        return jsonify({
            'success': False,
            'error': 'Check-out date must be after check-in date'
        }), 400

    # Get available rooms
    available_rooms = booking_service.get_available_rooms(
        room_type_id=room_type_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date
    )

    # Format response
    result = {
        'success': True,
        'check_in_date': check_in_date.isoformat(),
        'check_out_date': check_out_date.isoformat(),
        'available_rooms': [
            {
                'id': room.id,
                'number': room.number,
                'room_type_id': room.room_type_id,
                'room_type': {
                    'id': room.room_type.id,
                    'name': room.room_type.name,
                    'description': room.room_type.description,
                    'base_rate': room.room_type.base_rate,
                    'capacity': room.room_type.capacity,
                    'amenities': room.room_type.amenities if hasattr(room.room_type, 'amenities') else []
                }
            }
            for room in available_rooms
        ]
    }

    return jsonify(result)


@api_bp.route('/bookings', methods=['POST'])
@login_required
def create_booking():
    """
    Create a new booking.

    Request body:
    {
        "room_id": 1,
        "customer_id": 1,
        "check_in_date": "2023-06-01",
        "check_out_date": "2023-06-03",
        "num_guests": 2,
        "early_hours": 0,
        "late_hours": 0,
        "special_requests": "Extra pillows please"
    }

    Returns:
        JSON with booking details
    """
    booking_service = BookingService(db.session)

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        }), 400

    # Validate required fields
    required_fields = ['room_id', 'check_in_date', 'check_out_date']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': f'Missing required field: {field}'
            }), 400

    # Parse dates
    try:
        check_in_date = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format'
        }), 400

    # Get customer ID (from current user if not provided)
    customer_id = data.get('customer_id')
    if not customer_id and hasattr(current_user, 'customer_profile'):
        customer_id = current_user.customer_profile.id

    if not customer_id:
        return jsonify({
            'success': False,
            'error': 'Customer ID is required'
        }), 400

    # Create booking
    try:
        booking = booking_service.create_booking(
            room_id=data['room_id'],
            customer_id=customer_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=Booking.STATUS_RESERVED,
            early_hours=data.get('early_hours', 0),
            late_hours=data.get('late_hours', 0),
            num_guests=data.get('num_guests', 1),
            special_requests=data.get('special_requests', '')
        )

        # Calculate price
        booking.calculate_price()
        db.session.commit()

        return jsonify({
            'success': True,
            'booking': booking.to_dict()
        })
    except RoomNotAvailableError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 409
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating booking: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/bookings/<int:booking_id>', methods=['GET'])
@login_required
def get_booking(booking_id):
    """
    Get booking details.

    Returns:
        JSON with booking details
    """
    booking_service = BookingService(db.session)

    try:
        # Check if user has access to this booking
        if not current_user.has_role('admin') and not current_user.has_role('receptionist'):
            if not hasattr(current_user, 'customer_profile') or not booking_service.is_booking_owned_by_customer(booking_id, current_user.customer_profile.id):
                return jsonify({
                    'success': False,
                    'error': 'Access denied'
                }), 403

        booking = booking_service.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'error': 'Booking not found'
            }), 404

        return jsonify({
            'success': True,
            'booking': booking.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Error retrieving booking: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
@login_required
def update_booking(booking_id):
    """
    Update a booking.

    Request body:
    {
        "check_in_date": "2023-06-01",
        "check_out_date": "2023-06-03",
        "num_guests": 2,
        "early_hours": 0,
        "late_hours": 0,
        "special_requests": "Extra pillows please"
    }

    Returns:
        JSON with updated booking details
    """
    booking_service = BookingService(db.session)

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        }), 400

    try:
        # Check if user has access to this booking
        if not current_user.has_role('admin') and not current_user.has_role('receptionist'):
            if not hasattr(current_user, 'customer_profile') or not booking_service.is_booking_owned_by_customer(booking_id, current_user.customer_profile.id):
                return jsonify({
                    'success': False,
                    'error': 'Access denied'
                }), 403

        # Parse dates if provided
        if 'check_in_date' in data:
            data['check_in_date'] = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
        if 'check_out_date' in data:
            data['check_out_date'] = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()

        # Update booking
        booking = booking_service.update_booking(booking_id, **data)

        # Recalculate price if dates or hours changed
        if any(key in data for key in ['check_in_date', 'check_out_date', 'early_hours', 'late_hours']):
            booking.calculate_price()
            db.session.commit()

        return jsonify({
            'success': True,
            'booking': booking.to_dict()
        })
    except RoomNotAvailableError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 409
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error updating booking: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/bookings/<int:booking_id>/status', methods=['PATCH'])
@login_required
@role_required(['admin', 'receptionist'])
def update_booking_status(booking_id):
    """
    Update booking status.

    Request body:
    {
        "status": "Checked In"
    }

    Returns:
        JSON with updated booking details
    """
    booking_service = BookingService(db.session)

    # Get request data
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({
            'success': False,
            'error': 'Status is required'
        }), 400

    status = data['status']
    if status not in Booking.STATUS_CHOICES:
        return jsonify({
            'success': False,
            'error': f'Invalid status: {status}'
        }), 400

    try:
        booking = booking_service.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'error': 'Booking not found'
            }), 404

        # Handle status change based on requested status
        if status == Booking.STATUS_CHECKED_IN:
            booking = booking_service.check_in(booking_id)
        elif status == Booking.STATUS_CHECKED_OUT:
            booking = booking_service.check_out(booking_id)
        elif status == Booking.STATUS_CANCELLED:
            reason = data.get('reason', '')
            booking = booking_service.cancel_booking(booking_id, reason=reason, cancelled_by=current_user.id)
        else:
            # For other status changes, just update the status
            booking.status = status
            db.session.commit()

        return jsonify({
            'success': True,
            'booking': booking.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error updating booking status: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/bookings/<int:booking_id>/early-check-in', methods=['POST'])
@login_required
def request_early_check_in(booking_id):
    """
    Request early check-in for a booking.

    Request body:
    {
        "hours": 2
    }

    Returns:
        JSON with updated booking details
    """
    booking_service = BookingService(db.session)

    # Get request data
    data = request.get_json()
    if not data or 'hours' not in data:
        return jsonify({
            'success': False,
            'error': 'Hours is required'
        }), 400

    try:
        hours = int(data['hours'])
        if hours <= 0:
            return jsonify({
                'success': False,
                'error': 'Hours must be positive'
            }), 400
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Hours must be a number'
        }), 400

    try:
        # Check if user has access to this booking
        if not current_user.has_role('admin') and not current_user.has_role('receptionist'):
            if not hasattr(current_user, 'customer_profile') or not booking_service.is_booking_owned_by_customer(booking_id, current_user.customer_profile.id):
                return jsonify({
                    'success': False,
                    'error': 'Access denied'
                }), 403

        # Update early check-in hours
        booking = booking_service.update_booking(booking_id, early_hours=hours)

        # Recalculate price
        booking.calculate_price()
        db.session.commit()

        return jsonify({
            'success': True,
            'booking': booking.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error requesting early check-in: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/bookings/<int:booking_id>/late-check-out', methods=['POST'])
@login_required
def request_late_check_out(booking_id):
    """
    Request late check-out for a booking.

    Request body:
    {
        "hours": 2
    }

    Returns:
        JSON with updated booking details
    """
    booking_service = BookingService(db.session)

    # Get request data
    data = request.get_json()
    if not data or 'hours' not in data:
        return jsonify({
            'success': False,
            'error': 'Hours is required'
        }), 400

    try:
        hours = int(data['hours'])
        if hours <= 0:
            return jsonify({
                'success': False,
                'error': 'Hours must be positive'
            }), 400
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Hours must be a number'
        }), 400

    try:
        # Check if user has access to this booking
        if not current_user.has_role('admin') and not current_user.has_role('receptionist'):
            if not hasattr(current_user, 'customer_profile') or not booking_service.is_booking_owned_by_customer(booking_id, current_user.customer_profile.id):
                return jsonify({
                    'success': False,
                    'error': 'Access denied'
                }), 403

        # Update late check-out hours
        booking = booking_service.update_booking(booking_id, late_hours=hours)

        # Recalculate price
        booking.calculate_price()
        db.session.commit()

        return jsonify({
            'success': True,
            'booking': booking.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error requesting late check-out: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/rooms/<int:room_id>/status', methods=['PATCH'])
@login_required
@role_required(['admin', 'receptionist', 'housekeeping'])
def update_room_status(room_id):
    """
    Update room status.

    Request body:
    {
        "status": "Available"
    }

    Returns:
        JSON with updated room details
    """
    room_service = RoomService(db.session)

    # Get request data
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({
            'success': False,
            'error': 'Status is required'
        }), 400

    status = data['status']
    if status not in Room.STATUS_CHOICES:
        return jsonify({
            'success': False,
            'error': f'Invalid status: {status}'
        }), 400

    try:
        room = room_service.get_room_by_id(room_id)
        if not room:
            return jsonify({
                'success': False,
                'error': 'Room not found'
            }), 404

        # Update room status
        room.change_status(status, current_user.id)
        db.session.commit()

        return jsonify({
            'success': True,
            'room': room.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error updating room status: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@api_bp.route('/rooms/<int:room_id>/cleaned', methods=['POST'])
@login_required
@role_required(['admin', 'receptionist', 'housekeeping'])
def mark_room_cleaned(room_id):
    """
    Mark a room as cleaned.

    Returns:
        JSON with updated room details
    """
    room_service = RoomService(db.session)

    try:
        room = room_service.get_room_by_id(room_id)
        if not room:
            return jsonify({
                'success': False,
                'error': 'Room not found'
            }), 404

        # Mark room as cleaned
        room.mark_as_cleaned()
        db.session.commit()

        # Log the status change
        log = RoomStatusLog(
            room_id=room.id,
            old_status=Room.STATUS_CLEANING,
            new_status=Room.STATUS_AVAILABLE,
            changed_by=current_user.id,
            notes="Marked as cleaned"
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'success': True,
            'room': room.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error marking room as cleaned: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500
