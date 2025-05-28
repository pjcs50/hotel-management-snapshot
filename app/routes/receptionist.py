"""
Receptionist routes module.

This module defines the routes for receptionist operations.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import HTTPException

from db import db
from app.utils.decorators import role_required
from app.services.dashboard_service import DashboardService
from app.services.booking_service import BookingService
from app.services.room_service import RoomService
from app.models.room_type import RoomType
from app.models.room import Room
from app.models.booking import Booking
from app.models.customer import Customer
from app.models.room_status_log import RoomStatusLog
from app.models.folio_item import FolioItem
from app.models.payment import Payment

# Create blueprint
receptionist_bp = Blueprint('receptionist', __name__)


@receptionist_bp.route('/dashboard')
@login_required
@role_required('receptionist')
def dashboard():
    """Display receptionist dashboard."""
    # Get receptionist dashboard metrics
    try:
        dashboard_service = DashboardService(db.session)
        metrics = dashboard_service.get_receptionist_metrics()
        return render_template('receptionist/dashboard.html', metrics=metrics)
    except HTTPException as he:
        raise he
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}", exc_info=True)
        error_metrics = {
            "error": "An unexpected error occurred while loading dashboard data."
        }
        return render_template('receptionist/dashboard.html', metrics=error_metrics), 500


@receptionist_bp.route('/bookings')
@login_required
@role_required('receptionist')
def bookings():
    """Manage bookings."""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search_query = request.args.get('q', '')

    # Create query
    query = Booking.query

    # Apply filters
    if status_filter:
        query = query.filter(Booking.status == status_filter)

    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Booking.check_in_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Booking.check_out_date <= date_to_obj)
        except ValueError:
            pass

    # Apply search query
    if search_query:
        query = query.join(Customer).filter(Customer.name.ilike(f'%{search_query}%'))

    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 20
    bookings = query.order_by(Booking.check_in_date.desc()).paginate(page=page, per_page=per_page)

    # Get statuses for filter
    statuses_list = Booking.STATUS_CHOICES
    # Convert to list of tuples for template unpacking
    statuses_for_template = [(status, status) for status in statuses_list]

    return render_template(
        'receptionist/bookings.html',
        bookings=bookings,
        statuses=statuses_for_template,
        filters={
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search_query': search_query
        },
        metrics={}
    )


@receptionist_bp.route('/new-booking', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def new_booking():
    """Create a new booking."""
    from app.forms.booking_forms import BookingForm
    from app.services.booking_service import BookingService, RoomNotAvailableError
    from app.models.booking import Booking
    from app.models.room import Room
    from app.models.room_type import RoomType
    from app.models.customer import Customer
    from datetime import datetime, timedelta
    import json

    # Initialize services
    booking_service = BookingService(db.session)

    # Get all room types for display
    room_types = RoomType.query.all()

    # Set default dates
    today = datetime.now().date()
    default_check_in = today + timedelta(days=1)
    default_check_out = today + timedelta(days=2)

    # Initialize form
    form = BookingForm()
    form.status.data = Booking.STATUS_RESERVED

    # Initialize price variables
    estimated_price = None
    base_rate = None
    nights = None
    early_fee = None
    late_fee = None

    # Handle form submission
    if request.method == 'POST':
        # Check if it's an AJAX request for updating room options
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # If only updating options (e.g., date change)
        if request.form.get('action') == 'update_options':
            # Update available rooms based on selected dates
            if form.check_in_date.data and form.check_out_date.data:
                # Get available rooms
                available_rooms = booking_service.get_available_rooms(
                    check_in_date=form.check_in_date.data,
                    check_out_date=form.check_out_date.data
                )

                # Update room choices
                form.room_id.choices = [(room.id, f"Room {room.number} - {room.room_type.name}") for room in available_rooms]

                # Calculate price if room is selected
                if form.room_id.data:
                    try:
                        # Calculate price components
                        room = Room.query.get(form.room_id.data)
                        if room:
                            base_rate = room.room_type.base_rate
                            nights = (form.check_out_date.data - form.check_in_date.data).days
                            early_fee = base_rate * 0.1 * (form.early_hours.data or 0)
                            late_fee = base_rate * 0.1 * (form.late_hours.data or 0)
                            estimated_price = base_rate * nights + early_fee + late_fee
                    except Exception as e:
                        current_app.logger.error(f"Error calculating price: {e}")

                # If AJAX request, return JSON response
                if is_ajax:
                    room_options = []
                    for room in available_rooms:
                        room_options.append({
                            'value': room.id,
                            'text': f"Room {room.number} - {room.room_type.name}",
                            'room_number': room.number,
                            'room_type': room.room_type.name,
                            'capacity': room.room_type.capacity,
                            'rate': room.room_type.base_rate,
                            'amenities': room.room_type.amenities if hasattr(room.room_type, 'amenities') else ''
                        })

                    return jsonify({
                        'success': True,
                        'room_options': room_options,
                        'estimated_price': estimated_price
                    })

            # For non-AJAX requests, just re-render the template
            return render_template(
                'receptionist/new_booking.html',
                form=form,
                room_types=room_types,
                estimated_price=estimated_price,
                base_rate=base_rate,
                nights=nights,
                early_fee=early_fee,
                late_fee=late_fee,
                today=today.strftime('%Y-%m-%d'),
                tomorrow=(today + timedelta(days=1)).strftime('%Y-%m-%d')
            )

        # If creating a booking
        elif request.form.get('action') == 'create_booking':
            # Check if using existing customer or creating new one
            customer_id = form.customer_id.data
            if not customer_id:
                # Create new customer
                guest_name = request.form.get('guest_name')
                guest_email = request.form.get('guest_email')
                guest_phone = request.form.get('guest_phone')

                if not guest_name:
                    flash('Guest name is required', 'danger')
                    return redirect(url_for('receptionist.new_booking'))

                # Create customer
                customer = Customer(
                    name=guest_name,
                    email=guest_email,
                    phone=guest_phone
                )
                db.session.add(customer)
                db.session.commit()
                customer_id = customer.id

            # Validate form
            if form.validate_on_submit():
                try:
                    # Create booking
                    booking = booking_service.create_booking(
                        room_id=form.room_id.data,
                        customer_id=customer_id,
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data,
                        status=Booking.STATUS_RESERVED,
                        early_hours=form.early_hours.data or 0,
                        late_hours=form.late_hours.data or 0,
                        num_guests=form.num_guests.data,
                        special_requests=form.special_requests.data,
                        source='receptionist'
                    )

                    # Calculate price
                    booking.calculate_price()
                    db.session.commit()

                    flash(f'Booking created successfully. Confirmation code: {booking.confirmation_code}', 'success')
                    return redirect(url_for('receptionist.booking_details', booking_id=booking.id))

                except RoomNotAvailableError as e:
                    flash(f'Error: {str(e)}', 'danger')
                except ValueError as e:
                    flash(f'Error: {str(e)}', 'danger')
                except Exception as e:
                    current_app.logger.error(f"Error creating booking: {e}")
                    flash('An unexpected error occurred', 'danger')

    # For GET requests
    else:
        # Set default values
        form.check_in_date.data = default_check_in
        form.check_out_date.data = default_check_out
        form.num_guests.data = 1

        # Get available rooms for default dates
        available_rooms = booking_service.get_available_rooms(
            check_in_date=default_check_in,
            check_out_date=default_check_out
        )

        # Update room choices
        form.room_id.choices = [(room.id, f"Room {room.number} - {room.room_type.name}") for room in available_rooms]

    return render_template(
        'receptionist/new_booking.html',
        form=form,
        room_types=room_types,
        estimated_price=estimated_price,
        base_rate=base_rate,
        nights=nights,
        early_fee=early_fee,
        late_fee=late_fee,
        today=today.strftime('%Y-%m-%d'),
        tomorrow=(today + timedelta(days=1)).strftime('%Y-%m-%d')
    )


@receptionist_bp.route('/search-customers')
@login_required
@role_required('receptionist')
def search_customers():
    """Search for customers by name, email, or phone."""
    from app.models.customer import Customer
    from sqlalchemy import or_

    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify({
            'success': False,
            'message': 'Search query must be at least 2 characters',
            'customers': []
        })

    # Search for customers
    customers = Customer.query.filter(
        or_(
            Customer.name.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%')
        )
    ).limit(10).all()

    # Format results
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone
        })

    return jsonify({
        'success': True,
        'customers': results
    })


@receptionist_bp.route('/room-availability')
@login_required
@role_required('receptionist')
def room_availability():
    """View room availability."""
    try:
        # Get all rooms with their types and status
        rooms = db.session.query(Room).join(RoomType).order_by(Room.number).all()

        # Get date range parameters, default to next 7 days
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Parse date parameters or use defaults
        today = datetime.now().date()
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = today
        else:
            start_date = today

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                end_date = today + timedelta(days=7)
        else:
            end_date = today + timedelta(days=7)

        # Get room types for filter
        room_types = RoomType.query.all()

        # Initialize booking service
        booking_service = BookingService(db.session)

        # Get availability data
        availability_data = booking_service.get_availability_calendar_data(
            start_date=start_date,
            end_date=end_date
        )

        # Add room statistics
        total_rooms = Room.query.count()
        available_today = Room.query.filter_by(status=Room.STATUS_AVAILABLE).count()
        occupied_today = Room.query.filter_by(status=Room.STATUS_OCCUPIED).count()

        # Calculate occupancy rate
        occupancy_rate = 0
        if total_rooms > 0:
            occupancy_rate = round((occupied_today / total_rooms) * 100)

        # Add room statistics to availability data
        availability_data['room_stats'] = {
            'total_rooms': total_rooms,
            'available_today': available_today,
            'occupied_today': occupied_today,
            'occupancy_rate': occupancy_rate
        }

        return render_template(
            'receptionist/availability_calendar.html',
            room_types=room_types,
            availability_data=availability_data,
            start_date=start_date,
            end_date=end_date,
            selected_room_type_id=None,
            today_str=today.strftime('%Y-%m-%d'),
            metrics={}
        )
    except Exception as e:
        current_app.logger.error(f"Error loading room availability: {str(e)}")
        return jsonify({
            "message": f"Room Availability - Error: {str(e)}"
        })


@receptionist_bp.route('/room-inventory')
@login_required
@role_required('receptionist')
def room_inventory():
    """Display detailed room inventory."""
    try:
        # Get all rooms with their types and status
        rooms = db.session.query(Room).join(RoomType).order_by(Room.number).all()

        # Group rooms by type
        room_types = {}
        for room in rooms:
            if room.room_type_id not in room_types:
                room_types[room.room_type_id] = {
                    'type': room.room_type,
                    'rooms': []
                }
            room_types[room.room_type_id]['rooms'].append(room)

        # Get bookings for rooms that are occupied or booked
        occupied_room_ids = [room.id for room in rooms if room.status in [Room.STATUS_OCCUPIED, Room.STATUS_BOOKED]]
        bookings = {}

        if occupied_room_ids:
            booking_query = db.session.query(Booking).filter(
                Booking.room_id.in_(occupied_room_ids),
                Booking.status.in_([Booking.STATUS_CHECKED_IN, Booking.STATUS_RESERVED])
            ).all()

            for booking in booking_query:
                bookings[booking.room_id] = booking

        # Get room status logs for recent changes
        room_logs = db.session.query(RoomStatusLog).order_by(
            RoomStatusLog.change_time.desc()
        ).limit(10).all()

        return render_template(
            'receptionist/room_inventory.html',
            room_types=room_types,
            bookings=bookings,
            room_logs=room_logs,
            room_statuses=Room.STATUS_CHOICES,
            metrics={}
        )
    except Exception as e:
        flash(f"Error loading room inventory: {str(e)}", "danger")
        return redirect(url_for('receptionist.dashboard'))


@receptionist_bp.route('/guests')
@login_required
@role_required('receptionist')
def guests():
    """Manage guest information."""
    # Redirect to the guest_list route
    return redirect(url_for('receptionist.guest_list'))


@receptionist_bp.route('/view-guest/<int:customer_id>')
@login_required
@role_required('receptionist')
def view_guest(customer_id):
    """View guest details."""
    try:
        customer = Customer.query.get_or_404(customer_id)

        # Get bookings for this customer
        bookings = Booking.query.filter_by(customer_id=customer_id).order_by(Booking.check_in_date.desc()).all()

        # Get loyalty information if available
        loyalty_data = None
        try:
            from app.models.loyalty_ledger import LoyaltyLedger
            loyalty_transactions = LoyaltyLedger.query.filter_by(customer_id=customer_id).order_by(LoyaltyLedger.txn_dt.desc()).limit(10).all()
            loyalty_data = {
                'transactions': loyalty_transactions,
                'points': customer.loyalty_points,
                'tier': customer.loyalty_tier
            }
        except (ImportError, AttributeError):
            pass

        return render_template(
            'receptionist/guest_details.html',
            customer=customer,
            bookings=bookings,
            loyalty_data=loyalty_data,
            metrics={}
        )
    except Exception as e:
        flash(f"Error retrieving guest: {str(e)}", "danger")
        return redirect(url_for('receptionist.guest_list'))


@receptionist_bp.route('/add-guest-note/<int:customer_id>', methods=['POST'])
@login_required
@role_required('receptionist')
def add_guest_note(customer_id):
    """Add a note to a guest's profile."""
    try:
        customer = Customer.query.get_or_404(customer_id)

        note = request.form.get('note', '')
        if not note:
            flash("Note cannot be empty.", "warning")
            return redirect(url_for('receptionist.view_guest', customer_id=customer_id))

        # Add timestamp and user to the note
        timestamped_note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} by {current_user.username}] {note}"

        # Append to existing notes or create new
        if customer.notes:
            customer.notes = f"{customer.notes}\n\n{timestamped_note}"
        else:
            customer.notes = timestamped_note

        db.session.commit()

        flash("Note added successfully.", "success")
        return redirect(url_for('receptionist.view_guest', customer_id=customer_id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding note: {str(e)}", "danger")
        return redirect(url_for('receptionist.view_guest', customer_id=customer_id))


@receptionist_bp.route('/edit-guest/<int:customer_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def edit_guest(customer_id):
    """Edit guest information."""
    try:
        customer = Customer.query.get_or_404(customer_id)

        if request.method == 'POST':
            # Update customer information
            customer.name = request.form.get('name')
            customer.email = request.form.get('email')
            customer.phone = request.form.get('phone')
            customer.address = request.form.get('address')
            customer.id_type = request.form.get('id_type')
            customer.id_number = request.form.get('id_number')
            customer.emergency_contact = request.form.get('emergency_contact')

            db.session.commit()

            flash("Guest information updated successfully.", "success")
            return redirect(url_for('receptionist.view_guest', customer_id=customer_id))

        return render_template(
            'receptionist/edit_guest.html',
            customer=customer
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Error editing guest: {str(e)}", "danger")
        return redirect(url_for('receptionist.view_guest', customer_id=customer_id))


@receptionist_bp.route('/guest-list')
@login_required
@role_required('receptionist')
def guest_list():
    """View guest list."""
    # Get filter parameters
    search_query = request.args.get('q', '')

    # Create query
    query = Customer.query

    # Apply search filter if provided
    if search_query:
        query = query.filter(
            Customer.name.ilike(f'%{search_query}%') |
            Customer.phone.ilike(f'%{search_query}%') |
            Customer.address.ilike(f'%{search_query}%')
        )

    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 20
    customers = query.order_by(Customer.name).paginate(page=page, per_page=per_page)

    return render_template(
        'receptionist/guest_list.html',
        customers=customers,
        search_query=search_query,
        metrics={}
    )


@receptionist_bp.route('/check-in')
@login_required
@role_required('receptionist')
def check_in():
    """Check in guests."""
    # Get today's check-ins
    today = datetime.now().date()

    bookings = db.session.query(Booking).filter(
        Booking.check_in_date == today,
        Booking.status == Booking.STATUS_RESERVED
    ).all()

    return render_template(
        'receptionist/check_in_list.html',
        bookings=bookings,
        today=today,
        metrics={}
    )


@receptionist_bp.route('/check-in-guest/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def check_in_guest(booking_id):
    """Process guest check-in."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        # Verify booking status
        if booking.status != Booking.STATUS_RESERVED:
            flash(f"Cannot check in booking #{booking.id}: Current status is {booking.status}", "danger")
            return redirect(url_for('receptionist.check_in'))

        # For GET requests, show the check-in form
        if request.method == 'GET':
            return render_template(
                'receptionist/check_in_form.html',
                booking=booking,
                metrics={}
            )

        # For POST requests, process the check-in
        # Get form data
        payment_amount = request.form.get('payment_amount', type=float)
        payment_type = request.form.get('payment_type')
        special_notes = request.form.get('special_notes', '')

        # Start a transaction
        try:
            # Check in the guest (this will update room status too)
            booking.check_in(staff_id=current_user.id)

            # Add special notes if provided
            if special_notes:
                if booking.notes:
                    booking.notes += f"\nCheck-in notes: {special_notes}"
                else:
                    booking.notes = f"Check-in notes: {special_notes}"

            # Process payment if provided
            if payment_amount and payment_amount > 0:
                # Create a payment record
                booking.record_payment(
                    amount=payment_amount,
                    payment_type=payment_type,
                    reference=f"Check-in payment by {current_user.username}"
                )

            # Commit the transaction
            db.session.commit()

            flash(f"Guest {booking.customer.name} successfully checked in to Room {booking.room.number}.", "success")
            return redirect(url_for('receptionist.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error during check-in: {str(e)}", "danger")
            return redirect(url_for('receptionist.check_in_guest', booking_id=booking.id))

    except Exception as e:
        flash(f"Error retrieving booking: {str(e)}", "danger")
        return redirect(url_for('receptionist.check_in'))


@receptionist_bp.route('/check-out')
@login_required
@role_required('receptionist')
def check_out():
    """Check out guests."""
    # Get today's check-outs
    today = datetime.now().date()

    bookings = db.session.query(Booking).filter(
        Booking.check_out_date == today,
        Booking.status == Booking.STATUS_CHECKED_IN
    ).all()

    return render_template(
        'receptionist/check_out_list.html',
        bookings=bookings,
        today=today,
        metrics={}
    )


@receptionist_bp.route('/check-out-guest/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def check_out_guest(booking_id):
    """Process guest check-out."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        # Verify booking status
        if booking.status != Booking.STATUS_CHECKED_IN:
            flash(f"Cannot check out booking #{booking.id}: Current status is {booking.status}", "danger")
            return redirect(url_for('receptionist.check_out'))

        # Get charges for this booking
        try:
            folio_items = FolioItem.get_booking_charges(booking.id)
            total_charges = FolioItem.get_booking_total_charges(booking.id)
        except Exception as e:
            current_app.logger.error(f"Error getting folio items for checkout: {str(e)}")
            folio_items = []
            total_charges = 0.0

        # Calculate remaining balance
        try:
            total_paid = Payment.get_booking_total_paid(booking.id)
        except Exception as e:
            current_app.logger.error(f"Error getting total paid for checkout: {str(e)}")
            total_paid = 0.0

        balance_due = max(0, total_charges - total_paid)

        # For GET requests, show the check-out form
        if request.method == 'GET':
            try:
                return render_template(
                    'receptionist/check_out_form.html',
                    booking=booking,
                    folio_items=folio_items,
                    total_charges=total_charges,
                    total_paid=total_paid,
                    balance_due=balance_due,
                    metrics={}
                )
            except Exception as form_error:
                current_app.logger.error(f"Error rendering checkout form: {str(form_error)}", exc_info=True)
                flash(f"Error loading checkout form: {str(form_error)}", "danger")
                return redirect(url_for('receptionist.check_out'))

        # For POST requests, process the check-out
        # Get form data
        payment_amount = request.form.get('payment_amount', type=float)
        payment_type = request.form.get('payment_type')
        late_checkout_hours = request.form.get('late_checkout_hours', type=int, default=0)
        checkout_notes = request.form.get('checkout_notes', '')

        # Start a transaction
        try:
            # If there was a late check-out, add the hours and charge
            if late_checkout_hours > 0:
                booking.late_hours = late_checkout_hours

                # Calculate late checkout fee
                base_rate = booking.room.room_type.base_rate
                late_fee = (base_rate * 0.1) * late_checkout_hours

                # Add a charge for late check-out
                late_checkout_charge = FolioItem(
                    booking_id=booking.id,
                    description=f"Late check-out fee ({late_checkout_hours} hours)",
                    charge_amount=late_fee,
                    charge_type=FolioItem.TYPE_LATE_CHECKOUT,
                    staff_id=current_user.id
                )
                db.session.add(late_checkout_charge)

                # Update total charges
                total_charges += late_fee
                balance_due = max(0, total_charges - total_paid)

            # Process final payment if provided
            if payment_amount and payment_amount > 0:
                # Create a payment record
                booking.record_payment(
                    amount=payment_amount,
                    payment_type=payment_type,
                    reference=f"Check-out payment by {current_user.username}"
                )

                # Update balance
                balance_due = max(0, balance_due - payment_amount)

            # Add checkout notes if provided
            if checkout_notes:
                if booking.notes:
                    booking.notes += f"\nCheck-out notes: {checkout_notes}"
                else:
                    booking.notes = f"Check-out notes: {checkout_notes}"

            # Only proceed with check-out if balance is fully paid
            if balance_due > 0:
                flash(f"Cannot complete check-out: Outstanding balance of ${balance_due:.2f}", "danger")
                return redirect(url_for('receptionist.check_out_guest', booking_id=booking.id))

            # Check out the guest (this will update room status too)
            booking.check_out(staff_id=current_user.id)

            # Commit the transaction
            db.session.commit()

            flash(f"Guest {booking.customer.name} successfully checked out from Room {booking.room.number}.", "success")
            return redirect(url_for('receptionist.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error during check-out: {str(e)}", "danger")
            return redirect(url_for('receptionist.check_out_guest', booking_id=booking.id))

    except Exception as e:
        current_app.logger.error(f"Error retrieving booking for checkout: {str(e)}", exc_info=True)
        flash(f"Error retrieving booking: {str(e)}", "danger")
        return redirect(url_for('receptionist.check_out'))


@receptionist_bp.route('/view-booking/<int:booking_id>')
@login_required
@role_required('receptionist')
def view_booking(booking_id):
    """View booking details."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        # Get folio items and payments
        try:
            folio_items = FolioItem.get_booking_charges(booking.id)
        except:
            folio_items = []

        try:
            payments = Payment.get_booking_payments(booking.id)
        except:
            payments = []

        return render_template(
            'receptionist/booking_details.html',
            booking=booking,
            folio_items=folio_items,
            payments=payments,
            metrics={}
        )
    except Exception as e:
        flash(f"Error retrieving booking: {str(e)}", "danger")
        return redirect(url_for('receptionist.dashboard'))


@receptionist_bp.route('/view-folio/<int:booking_id>')
@login_required
@role_required('receptionist')
def view_folio(booking_id):
    """View booking folio."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        # Get folio items and payments
        try:
            folio_items = FolioItem.get_booking_charges(booking.id)
            total_charges = FolioItem.get_booking_total_charges(booking.id)
        except Exception as e:
            current_app.logger.error(f"Error getting folio items: {str(e)}")
            folio_items = []
            total_charges = 0.0

        try:
            payments = Payment.get_booking_payments(booking.id)
            total_paid = Payment.get_booking_total_paid(booking.id)
        except Exception as e:
            current_app.logger.error(f"Error getting payments: {str(e)}")
            payments = []
            total_paid = 0.0

        # Calculate balance
        balance = total_charges - total_paid

        return render_template(
            'receptionist/folio_view.html',
            booking=booking,
            folio_items=folio_items,
            payments=payments,
            total_charges=total_charges,
            total_paid=total_paid,
            balance=balance,
            metrics={}
        )
    except Exception as e:
        current_app.logger.error(f"Error retrieving folio: {str(e)}", exc_info=True)
        flash(f"Error retrieving folio: {str(e)}", "danger")
        return redirect(url_for('receptionist.dashboard'))


@receptionist_bp.route('/post-charge/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def post_charge(booking_id):
    """Post a charge to a booking."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        # For GET requests, show the charge form
        if request.method == 'GET':
            try:
                return render_template(
                    'receptionist/post_charge_form.html',
                    booking=booking,
                    charge_types=FolioItem.TYPE_CHOICES,
                    metrics={}
                )
            except Exception as form_error:
                current_app.logger.error(f"Error rendering charge form: {str(form_error)}", exc_info=True)
                flash(f"Error loading charge form: {str(form_error)}", "danger")
                return redirect(url_for('receptionist.view_folio', booking_id=booking.id))

        # For POST requests, process the charge
        # Get form data
        charge_amount = request.form.get('charge_amount', type=float)
        charge_type = request.form.get('charge_type')
        description = request.form.get('description')
        reference = request.form.get('reference', '')

        # Validate input
        if not charge_amount or charge_amount <= 0:
            flash("Charge amount must be greater than zero.", "danger")
            return redirect(url_for('receptionist.post_charge', booking_id=booking.id))

        if not description:
            flash("Description is required.", "danger")
            return redirect(url_for('receptionist.post_charge', booking_id=booking.id))

        # Create the charge
        try:
            folio_item = FolioItem(
                booking_id=booking.id,
                description=description,
                charge_amount=charge_amount,
                charge_type=charge_type,
                staff_id=current_user.id,
                reference=reference
            )
            db.session.add(folio_item)
            db.session.commit()

            flash(f"Charge of ${charge_amount:.2f} posted successfully.", "success")
            return redirect(url_for('receptionist.view_folio', booking_id=booking.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error posting charge: {str(e)}", "danger")
            return redirect(url_for('receptionist.post_charge', booking_id=booking.id))

    except Exception as e:
        current_app.logger.error(f"Error retrieving booking for charge: {str(e)}", exc_info=True)
        flash(f"Error retrieving booking: {str(e)}", "danger")
        return redirect(url_for('receptionist.dashboard'))


@receptionist_bp.route('/process-payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def process_payment(booking_id):
    """Process a payment for a booking."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        # Get current balance
        try:
            total_charges = FolioItem.get_booking_total_charges(booking.id)
            total_paid = Payment.get_booking_total_paid(booking.id)
            balance_due = max(0, total_charges - total_paid)
        except Exception as e:
            current_app.logger.error(f"Error calculating balance: {str(e)}")
            total_charges = 0.0
            total_paid = 0.0
            balance_due = 0.0

        # For GET requests, show the payment form
        if request.method == 'GET':
            try:
                return render_template(
                    'receptionist/payment_form.html',
                    booking=booking,
                    balance_due=balance_due,
                    payment_types=Payment.TYPE_CHOICES,
                    metrics={}
                )
            except Exception as form_error:
                current_app.logger.error(f"Error rendering payment form: {str(form_error)}", exc_info=True)
                flash(f"Error loading payment form: {str(form_error)}", "danger")
                return redirect(url_for('receptionist.view_folio', booking_id=booking.id))

        # For POST requests, process the payment
        # Get form data
        payment_amount = request.form.get('payment_amount', type=float)
        payment_type = request.form.get('payment_type')
        reference = request.form.get('reference', '')

        # Validate input
        if not payment_amount or payment_amount <= 0:
            flash("Payment amount must be greater than zero.", "danger")
            return redirect(url_for('receptionist.process_payment', booking_id=booking.id))

        # Process the payment
        try:
            booking.record_payment(
                amount=payment_amount,
                payment_type=payment_type,
                reference=reference or f"Payment processed by {current_user.username}"
            )

            db.session.commit()

            flash(f"Payment of ${payment_amount:.2f} processed successfully.", "success")
            return redirect(url_for('receptionist.view_folio', booking_id=booking.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error processing payment: {str(e)}", "danger")
            return redirect(url_for('receptionist.process_payment', booking_id=booking.id))

    except Exception as e:
        current_app.logger.error(f"Error retrieving booking for payment: {str(e)}", exc_info=True)
        flash(f"Error retrieving booking: {str(e)}", "danger")
        return redirect(url_for('receptionist.dashboard'))


@receptionist_bp.route('/mark-room-clean/<int:room_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def mark_room_clean(room_id):
    """Mark a room as clean and available."""
    try:
        room = Room.query.get_or_404(room_id)

        if request.method == 'POST':
            # Update room status
            old_status = room.status
            room.mark_as_cleaned()

            # Log the status change
            RoomStatusLog.log_status_change(
                room_id=room.id,
                old_status=old_status,
                new_status=room.status,
                changed_by=current_user.id,
                notes=f"Marked as clean by receptionist"
            )

            db.session.commit()
            flash(f"Room {room.number} marked as clean and available.", "success")
            return redirect(url_for('receptionist.room_inventory'))

        return render_template(
            'receptionist/confirm_action.html',
            title="Mark Room as Clean",
            message=f"Are you sure you want to mark Room {room.number} as clean and available?",
            form_action=url_for('receptionist.mark_room_clean', room_id=room.id),
            return_url=url_for('receptionist.room_inventory'),
            metrics={}
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating room status: {str(e)}", "danger")
        return redirect(url_for('receptionist.room_inventory'))


@receptionist_bp.route('/mark-room-maintenance/<int:room_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def mark_room_maintenance(room_id):
    """Mark a room for maintenance."""
    try:
        room = Room.query.get_or_404(room_id)

        if request.method == 'POST':
            notes = request.form.get('notes', '')

            # Update room status
            old_status = room.status
            room.change_status(Room.STATUS_MAINTENANCE, current_user.id)

            # Log the status change
            RoomStatusLog.log_status_change(
                room_id=room.id,
                old_status=old_status,
                new_status=room.status,
                changed_by=current_user.id,
                notes=f"Marked for maintenance: {notes}"
            )

            db.session.commit()
            flash(f"Room {room.number} marked for maintenance.", "success")
            return redirect(url_for('receptionist.room_inventory'))

        return render_template(
            'receptionist/confirm_action.html',
            title="Mark Room for Maintenance",
            message=f"Are you sure you want to mark Room {room.number} for maintenance?",
            form_action=url_for('receptionist.mark_room_maintenance', room_id=room.id),
            return_url=url_for('receptionist.room_inventory'),
            show_notes=True,
            metrics={}
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating room status: {str(e)}", "danger")
        return redirect(url_for('receptionist.room_inventory'))


@receptionist_bp.route('/mark-room-available/<int:room_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def mark_room_available(room_id):
    """Mark a room as available."""
    try:
        room = Room.query.get_or_404(room_id)

        if request.method == 'POST':
            # Update room status
            old_status = room.status
            room.change_status(Room.STATUS_AVAILABLE, current_user.id)

            # Log the status change
            RoomStatusLog.log_status_change(
                room_id=room.id,
                old_status=old_status,
                new_status=room.status,
                changed_by=current_user.id,
                notes=f"Marked as available by receptionist"
            )

            db.session.commit()
            flash(f"Room {room.number} marked as available.", "success")
            return redirect(url_for('receptionist.room_inventory'))

        return render_template(
            'receptionist/confirm_action.html',
            title="Mark Room as Available",
            message=f"Are you sure you want to mark Room {room.number} as available?",
            form_action=url_for('receptionist.mark_room_available', room_id=room.id),
            return_url=url_for('receptionist.room_inventory'),
            metrics={}
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating room status: {str(e)}", "danger")
        return redirect(url_for('receptionist.room_inventory'))


@receptionist_bp.route('/room-history/<int:room_id>')
@login_required
@role_required('receptionist')
def room_history(room_id):
    """View room status history."""
    try:
        room = Room.query.get_or_404(room_id)

        # Get room status logs
        logs = RoomStatusLog.get_room_history(room.id)

        # Get bookings for this room
        bookings = Booking.query.filter_by(room_id=room.id).order_by(Booking.check_in_date.desc()).all()

        return render_template(
            'receptionist/room_history.html',
            room=room,
            logs=logs,
            bookings=bookings,
            metrics={}
        )
    except Exception as e:
        flash(f"Error retrieving room history: {str(e)}", "danger")
        return redirect(url_for('receptionist.room_inventory'))


@receptionist_bp.route('/availability-calendar')
@login_required
@role_required('receptionist')
def availability_calendar():
    """Display room availability calendar."""
    booking_service = BookingService(db.session)
    room_service = RoomService(db.session)

    # Get room types for filter
    room_types = RoomType.query.all()

    # Get date range parameters, default to next 30 days
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    room_type_id = request.args.get('room_type_id')

    # Parse date parameters or use defaults
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else (today + timedelta(days=30))

        # Validate dates (no need to restrict to today for staff)

        # Limit to reasonable range (e.g., 90 days for staff)
        if (end_date - start_date).days > 90:
            end_date = start_date + timedelta(days=90)

    except ValueError:
        # If date parsing fails, use defaults
        start_date = today
        end_date = today + timedelta(days=30)

    # Convert room_type_id to int if present
    if room_type_id and room_type_id.isdigit():
        room_type_id = int(room_type_id)
    else:
        room_type_id = None

    # Get availability data for calendar
    availability_data = booking_service.get_availability_calendar_data(
        start_date=start_date,
        end_date=end_date,
        room_type_id=room_type_id
    )

    # Add room statistics for staff view
    total_rooms = Room.query.count()
    available_today = Room.query.filter_by(status=Room.STATUS_AVAILABLE).count()
    occupied_today = Room.query.filter_by(status=Room.STATUS_OCCUPIED).count()

    # Calculate occupancy rate
    occupancy_rate = 0
    if total_rooms > 0:
        occupancy_rate = round((occupied_today / total_rooms) * 100)

    # Add room statistics to availability data
    availability_data['room_stats'] = {
        'total_rooms': total_rooms,
        'available_today': available_today,
        'occupied_today': occupied_today,
        'occupancy_rate': occupancy_rate
    }

    return render_template(
        'receptionist/availability_calendar.html',
        room_types=room_types,
        availability_data=availability_data,
        start_date=start_date,
        end_date=end_date,
        selected_room_type_id=room_type_id,
        today_str=today_str,
        metrics={}
    )