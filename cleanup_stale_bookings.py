from datetime import datetime
from app.models import Booking
from db import db

def cleanup_stale_bookings():
    """Clean up existing bookings that have passed their dates."""
    today = datetime.now().date()
    
    print("Checking for overdue check-outs...")
    # Process checked-in bookings past check-out date
    checked_in_overdue = Booking.query.filter(
        Booking.check_out_date < today,
        Booking.status == Booking.STATUS_CHECKED_IN
    ).all()
    
    for booking in checked_in_overdue:
        print(f"Auto-checking out booking {booking.id} (Room {booking.room_id})")
        booking.check_out(staff_id=None)
    db.session.commit()
    print(f"Processed {len(checked_in_overdue)} overdue check-outs")
    
    print("\nChecking for missed check-ins...")
    # Process reserved bookings past check-in date
    reserved_missed = Booking.query.filter(
        Booking.check_in_date < today,
        Booking.status == Booking.STATUS_RESERVED
    ).all()
    
    for booking in reserved_missed:
        print(f"Marking booking {booking.id} as no-show")
        booking.mark_no_show(staff_id=None)
    db.session.commit()
    print(f"Processed {len(reserved_missed)} missed check-ins")

if __name__ == "__main__":
    from app_factory import create_app
    app = create_app()
    with app.app_context():
        cleanup_stale_bookings()
