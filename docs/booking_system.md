# Hotel Booking System

This document provides an overview of the Hotel Booking System implementation, including API endpoints, data models, and usage examples.

## Overview

The Hotel Booking System provides a comprehensive solution for managing hotel room bookings, including:

- Room availability checking
- Booking creation, modification, and cancellation
- Check-in and check-out processing
- Early check-in and late check-out handling
- Room status management
- Booking history tracking

## API Endpoints

### Room Availability

#### `GET /api/availability`

Get room availability for a date range.

**Query Parameters:**
- `check_in_date`: Start date (YYYY-MM-DD)
- `check_out_date`: End date (YYYY-MM-DD)
- `room_type_id`: (Optional) Room type ID to filter by

**Response:**
```json
{
  "success": true,
  "check_in_date": "2023-06-01",
  "check_out_date": "2023-06-03",
  "available_rooms": [
    {
      "id": 1,
      "number": "101",
      "room_type_id": 1,
      "room_type": {
        "id": 1,
        "name": "Standard",
        "description": "Standard room",
        "base_rate": 100.0,
        "capacity": 2,
        "amenities": ["WiFi", "TV"]
      }
    }
  ]
}
```

### Booking Management

#### `POST /api/bookings`

Create a new booking.

**Request Body:**
```json
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
```

**Response:**
```json
{
  "success": true,
  "booking": {
    "id": 1,
    "room_id": 1,
    "customer_id": 1,
    "check_in_date": "2023-06-01",
    "check_out_date": "2023-06-03",
    "status": "Reserved",
    "total_price": 200.0,
    "confirmation_code": "ABC12345"
  }
}
```

#### `GET /api/bookings/{booking_id}`

Get booking details.

**Response:**
```json
{
  "success": true,
  "booking": {
    "id": 1,
    "room_id": 1,
    "customer_id": 1,
    "check_in_date": "2023-06-01",
    "check_out_date": "2023-06-03",
    "status": "Reserved",
    "total_price": 200.0,
    "confirmation_code": "ABC12345"
  }
}
```

#### `PUT /api/bookings/{booking_id}`

Update a booking.

**Request Body:**
```json
{
  "check_in_date": "2023-06-01",
  "check_out_date": "2023-06-04",
  "num_guests": 2,
  "early_hours": 0,
  "late_hours": 0,
  "special_requests": "Extra pillows please"
}
```

**Response:**
```json
{
  "success": true,
  "booking": {
    "id": 1,
    "room_id": 1,
    "customer_id": 1,
    "check_in_date": "2023-06-01",
    "check_out_date": "2023-06-04",
    "status": "Reserved",
    "total_price": 300.0,
    "confirmation_code": "ABC12345"
  }
}
```

#### `PATCH /api/bookings/{booking_id}/status`

Update booking status.

**Request Body:**
```json
{
  "status": "Checked In"
}
```

**Response:**
```json
{
  "success": true,
  "booking": {
    "id": 1,
    "status": "Checked In"
  }
}
```

### Early Check-in and Late Check-out

#### `POST /api/bookings/{booking_id}/early-check-in`

Request early check-in for a booking.

**Request Body:**
```json
{
  "hours": 2
}
```

**Response:**
```json
{
  "success": true,
  "booking": {
    "id": 1,
    "early_hours": 2,
    "total_price": 220.0
  }
}
```

#### `POST /api/bookings/{booking_id}/late-check-out`

Request late check-out for a booking.

**Request Body:**
```json
{
  "hours": 2
}
```

**Response:**
```json
{
  "success": true,
  "booking": {
    "id": 1,
    "late_hours": 2,
    "total_price": 220.0
  }
}
```

### Room Status Management

#### `PATCH /api/rooms/{room_id}/status`

Update room status.

**Request Body:**
```json
{
  "status": "Available"
}
```

**Response:**
```json
{
  "success": true,
  "room": {
    "id": 1,
    "number": "101",
    "status": "Available"
  }
}
```

#### `POST /api/rooms/{room_id}/cleaned`

Mark a room as cleaned.

**Response:**
```json
{
  "success": true,
  "room": {
    "id": 1,
    "number": "101",
    "status": "Available",
    "last_cleaned": "2023-06-01T14:30:00Z"
  }
}
```

## Data Models

### Booking

The Booking model represents a hotel reservation with the following attributes:

- `id`: Primary key
- `room_id`: Foreign key to the Room model
- `customer_id`: Foreign key to the Customer model
- `check_in_date`: Date when the guest will check in
- `check_out_date`: Date when the guest will check out
- `status`: Booking status (Reserved/Checked In/Checked Out/Cancelled)
- `early_hours`: Hours before standard check-in time
- `late_hours`: Hours after standard check-out time
- `total_price`: Total price including all adjustments
- `num_guests`: Number of guests for the reservation
- `payment_status`: Status of payment
- `notes`: Internal notes about the reservation
- `special_requests`: Guest's special requests
- `room_preferences`: Guest's room preferences
- `confirmation_code`: Unique confirmation code
- `created_at`: Timestamp when the booking was created
- `updated_at`: Timestamp when the booking was last updated

### Room

The Room model represents a physical hotel room with the following attributes:

- `id`: Primary key
- `number`: Room number (unique)
- `room_type_id`: Foreign key to the RoomType model
- `status`: Current room status (Available/Booked/Occupied/Needs Cleaning)
- `last_cleaned`: Timestamp when the room was last cleaned
- `created_at`: Timestamp when the room was created
- `updated_at`: Timestamp when the room was last updated

## Usage Examples

### Creating a Booking

```python
from app.services.booking_service import BookingService
from datetime import datetime, timedelta

# Create a booking service instance
booking_service = BookingService(db.session)

# Define booking parameters
room_id = 1
customer_id = 1
check_in_date = datetime.now().date() + timedelta(days=1)
check_out_date = check_in_date + timedelta(days=2)

# Create the booking
booking = booking_service.create_booking(
    room_id=room_id,
    customer_id=customer_id,
    check_in_date=check_in_date,
    check_out_date=check_out_date,
    num_guests=2,
    special_requests="Extra pillows please"
)

# Calculate the price
booking.calculate_price()
db.session.commit()

print(f"Booking created with confirmation code: {booking.confirmation_code}")
print(f"Total price: ${booking.total_price:.2f}")
```

### Checking In a Guest

```python
from app.services.booking_service import BookingService

# Create a booking service instance
booking_service = BookingService(db.session)

# Check in the guest
booking = booking_service.check_in(booking_id=1, staff_id=1)

print(f"Guest checked in. Room status: {booking.room.status}")
```

### Cancelling a Booking

```python
from app.services.booking_service import BookingService

# Create a booking service instance
booking_service = BookingService(db.session)

# Cancel the booking
booking = booking_service.cancel_booking(
    booking_id=1,
    reason="Change of plans",
    cancelled_by=1
)

print(f"Booking cancelled. Cancellation fee: ${booking.cancellation_fee:.2f}")
```
