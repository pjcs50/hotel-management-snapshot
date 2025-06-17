from datetime import datetime
from app.models import Booking
from db import db

def auto_check_out_overdue():
    """Automatically check out bookings that have passed their check-out date."""
    today = datetime.now().date()
    
    # Find bookings where check-out date has passed and guest hasn't checked out
    overdue_checkouts = Booking.query.filter(
        Booking.check_out_date < today,
        Booking.status == Booking.STATUS_CHECKED_IN
    ).all()
    
    for booking in overdue_checkouts:
        booking.check_out(staff_id=None)
    
    # Commit changes for overdue check-outs
    db.session.commit()
    
    # Find bookings where check-in date has passed and guest never checked in
    missed_checkins = Booking.query.filter(
        Booking.check_in_date < today,
        Booking.status == Booking.STATUS_RESERVED
    ).all()
    
    for booking in missed_checkins:
        booking.mark_no_show(staff_id=None)
    
    # Commit changes for missed check-ins
    db.session.commit()
