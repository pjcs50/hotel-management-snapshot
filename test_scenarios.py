from datetime import datetime, timedelta
from app_factory import create_app
from app.models import db, Booking, Customer, Room

def create_test_scenarios():
    app = create_app()
    with app.app_context():
        # Create test customer with unique test identifier
        customer = Customer.query.filter_by(email="test@example.com").first() or Customer(name="Test Guest", email="test@example.com")
        if not Customer.query.filter_by(email="test@example.com").first():
            db.session.add(customer)
            db.session.commit()
            print("Created test customer")
        else:
            print("Using existing test customer")

        # Clear existing test bookings
        Booking.query.filter(Booking.customer_id == customer.id).delete()
        
        # Clean up existing test rooms first
        Room.query.filter(Room.number.like("TEST%")).delete()
        db.session.commit()
        
        # Create required test rooms
        required_rooms = 5
        test_rooms = []
        for i in range(required_rooms):
            new_room = Room(
                number=f"TEST{i+1}",
                room_type_id=1,  # Assuming default RoomType ID exists
                price=100.0,
                status=Room.STATUS_AVAILABLE
            )
            db.session.add(new_room)
            test_rooms.append(new_room)
            print(f"Created test room {new_room.number}")
        db.session.commit()
        
        # Refresh the test rooms to get their IDs
        test_rooms = Room.query.filter(Room.number.like("TEST%")).all()
        
        # Fixed date for consistent testing
        now = datetime(2025, 6, 12).date()  # Fixed test date: 2025-06-12
        
        # Scenario 1: Active booking (today)
        b1 = Booking(
            customer_id=customer.id,
            room_id=Room.query.filter(Room.status == Room.STATUS_AVAILABLE).first().id,
            check_in_date=now,
            check_out_date=now + timedelta(days=2),
            status=Booking.STATUS_CHECKED_IN
        )
        b1.calculate_price(save=True)  # Ensure price is calculated
        
        # Scenario 2: Late check-out (3 days overdue)
        # Get a different available room
        room2 = Room.query.filter(Room.id != b1.room_id, Room.status == Room.STATUS_AVAILABLE).first()
        b2 = Booking(
            customer_id=customer.id,
            room_id=room2.id if room2 else Room.query.first().id,
            check_in_date=now - timedelta(days=4),
            check_out_date=now - timedelta(days=1),
            status=Booking.STATUS_CHECKED_OUT
        )
        b2.calculate_price(save=True)  # Ensure price is calculated
        
        # Scenario 3: No-show (check-in date passed, no arrival)
        # Get a different available room
        room3 = Room.query.filter(Room.id != b1.room_id, Room.status == Room.STATUS_AVAILABLE).first()
        b3 = Booking(
            customer_id=customer.id,
            room_id=room3.id if room3 else Room.query.first().id,
            check_in_date=now - timedelta(days=2),
            check_out_date=now,
            status=Booking.STATUS_NO_SHOW
        )
        b3.calculate_price(save=True)  # Ensure price is calculated
        
        # Scenario 4: Future booking (not yet started)
        # Get a different available room
        room4 = Room.query.filter(Room.id != b1.room_id, Room.id != b2.room_id, Room.status == Room.STATUS_AVAILABLE).first()
        b4 = Booking(
            customer_id=customer.id,
            room_id=room4.id if room4 else Room.query.first().id,
            check_in_date=now + timedelta(days=1),
            check_out_date=now + timedelta(days=3),
            status=Booking.STATUS_RESERVED
        )
        b4.calculate_price(save=True)  # Ensure price is calculated
        
        # Scenario 5: Booking with special requests and preferences
        # Get a different available room
        room5 = Room.query.filter(
            Room.id != b1.room_id, 
            Room.id != b2.room_id,
            Room.id != b3.room_id,
            Room.status == Room.STATUS_AVAILABLE
        ).first()
        
        b5 = Booking(
            customer_id=customer.id,
            room_id=room5.id if room5 else Room.query.first().id,
            check_in_date=now + timedelta(days=4),
            check_out_date=now + timedelta(days=6),
            status=Booking.STATUS_RESERVED,
            special_requests=['Late check-out', 'Extra towels'],
            room_preferences={'floor': 'high', 'view': 'ocean'},
            num_guests=2,
            payment_status=Booking.PAYMENT_DEPOSIT,
            payment_amount=100.0
        )
        b5.calculate_price(save=True)  # Ensure price is calculated
        
        db.session.add_all([b1, b2, b3, b4, b5])
        db.session.commit()
        print("Test scenarios created successfully")

if __name__ == '__main__':
    create_test_scenarios()
