from datetime import datetime, timedelta
from app.models import Booking, Room, Customer, User
from db import db

def create_test_bookings():
    # Get or create test user and customer
    user = User.query.filter_by(email="test@example.com").first()
    if not user:
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="pbkdf2:sha256:260000$TestPasswordHash",
            role="customer"
        )
        db.session.add(user)
        db.session.commit()

    customer = Customer.query.filter_by(user_id=user.id).first()
    if not customer:
        customer = Customer(
            user_id=user.id,
            name="Test User",
            email="test@example.com",
            phone="123-456-7890",
            address="Test Address"
        )
        db.session.add(customer)
        db.session.commit()

    # Get available room
    room = Room.query.filter_by(status=Room.STATUS_AVAILABLE).first()
    if not room:
        room = Room(number="TEST-101", room_type_id=1, status=Room.STATUS_AVAILABLE)
        db.session.add(room)
        db.session.commit()
        

    # Create test bookings
    past_booking = Booking(
        room_id=room.id,
        customer_id=customer.id,
        check_in_date=datetime(2025, 5, 29).date(),
        check_out_date=datetime(2025, 5, 30).date(),
        status=Booking.STATUS_CHECKED_IN,
        payment_status=Booking.PAYMENT_FULL
    )

    future_booking = Booking(
        room_id=room.id,
        customer_id=customer.id,
        check_in_date=datetime(2025, 6, 12).date(),
        check_out_date=datetime(2025, 6, 14).date(),
        status=Booking.STATUS_RESERVED
    )

    db.session.add(past_booking)
    db.session.add(future_booking)
    db.session.commit()

if __name__ == "__main__":
    from app_factory import create_app
    app = create_app()
    with app.app_context():
        create_test_bookings()
        print("Created test bookings:")
        print(f"- Past booking: 2025-05-29 to 2025-05-30 (Checked In)")
        print(f"- Future booking: 2025-06-12 to 2025-06-14 (Reserved)")
