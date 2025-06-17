"""
Customer routes module.

This module defines the routes for customer operations.
"""

import stripe
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
import traceback

from db import db
from app.utils.decorators import role_required
from app.services.dashboard_service import DashboardService
from app.services.customer_service import CustomerService, DuplicateUserError
from app.services.booking_service import BookingService, RoomNotAvailableError
from app.services.room_service import RoomService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.models.customer import Customer
from app.models.room_type import RoomType
from app.models.booking import Booking
from app.models.room import Room
from app.forms.customer_forms import CustomerProfileForm
from app.forms.booking_forms import BookingForm, BookingSearchForm
from app.forms.user_forms import ChangePasswordForm
from app.services.user_service import UserService
from app.models.loyalty_reward import LoyaltyReward
from app.models.loyalty_redemption import LoyaltyRedemption
from app.utils.password_security import PasswordStrengthError, PasswordRateLimitError

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
    """Allow customer to change their password with enhanced security."""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        user_service = UserService(db.session)
        
        try:
            user_service.change_password(
                user_id=current_user.id,
                current_password=form.current_password.data,
                new_password=form.new_password.data
            )
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('customer.profile'))
            
        except PasswordStrengthError as e:
            flash(f'Password validation failed: {str(e)}', 'danger')
            
        except PasswordRateLimitError as e:
            flash(f'Security restriction: {str(e)}', 'danger')
            
        except ValueError as e:
            # Handle user not found or current password mismatch
            if "Current password does not match" in str(e):
                flash('Current password is incorrect.', 'danger')
            else:
                flash('Password change failed. Please try again.', 'danger')
                # Log the error for debugging
                current_app.logger.error(f"Password change error for user {current_user.id}: {e}")
                
        except Exception as e:
            flash('Password change failed. Please try again later.', 'danger')
            # Log unexpected errors
            current_app.logger.error(f"Unexpected password change error for user {current_user.id}: {e}")

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

    # Always use room_type_id if present (from URL or form)
    effective_room_type_id = request.form.get('room_type_id') or target_booking.room_type_id or target_booking.room.room_type_id
    if effective_room_type_id and str(effective_room_type_id).isdigit():
        available_rooms = booking_service.get_available_rooms(
            room_type_id=int(effective_room_type_id),
            check_in_date=check_in_for_avail,
            check_out_date=check_out_for_avail
        )
    else:
        available_rooms = booking_service.get_available_rooms(
            check_in_date=check_in_for_avail,
            check_out_date=check_out_for_avail
        )
    room_choices = [(r.id, f"{r.number} - {r.room_type.name} (${r.room_type.base_rate:.2f}/night)") for r in available_rooms]
    # If the selected room is not in available_rooms, add it as a disabled option
    selected_room_id = form.room_id.data
    if selected_room_id and selected_room_id not in [r.id for r in available_rooms]:
        # Try to fetch the room for display
        missing_room = Room.query.get(selected_room_id)
        if missing_room:
            room_choices = [
                (missing_room.id, f"{missing_room.number} - {missing_room.room_type.name} (Unavailable)")
            ] + room_choices
    form.room_id.choices = room_choices

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_options': # JS date change, re-evaluate rooms and price
            # Check if it's an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if form.check_in_date.data and form.check_out_date.data:
                # Use room_type_id from form or request
                update_room_type_id = request.form.get('room_type_id') or target_booking.room_type_id or target_booking.room.room_type_id
                if update_room_type_id and str(update_room_type_id).isdigit():
                    available_rooms = booking_service.get_available_rooms(
                        room_type_id=int(update_room_type_id),
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data
                    )
                else:
                    available_rooms = booking_service.get_available_rooms(
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data
                    )
                # Update room choices
                room_choices = [(r.id, f"{r.number} - {r.room_type.name}") for r in available_rooms]

                # Calculate price if room is selected
                if form.room_id.data:
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

            # No validation, just re-render template with updated room list and possibly price
            return render_template(
                'customer/edit_booking.html',
                form=form,
                booking=target_booking,
                room_types=room_types,
                estimated_price=estimated_price
            )

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
    tier_benefits = customer_service.get_tier_benefits(customer.loyalty_tier)
    tier_progress = customer_service.get_tier_progress(customer.id)

    return render_template('customer/loyalty_history.html',
                           customer=customer,
                           history=history,
                           tier_benefits=tier_benefits,
                           tier_progress=tier_progress)


@customer_bp.route('/profile/loyalty/rewards')
@login_required
@role_required('customer')
def loyalty_rewards():
    """Display available loyalty rewards for redemption."""
    customer_service = CustomerService(db.session)
    customer = customer_service.get_customer_by_user_id(current_user.id)

    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('customer.dashboard'))

    # Get category filter if provided
    category = request.args.get('category')
    
    # Get available rewards
    rewards = customer_service.get_available_rewards(customer.id, category)
    
    # Get reward categories for filter
    categories = [
        {'id': 'all', 'name': 'All Rewards'},
        {'id': LoyaltyReward.CATEGORY_ROOM, 'name': 'Room Upgrades'},
        {'id': LoyaltyReward.CATEGORY_DINING, 'name': 'Dining'},
        {'id': LoyaltyReward.CATEGORY_SPA, 'name': 'Spa Services'},
        {'id': LoyaltyReward.CATEGORY_AMENITY, 'name': 'Amenities'},
        {'id': LoyaltyReward.CATEGORY_SERVICE, 'name': 'Premium Services'},
        {'id': LoyaltyReward.CATEGORY_OTHER, 'name': 'Other Rewards'}
    ]
    
    # Get customer redemptions
    redemptions = customer_service.get_customer_redemptions(customer.id, limit=5)

    return render_template('customer/loyalty_rewards.html',
                           customer=customer,
                           rewards=rewards,
                           categories=categories,
                           selected_category=category or 'all',
                           redemptions=redemptions)


@customer_bp.route('/profile/loyalty/rewards/<int:reward_id>')
@login_required
@role_required('customer')
def loyalty_reward_detail(reward_id):
    """Display loyalty reward details."""
    customer_service = CustomerService(db.session)
    customer = customer_service.get_customer_by_user_id(current_user.id)

    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    # Get reward
    reward = LoyaltyReward.query.get_or_404(reward_id)
    
    # Check if reward is available to this customer
    is_available = reward.is_available_for_customer(customer)
    
    # Get customer's upcoming bookings for potential association
    bookings = customer.get_upcoming_bookings()

    return render_template('customer/loyalty_reward_detail.html',
                           customer=customer,
                           reward=reward,
                           is_available=is_available,
                           bookings=bookings)


@customer_bp.route('/profile/loyalty/redeem/<int:reward_id>', methods=['POST'])
@login_required
@role_required('customer')
def redeem_reward(reward_id):
    """Redeem a loyalty reward."""
    customer_service = CustomerService(db.session)
    customer = customer_service.get_customer_by_user_id(current_user.id)

    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    # Get booking ID if provided
    booking_id = request.form.get('booking_id', type=int)
    notes = request.form.get('notes')
    
    try:
        # Redeem reward
        redemption = customer_service.redeem_reward(customer.id, reward_id, booking_id, notes)
        
        flash(f'You have successfully redeemed the reward. Your request is being processed.', 'success')
    except InsufficientPointsError:
        flash('You do not have enough points to redeem this reward.', 'danger')
    except RewardNotAvailableError:
        flash('This reward is not available to you.', 'danger')
    except ValueError as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('customer.loyalty_redemptions'))


@customer_bp.route('/profile/loyalty/redemptions')
@login_required
@role_required('customer')
def loyalty_redemptions():
    """Display customer's loyalty reward redemptions."""
    customer_service = CustomerService(db.session)
    customer = customer_service.get_customer_by_user_id(current_user.id)

    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    # Get status filter if provided
    status = request.args.get('status')
    
    # Get redemptions
    redemptions = customer_service.get_customer_redemptions(customer.id, status)

    return render_template('customer/loyalty_redemptions.html',
                           customer=customer,
                           redemptions=redemptions,
                           selected_status=status or 'all')


@customer_bp.route('/profile/loyalty/redemptions/<int:redemption_id>/cancel', methods=['POST'])
@login_required
@role_required('customer')
def cancel_redemption(redemption_id):
    """Cancel a pending loyalty reward redemption."""
    redemption = LoyaltyRedemption.query.get_or_404(redemption_id)
    
    # Verify ownership
    if redemption.customer_id != current_user.customer_profile.id:
        abort(403)
    
    try:
        # Cancel redemption
        reason = request.form.get('reason')
        redemption.cancel(reason)
        db.session.commit()
        
        flash('Your redemption has been cancelled and your points have been refunded.', 'success')
    except ValueError as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('customer.loyalty_redemptions'))


@customer_bp.route('/profile/loyalty/tier-benefits')
@login_required
@role_required('customer')
def tier_benefits():
    """Display loyalty tier benefits comparison."""
    customer_service = CustomerService(db.session)
    customer = customer_service.get_customer_by_user_id(current_user.id)

    if not customer:
        flash('Customer profile not found.', 'danger')
        return redirect(url_for('customer.dashboard'))
    
    # Get benefits for all tiers
    standard_benefits = customer_service.get_tier_benefits(Customer.TIER_STANDARD)
    silver_benefits = customer_service.get_tier_benefits(Customer.TIER_SILVER)
    gold_benefits = customer_service.get_tier_benefits(Customer.TIER_GOLD)
    platinum_benefits = customer_service.get_tier_benefits(Customer.TIER_PLATINUM)
    
    tier_progress = customer_service.get_tier_progress(customer.id)

    return render_template('customer/tier_benefits.html',
                           customer=customer,
                           standard_benefits=standard_benefits,
                           silver_benefits=silver_benefits,
                           gold_benefits=gold_benefits,
                           platinum_benefits=platinum_benefits,
                           tier_progress=tier_progress)


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

    # Get parameters from URL if provided
    room_type_id = request.args.get('room_type_id')
    check_in_date_str = request.args.get('check_in_date')
    check_out_date_str = request.args.get('check_out_date')

    # Determine dates for availability check and form defaults
    default_check_in = datetime.now().date()
    default_check_out = default_check_in + timedelta(days=1)

    # Parse date parameters if provided
    try:
        if check_in_date_str:
            default_check_in = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
        if check_out_date_str:
            default_check_out = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()

        # Validate dates
        if default_check_in < datetime.now().date():
            default_check_in = datetime.now().date()
        if default_check_out <= default_check_in:
            default_check_out = default_check_in + timedelta(days=1)
    except ValueError:
        # If date parsing fails, use defaults
        pass

    check_in_for_avail = form.check_in_date.data if form.check_in_date.data else default_check_in
    check_out_for_avail = form.check_out_date.data if form.check_out_date.data else default_check_out

    # Populate room choices
    # Always use room_type_id if present (from URL or form)
    effective_room_type_id = room_type_id or form.room_id.data or request.form.get('room_type_id')
    if effective_room_type_id and str(effective_room_type_id).isdigit():
        available_rooms = booking_service.get_available_rooms(
            room_type_id=int(effective_room_type_id),
            check_in_date=check_in_for_avail,
            check_out_date=check_out_for_avail
        )
    else:
        available_rooms = booking_service.get_available_rooms(
            check_in_date=check_in_for_avail,
            check_out_date=check_out_for_avail
        )
    room_choices = [(r.id, f"{r.number} - {r.room_type.name} (${r.room_type.base_rate:.2f}/night)") for r in available_rooms]
    # If the selected room is not in available_rooms, add it as a disabled option
    selected_room_id = form.room_id.data
    if selected_room_id and selected_room_id not in [r.id for r in available_rooms]:
        # Try to fetch the room for display
        missing_room = Room.query.get(selected_room_id)
        if missing_room:
            room_choices = [
                (missing_room.id, f"{missing_room.number} - {missing_room.room_type.name} (Unavailable)")
            ] + room_choices
    form.room_id.choices = room_choices

    if request.method == 'POST':
        # If only updating options (e.g., date change from JS)
        if request.form.get('action') == 'update_options':
            # Check if it's an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if form.check_in_date.data and form.check_out_date.data:
                # Use room_type_id from form or request
                update_room_type_id = request.form.get('room_type_id') or room_type_id
                if update_room_type_id and str(update_room_type_id).isdigit():
                    available_rooms = booking_service.get_available_rooms(
                        room_type_id=int(update_room_type_id),
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data
                    )
                else:
                    available_rooms = booking_service.get_available_rooms(
                        check_in_date=form.check_in_date.data,
                        check_out_date=form.check_out_date.data
                    )
                # Update room choices
                room_choices = [(r.id, f"{r.number} - {r.room_type.name}") for r in available_rooms]

                # Calculate price if room is selected
                if form.room_id.data:
                    try:
                        estimated_price = booking_service.calculate_booking_price(
                            room_id=int(form.room_id.data),
                            check_in_date=form.check_in_date.data,
                            check_out_date=form.check_out_date.data,
                            early_hours=form.early_hours.data or 0,
                            late_hours=form.late_hours.data or 0
                        )
                    except ValueError:
                        if is_ajax:
                            return jsonify({
                                'success': False,
                                'error': str(e)
                            })
                        flash(f"Could not estimate price: {e}", 'warning')

                # If AJAX request, return JSON response
                if is_ajax:
                    room_options = []
                    for room in available_rooms:
                        # Get amenities as a list if available
                        amenities_list = []
                        if hasattr(room.room_type, 'amenities') and room.room_type.amenities:
                            if isinstance(room.room_type.amenities, list):
                                amenities_list = room.room_type.amenities
                            elif isinstance(room.room_type.amenities, str):
                                amenities_list = [a.strip() for a in room.room_type.amenities.split(',')]

                        # Create room option with detailed information
                        room_option = {
                            'value': room.id,
                            'text': f"Room {room.number} - {room.room_type.name}",
                            'room_number': room.number,
                            'room_type': room.room_type.name,
                            'capacity': room.room_type.capacity,
                            'rate': room.room_type.base_rate,
                            'amenities': amenities_list,
                            'description': room.room_type.description,
                            'size_sqm': getattr(room.room_type, 'size_sqm', None),
                            'bed_type': getattr(room.room_type, 'bed_type', None),
                            'has_view': getattr(room.room_type, 'has_view', False),
                            'has_balcony': getattr(room.room_type, 'has_balcony', False)
                        }

                        # Add image URL if available
                        if hasattr(room.room_type, 'image_main') and room.room_type.image_main:
                            room_option['image_url'] = room.room_type.image_main

                        room_options.append(room_option)

                    return jsonify({
                        'success': True,
                        'room_options': room_options,
                        'estimated_price': estimated_price
                    })

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

                # Send confirmation email (would be implemented in a real system)
                # email_service.send_booking_confirmation(booking)

                # Create a notification for the customer
                try:
                    notification_service = NotificationService(db.session)
                    notification_service.create_notification(
                        user_id=current_user.id,
                        message=f"Your booking #{booking.confirmation_code} has been confirmed.",
                        type='booking_confirmation',
                        link_url=url_for('customer.booking_confirmation', booking_id=booking.id),
                        priority='normal',
                        category='booking',
                        channels='web',
                        related_entity_type='booking',
                        related_entity_id=booking.id
                    )
                except Exception as notification_error:
                    # Log the notification error but don't fail the booking
                    current_app.logger.error(f"Failed to create notification: {notification_error}")
                    # Don't re-raise as the booking was successful

                flash('Your booking has been created successfully! Confirmation # {}'.format(booking.confirmation_code or booking.id), 'success')
                return redirect(url_for('customer.booking_confirmation', booking_id=booking.id))
            except RoomNotAvailableError as e:
                flash(str(e), 'danger')
            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                # Enable proper error logging to debug the issue
                import traceback
                error_details = traceback.format_exc()
                print(f"Booking creation error: {str(e)}")
                print(f"Error details: {error_details}")
                
                # More descriptive error message
                flash(f'An unexpected error occurred: {str(e)}. Please try again or contact support.', 'danger')
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
    
    # Debug - print the form data
    if request.method == 'POST' and form.is_submitted():
        print(f"Form data: customer_id={form.customer_id.data}, status={form.status.data}, room_id={form.room_id.data}, " +
              f"check_in={form.check_in_date.data}, check_out={form.check_out_date.data}, num_guests={form.num_guests.data}")

    return render_template(
        'customer/new_booking.html',
        form=form,
        room_types=room_types,
        estimated_price=estimated_price
    )


@customer_bp.route('/booking-confirmation/<int:booking_id>')
@login_required
@role_required('customer')
def booking_confirmation(booking_id):
    """Display booking confirmation page."""
    # Get the booking
    booking = db.session.query(Booking).get(booking_id)

    # Check if booking exists and belongs to the current user
    if not booking or booking.customer.user_id != current_user.id:
        flash('Booking not found or access denied.', 'danger')
        return redirect(url_for('customer.bookings'))

    return render_template('customer/booking_confirmation.html', booking=booking)


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

@customer_bp.route('/room-types')
@login_required
@role_required('customer')
def room_types():
    """Display room types with filtering and availability checking."""
    # Get filter parameters
    capacity = request.args.get('capacity')
    price_range = request.args.get('price_range')
    amenities = request.args.get('amenities')

    # Get date parameters for availability check
    check_in_date_str = request.args.get('check_in_date')
    check_out_date_str = request.args.get('check_out_date')

    # Parse date parameters or use defaults
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    today_str = today.strftime('%Y-%m-%d')
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')

    try:
        check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date() if check_in_date_str else today
        check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date() if check_out_date_str else tomorrow

        # Validate dates
        if check_in_date < today:
            check_in_date = today
        if check_out_date <= check_in_date:
            check_out_date = check_in_date + timedelta(days=1)
    except ValueError:
        # If date parsing fails, use defaults
        check_in_date = today
        check_out_date = tomorrow

    # Query room types with filters
    query = RoomType.query

    if capacity and capacity.isdigit():
        query = query.filter(RoomType.capacity >= int(capacity))

    if price_range:
        if price_range == 'economy':
            query = query.filter(RoomType.base_rate < 100)
        elif price_range == 'standard':
            query = query.filter(RoomType.base_rate >= 100, RoomType.base_rate < 200)
        elif price_range == 'premium':
            query = query.filter(RoomType.base_rate >= 200, RoomType.base_rate < 300)
        elif price_range == 'luxury':
            query = query.filter(RoomType.base_rate >= 300)

    if amenities:
        if amenities == 'view':
            query = query.filter(RoomType.has_view == True)
        elif amenities == 'balcony':
            query = query.filter(RoomType.has_balcony == True)

    room_types = query.all()

    # Check availability for each room type
    availability = {}
    if check_in_date and check_out_date:
        for rt in room_types:
            # Count rooms of this type
            total_rooms = db.session.query(db.func.count(Room.id)).filter(Room.room_type_id == rt.id).scalar()

            # Count booked rooms of this type for the date range
            booked_rooms = db.session.query(db.func.count(Booking.id)).join(Room).filter(
                Room.room_type_id == rt.id,
                Booking.status.in_([Booking.STATUS_RESERVED, Booking.STATUS_CHECKED_IN]),
                Booking.check_in_date < check_out_date,
                Booking.check_out_date > check_in_date
            ).scalar()

            # Calculate available rooms
            available_rooms = max(0, total_rooms - booked_rooms)
            availability[rt.id] = available_rooms

    return render_template(
        'customer/room_types.html',
        room_types=room_types,
        availability=availability,
        today_str=today_str,
        tomorrow_str=tomorrow_str
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


@customer_bp.route('/payment/success')
@login_required
@role_required('customer')
def payment_success():
    """Handle successful payment."""
    session_id = request.args.get('session_id')

    if not session_id:
        flash("Invalid payment session.", "danger")
        return redirect(url_for('customer.bookings'))

    try:
        # Retrieve the session to get booking details
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        session = stripe.checkout.Session.retrieve(session_id)
        booking_id = session.metadata.get('booking_id')

        if not booking_id:
            flash("Booking information not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Get the booking
        booking = db.session.query(Booking).get(int(booking_id))
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Show success page
        return render_template(
            'payment/success.html',
            booking=booking,
            payment_intent_id=session.payment_intent
        )
    except Exception as e:
        current_app.logger.error(f"Payment success error: {str(e)}")
        flash("An unexpected error occurred.", "danger")
        return redirect(url_for('customer.bookings'))


@customer_bp.route('/payment/cancel')
@login_required
@role_required('customer')
def payment_cancel():
    """Handle cancelled payment."""
    session_id = request.args.get('session_id')

    if not session_id:
        flash("Invalid payment session.", "danger")
        return redirect(url_for('customer.bookings'))

    try:
        # Retrieve the session to get booking details
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        session = stripe.checkout.Session.retrieve(session_id)
        booking_id = session.metadata.get('booking_id')

        if not booking_id:
            flash("Booking information not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Get the booking
        booking = db.session.query(Booking).get(int(booking_id))
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for('customer.bookings'))

        # Show cancel page
        return render_template(
            'payment/cancel.html',
            booking=booking
        )
    except Exception as e:
        current_app.logger.error(f"Payment cancel error: {str(e)}")
        flash("An unexpected error occurred.", "danger")
        return redirect(url_for('customer.bookings'))


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