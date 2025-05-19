"""
Customer routes module.

This module defines the routes for customer operations.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
import traceback

from db import db
from app.utils.decorators import role_required
from app.services.dashboard_service import DashboardService
from app.services.customer_service import CustomerService, DuplicateUserError
from app.services.booking_service import BookingService, RoomNotAvailableError
from app.services.room_service import RoomService
from app.services.notification_service import NotificationService
from app.models.customer import Customer
from app.models.room_type import RoomType
from app.forms.customer_forms import CustomerProfileForm
from app.forms.booking_forms import BookingForm, BookingSearchForm
from app.forms.user_forms import ChangePasswordForm
from app.services.user_service import UserService

# Create blueprint
customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
@role_required('customer')
def dashboard():
    """Display customer dashboard."""
    # Get customer dashboard metrics
    try:
        # Initialize the dashboard service with a db session
        dashboard_service = DashboardService(db.session)
        metrics = dashboard_service.get_customer_metrics(current_user.id)
        # Ensure metrics is a dict even if service returns None or error string sometimes
        if not isinstance(metrics, dict):
            # Log this unexpected return type from service
            # current_app.logger.error(f"DashboardService.get_customer_metrics returned non-dict: {metrics}")
            raise ValueError("Invalid data received from dashboard service.")

        return render_template('customer/dashboard.html', metrics=metrics)
    except Exception as e:
        # Log the real error and traceback for debugging
        print("DASHBOARD ERROR:", e)
        traceback.print_exc()
        # Provide a more complete error_metrics dictionary with defaults
        error_metrics = {
            "error": f"Error loading dashboard data: {str(e)}",
            "customer_name": "N/A",
            "profile_status": "Unknown",
            "active_booking": None,
            "upcoming_bookings": [],
            "past_bookings": [],
            "booking_count": 0,
            "loyalty_points": 0,
            "loyalty_tier": "N/A",
            "unread_notification_count": 0 # Default for the problematic key
        }
        return render_template('customer/dashboard.html', metrics=error_metrics)


@customer_bp.route('/bookings')
@login_required
@role_required('customer')
def bookings():
    """Manage bookings."""
    customer_service = CustomerService(db.session)
    booking_service = BookingService(db.session)
    
    # Get customer profile
    customer = customer_service.get_customer_by_user_id(current_user.id)
    
    if not customer:
        flash('Please complete your profile before managing bookings.', 'warning')
        return redirect(url_for('customer.profile'))
    
    # Get customer's bookings
    bookings = booking_service.get_bookings_by_customer(customer.id)
    
    return render_template('customer/bookings.html', bookings=bookings)


@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def profile():
    """View and edit customer profile."""
    customer_service = CustomerService(db.session)
    
    # Get customer profile or create new one if it doesn't exist
    customer = customer_service.get_customer_by_user_id(current_user.id)
    
    if not customer:
        try:
            customer = customer_service.create_customer(user_id=current_user.id)
        except (ValueError, DuplicateUserError) as e:
            flash(str(e), 'danger')
            return redirect(url_for('customer.dashboard'))
    
    form = CustomerProfileForm()
    
    if request.method == 'GET':
        # Populate form with existing data
        if customer:
            form.name.data = customer.name
            form.phone.data = customer.phone
            form.address.data = customer.address
            form.emergency_contact.data = customer.emergency_contact
    
    if form.validate_on_submit():
        try:
            # Update customer with form data
            customer_service.update_customer(
                customer_id=customer.id,
                name=form.name.data,
                phone=form.phone.data,
                address=form.address.data,
                emergency_contact=form.emergency_contact.data
            )
            
            flash('Your profile has been updated successfully.', 'success')
            return redirect(url_for('customer.dashboard'))
        
        except ValueError as e:
            flash(str(e), 'danger')
    
    return render_template('customer/profile.html', form=form, customer=customer)


@customer_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def change_password():
    """Allow customer to change their password."""
    form = ChangePasswordForm()
    user_service = UserService(db.session)

    if form.validate_on_submit():
        try:
            user_service.change_password(
                user_id=current_user.id,
                current_password=form.current_password.data,
                new_password=form.new_password.data
            )
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('customer.profile'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            # Log general errors for debugging
            # current_app.logger.error(f"Password change error for user {current_user.id}: {e}")
            flash('An unexpected error occurred. Please try again.', 'danger')
            
    return render_template('customer/change_password.html', form=form)


@customer_bp.route('/bookings/<int:booking_id>/details')
@login_required
@role_required('customer')
def booking_details(booking_id):
    """Display details for a specific booking."""
    booking_service = BookingService(db.session)
    # Fetch the booking ensuring it belongs to the current customer
    booking = booking_service.get_booking_by_id_and_customer(
        booking_id=booking_id, 
        customer_id=current_user.customer_profile.id # Corrected from current_user.customer.id
    )

    if not booking:
        flash('Booking not found or access denied.', 'danger')
        return redirect(url_for('customer.bookings'))

    # Payments are accessed via booking.payments (backref)
    # FolioItems would be similar if the model existed (e.g., booking.folio_items)
    
    return render_template('customer/booking_details.html', booking=booking)


@customer_bp.route('/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def edit_booking(booking_id):
    """Allow customer to edit their booking."""
    booking_service = BookingService(db.session)
    target_booking = booking_service.get_booking_by_id_and_customer(booking_id, current_user.customer_profile.id)

    if not target_booking:
        flash('Booking not found or you do not have permission to edit it.', 'danger')
        return redirect(url_for('customer.bookings'))

    if target_booking.status != Booking.STATUS_RESERVED:
        flash(f'This booking cannot be edited as its status is "{target_booking.status}".', 'warning')
        return redirect(url_for('customer.booking_details', booking_id=booking_id))

    form = BookingForm(request.form if request.method == 'POST' else None, obj=target_booking)
    # Populate special_requests manually as it's a TextArea for a list in the model
    if request.method == 'GET' and target_booking.special_requests:
        form.special_requests.data = '\n'.join(target_booking.special_requests)
        
    room_types = RoomType.query.all() # For informational display, or if room type change is allowed
    estimated_price = target_booking.total_price # Initial estimated price is current total price

    # Populate room choices for the booking's current dates initially, or new dates if POSTing for update
    check_in_for_avail = form.check_in_date.data if form.check_in_date.data else target_booking.check_in_date
    check_out_for_avail = form.check_out_date.data if form.check_out_date.data else target_booking.check_out_date
    
    available_rooms = booking_service.get_available_rooms(
        check_in_date=check_in_for_avail,
        check_out_date=check_out_for_avail
    )
    # Ensure current room is in choices if still valid, or add it
    current_room_choice = (target_booking.room_id, f"{target_booking.room.number} - {target_booking.room.room_type.name} (${target_booking.room.room_type.base_rate:.2f}/night) (Current)")
    form.room_id.choices = [(r.id, f"{r.number} - {r.room_type.name} (${r.room_type.base_rate:.2f}/night)") for r in available_rooms if r.id != target_booking.room_id]
    form.room_id.choices.insert(0, current_room_choice) # Add current room to top
    # If current room is not in available_rooms (e.g. if user changed dates and current room became unavailable),
    # it will still be listed, but check_room_availability in update_booking will handle it if selected with incompatible dates.

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_options': # JS date change, re-evaluate rooms and price
            # Repopulate choices based on potentially new dates from form
            new_available_rooms = booking_service.get_available_rooms(check_in_date=form.check_in_date.data, check_out_date=form.check_out_date.data)
            form.room_id.choices = [(r.id, f"{r.number} - {r.room_type.name} (${r.room_type.base_rate:.2f}/night)") for r in new_available_rooms]
            # Attempt to keep selected room if still available, or default
            if form.room_id.data and any(rc[0] == int(form.room_id.data) for rc in form.room_id.choices):
                pass # Keep current selection
            elif form.room_id.choices: # Default to first available if previous selection is gone
                form.room_id.data = str(form.room_id.choices[0][0])
            else: # No rooms available for new dates
                form.room_id.data = None
            
            if form.room_id.data and form.check_in_date.data and form.check_out_date.data:
                try:
                    estimated_price = booking_service.calculate_booking_price(
                        room_id=int(form.room_id.data),
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data,
                        early_hours=form.early_hours.data or 0,
                        late_hours=form.late_hours.data or 0
                    )
                except ValueError:
                    estimated_price = None # Could not estimate
            return render_template('customer/edit_booking.html', form=form, booking=target_booking, room_types=room_types, estimated_price=estimated_price)

        # Actual edit submission
        if form.validate_on_submit():
            try:
                updated_booking = booking_service.update_booking(
                    booking_id=booking_id,
                    room_id=form.room_id.data,
                    check_in_date=form.check_in_date.data,
                    check_out_date=form.check_out_date.data,
                    num_guests=form.num_guests.data,
                    special_requests=form.special_requests.data,
                    early_hours=form.early_hours.data or 0,
                    late_hours=form.late_hours.data or 0
                    # status is not changed by customer edit
                )
                flash('Booking updated successfully!', 'success')
                return redirect(url_for('customer.booking_details', booking_id=updated_booking.id))
            except (RoomNotAvailableError, ValueError) as e:
                flash(str(e), 'danger')
            except Exception as e:
                # current_app.logger.error(f"Booking update error: {e}")
                flash('An unexpected error occurred while updating your booking.', 'danger')
        else: # Form validation failed on POST
             if form.room_id.data and form.check_in_date.data and form.check_out_date.data:
                try:
                    estimated_price = booking_service.calculate_booking_price(
                        room_id=int(form.room_id.data),
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data,
                        early_hours=form.early_hours.data or 0,
                        late_hours=form.late_hours.data or 0
                    )
                except ValueError:
                    pass # Error already on form or handled by validation
                    
    # For GET request, set initial form data from the booking object
    if request.method == 'GET':
        form.room_id.data = str(target_booking.room_id) # Set current room as selected
        form.num_guests.data = target_booking.num_guests
        form.early_hours.data = target_booking.early_hours
        form.late_hours.data = target_booking.late_hours

    # Ensure status is not editable by customer for safety
    form.status.data = target_booking.status 

    return render_template('customer/edit_booking.html', form=form, booking=target_booking, room_types=room_types, estimated_price=estimated_price)


@customer_bp.route('/profile/loyalty')
@login_required
@role_required('customer')
def loyalty_history():
    """Display customer's loyalty point history."""
    customer_service = CustomerService(db.session)
    customer = customer_service.get_customer_by_user_id(current_user.id)

    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('customer.dashboard'))

    history = customer_service.get_loyalty_history(customer.id)
    
    return render_template('customer/loyalty_history.html', 
                           customer=customer, 
                           history=history)


@customer_bp.route('/notifications')
@login_required
@role_required('customer')
def notifications_list():
    """Display user's notifications."""
    notification_service = NotificationService(db.session)
    # Fetch unread notifications by default, can be expanded with filters (all, unread, read)
    user_notifications = notification_service.get_user_notifications(current_user.id, limit=50, include_read=True)
    unread_count = notification_service.get_unread_notification_count(current_user.id)
    
    # Example: Mark all as read when page is viewed - or do this via a button click
    # notification_service.mark_all_notifications_as_read(current_user.id)
    # flash(f"Marked {unread_count} notifications as read.", "info")

    return render_template('customer/notifications.html', 
                           notifications=user_notifications,
                           unread_count=unread_count)

@customer_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_one_notification_read(notification_id):
    """Mark a single notification as read."""
    notification_service = NotificationService(db.session)
    notification = notification_service.mark_notification_as_read(notification_id, current_user.id)
    if notification:
        flash("Notification marked as read.", "success")
    else:
        flash("Failed to mark notification as read or notification not found.", "danger")
    return redirect(request.referrer or url_for('customer.notifications_list'))

@customer_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_customer_notifications_read():
    """Mark all of current user's notifications as read."""
    notification_service = NotificationService(db.session)
    count = notification_service.mark_all_notifications_as_read(current_user.id)
    flash(f"{count} notification(s) marked as read.", "success")
    return redirect(request.referrer or url_for('customer.notifications_list'))


@customer_bp.route('/new-booking', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def new_booking():
    """Create a new booking."""
    customer_service = CustomerService(db.session)
    booking_service = BookingService(db.session)
    # room_service = RoomService(db.session) # Not directly used, BookingService handles room info
    
    customer = customer_service.get_customer_by_user_id(current_user.id)
    if not customer or not customer.profile_complete:
        flash('Please complete your profile before making a booking.', 'warning')
        return redirect(url_for('customer.profile'))
    
    form = BookingForm(request.form if request.method == 'POST' else None) # Populate from request.form on POST
    room_types = RoomType.query.all()
    estimated_price = None

    # Determine dates for availability check and form defaults
    default_check_in = datetime.now().date()
    default_check_out = default_check_in + timedelta(days=1)

    check_in_for_avail = form.check_in_date.data if form.check_in_date.data else default_check_in
    check_out_for_avail = form.check_out_date.data if form.check_out_date.data else default_check_out

    # Populate room choices
    available_rooms = booking_service.get_available_rooms(
        check_in_date=check_in_for_avail,
        check_out_date=check_out_for_avail
    )
    form.room_id.choices = [(r.id, f"{r.number} - {r.room_type.name} (${r.room_type.base_rate:.2f}/night)") for r in available_rooms]

    if request.method == 'POST':
        # If only updating options (e.g., date change from JS)
        if request.form.get('action') == 'update_options':
            if form.room_id.data and form.check_in_date.data and form.check_out_date.data:
                try:
                    estimated_price = booking_service.calculate_booking_price(
                        room_id=int(form.room_id.data),
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data,
                        early_hours=form.early_hours.data or 0,
                        late_hours=form.late_hours.data or 0
                    )
                except ValueError as e:
                    flash(f"Could not estimate price: {e}", 'warning')
            # No validation, just re-render template with updated room list and possibly price
            return render_template(
                'customer/new_booking.html',
                form=form,
                room_types=room_types,
                estimated_price=estimated_price
            )

        # Actual booking submission
        if form.validate_on_submit():
            try:
                booking = booking_service.create_booking(
                    room_id=form.room_id.data,
                    customer_id=customer.id,
                    check_in_date=form.check_in_date.data,
                    check_out_date=form.check_out_date.data,
                    status='Reserved', # Status is fixed for customer new booking
                    num_guests=form.num_guests.data,
                    special_requests=form.special_requests.data, # Pass as string
                    early_hours=form.early_hours.data or 0,
                    late_hours=form.late_hours.data or 0
                )
                flash('Your booking has been created successfully! Confirmation # {}'.format(booking.confirmation_code or booking.id), 'success')
                return redirect(url_for('customer.bookings'))
            except RoomNotAvailableError as e:
                flash(str(e), 'danger')
            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                # current_app.logger.error(f"Booking creation error: {e}")
                flash('An unexpected error occurred while creating your booking. Please try again.', 'danger')
        else:
            # Form validation failed, try to estimate price if possible
            if form.room_id.data and form.check_in_date.data and form.check_out_date.data:
                try:
                    estimated_price = booking_service.calculate_booking_price(
                        room_id=int(form.room_id.data),
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data,
                        early_hours=form.early_hours.data or 0,
                        late_hours=form.late_hours.data or 0
                    )
                except ValueError:
                    pass # Don't flash error here, form errors are primary

    # For GET requests or if POST validation failed
    if request.method == 'GET':
        form.check_in_date.data = default_check_in
        form.check_out_date.data = default_check_out
        form.num_guests.data = 1 # Default to 1 guest

    form.customer_id.data = customer.id
    form.status.data = 'Reserved' # Ensure status is correctly set for template if hidden

    return render_template(
        'customer/new_booking.html',
        form=form,
        room_types=room_types,
        estimated_price=estimated_price
    )


@customer_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
@role_required('customer')
def cancel_booking(booking_id):
    """Cancel a booking."""
    booking_service = BookingService(db.session)
    
    try:
        booking = booking_service.cancel_booking(booking_id)
        flash(f'Booking for room {booking.room.number} has been cancelled.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('customer.bookings'))

@customer_bp.route('/availability-calendar')
@login_required
@role_required('customer')
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
        
        # Validate dates
        if start_date < today:
            start_date = today
        
        # Limit to reasonable range (e.g., 60 days)
        if (end_date - start_date).days > 60:
            end_date = start_date + timedelta(days=60)
            
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
    
    return render_template(
        'customer/availability_calendar.html',
        room_types=room_types,
        availability_data=availability_data,
        start_date=start_date,
        end_date=end_date,
        selected_room_type_id=room_type_id,
        today_str=today_str
    )

@customer_bp.route('/help')
@login_required
@role_required('customer')
def help_page():
    """Display help and FAQ page."""
    # Get common FAQs or help topics
    faqs = [
        {
            "question": "How do I modify my booking?",
            "answer": "To modify an existing booking, go to 'My Bookings', find your booking, and click the 'Edit' button. You can change dates, room type, and special requests as long as the booking status is 'Reserved'."
        },
        {
            "question": "What is the check-in/check-out time?",
            "answer": "Standard check-in time is 3:00 PM. Standard check-out time is 11:00 AM. Early check-in or late check-out may be available for an additional fee."
        },
        {
            "question": "How does the loyalty program work?",
            "answer": "You earn points for each night stayed. Points can be redeemed for room upgrades, free nights, or other perks. Visit 'My Profile' > 'Loyalty History' to see your current status and point balance."
        },
        {
            "question": "Is Wi-Fi available?",
            "answer": "Yes, complimentary high-speed Wi-Fi is available throughout the hotel for all guests."
        },
        {
            "question": "What amenities are available?",
            "answer": "Horizon Hotel offers 24/7 room service, concierge assistance, free Wi-Fi, a fitness center, spa, and pool access."
        },
        {
            "question": "How do I contact the hotel?",
            "answer": "For immediate assistance, please call our front desk at +1-555-1234-5678 or email us at contact@horizonhotel.com."
        }
    ]
    
    # Get hotel contact information
    contact_info = {
        "phone": "+1-555-1234-5678",
        "email": "contact@horizonhotel.com",
        "address": "123 Horizon Blvd, Seaside, CA 94955"
    }
    
    return render_template('customer/help.html', faqs=faqs, contact_info=contact_info)


@customer_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def feedback():
    """Submit and view customer feedback."""
    # Initialize a simple form for feedback
    from flask_wtf import FlaskForm
    from wtforms import TextAreaField, SelectField, SubmitField
    from wtforms.validators import DataRequired, Length
    
    class FeedbackForm(FlaskForm):
        """Form for customer feedback."""
        category = SelectField('Category', choices=[
            ('general', 'General Feedback'),
            ('service', 'Service Quality'),
            ('amenities', 'Hotel Amenities'),
            ('cleanliness', 'Cleanliness'),
            ('suggestion', 'Suggestion for Improvement')
        ], validators=[DataRequired()])
        message = TextAreaField('Your Feedback', validators=[
            DataRequired(),
            Length(min=10, max=1000)
        ])
        submit = SubmitField('Submit Feedback')
    
    # Create a feedback model in-memory (in a real application, you'd want to save this to the database)
    class Feedback:
        """Simple in-memory feedback model."""
        def __init__(self, user_id, category, message):
            self.id = hash(f"{user_id}-{category}-{datetime.now().isoformat()}")
            self.user_id = user_id
            self.category = category
            self.message = message
            self.created_at = datetime.now()
            self.status = 'Submitted'  # Submitted, In Review, Responded
    
    # Get user's previous feedback (for demonstration; in a real app, you'd fetch from database)
    # In a real implementation, you would store feedback in the database and retrieve it
    if not hasattr(current_user, '_feedback'):
        current_user._feedback = []
    
    form = FeedbackForm()
    
    if form.validate_on_submit():
        # Create and store new feedback
        new_feedback = Feedback(
            user_id=current_user.id,
            category=form.category.data,
            message=form.message.data
        )
        current_user._feedback.append(new_feedback)
        
        # In a real app, you'd save to database here
        # db.session.add(new_feedback)
        # db.session.commit()
        
        # Notify staff about new feedback
        # notification_service = NotificationService(db.session)
        # notification_service.create_notification(
        #     recipient_id=staff_id, 
        #     type='feedback', 
        #     content=f"New feedback received from {current_user.username}",
        #     related_id=new_feedback.id
        # )
        
        flash('Thank you for your feedback! We value your opinion.', 'success')
        return redirect(url_for('customer.feedback'))
    
    # Get all feedback for this user, sorted by most recent first
    user_feedback = sorted(
        current_user._feedback, 
        key=lambda f: f.created_at, 
        reverse=True
    )
    
    return render_template('customer/feedback.html', form=form, feedback_list=user_feedback) 