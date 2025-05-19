# Horizon Hotel Management System

A comprehensive hotel management system developed as an IB Computer Science Internal Assessment project. This system helps hotel staff manage reservations, room inventory, guest information, and generate operational reports.

## Features

- Room inventory management with detailed room type categorization
- Guest profile creation and management with preferences and loyalty program
- Reservation booking with availability checks and special requests handling
- Dynamic pricing with seasonal rates and day-of-week adjustments
- Staff management with role-based access
- Reporting and analytics dashboard
- Payment processing and transaction tracking
- Loyalty program with points earning and redemption
- Booking history and activity logging
- Room status tracking and maintenance management
- Email notifications for reservations

## Enhanced Features

### Room Management
- Detailed room type categorization with amenities
- Image galleries for room types
- Room status tracking (Available, Booked, Occupied, Cleaning, Maintenance)
- Room status change history logging

### Guest Management
- Enhanced customer profiles with preferences and documents
- Nationality and date of birth tracking
- VIP status designation
- Stay history and statistics

### Loyalty Program
- Multi-tier loyalty program (Standard, Silver, Gold, Platinum)
- Points earning from stays and promotions
- Points redemption for services and upgrades
- Transaction ledger for tracking all loyalty activity

### Dynamic Pricing
- Seasonal rate adjustments based on date ranges
- Day-of-week pricing adjustments
- Special event rate handling
- Minimum stay requirements
- Holiday and weekend rate differentiation

### Booking Enhancements
- Special requests handling
- Early check-in and late checkout management
- Payment tracking with different payment methods
- Confirmation code generation
- Booking cancellation management with fee calculation
- Activity logging for auditing and tracking

## Technology Stack

- **Backend:** Python 3.11+, Flask
- **Database:** SQLite (development), PostgreSQL (production)
- **ORM:** SQLAlchemy with Flask-SQLAlchemy
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Authentication:** Flask-Login, JWT
- **Email:** Flask-Mail
- **Testing:** Pytest, Coverage
- **Task Scheduling:** APScheduler

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/hotel-management-system.git
   cd hotel-management-system
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. Create sample data (optional):
   ```
   python create_sample_data.py  # Basic data
   python create_enhanced_sample_data.py  # Enhanced features data
   ```

7. Run the development server:
   ```
   flask run
   ```

8. Access the application at http://localhost:5000

### Running Tests

```
pytest
```

For coverage report:
```
pytest --cov=app tests/
coverage html  # Creates HTML report in htmlcov/
```

## Project Structure

```
hotel-management-system/
├── app/                    # Application package
│   ├── models/             # Database models
│   │   ├── room_type.py    # Room type model
│   │   ├── room.py         # Room model
│   │   ├── customer.py     # Customer model
│   │   ├── booking.py      # Booking model
│   │   ├── payment.py      # Payment model
│   │   ├── booking_log.py  # Booking history model
│   │   ├── loyalty_ledger.py # Loyalty points model
│   │   └── room_status_log.py # Room status history
│   ├── routes/             # Route definitions 
│   ├── services/           # Business logic services
│   └── utils/              # Utility functions
├── services/               # Business logic services
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── functional/         # Functional tests
├── migrations/             # Database migrations
├── templates/              # HTML templates
├── static/                 # Static assets
│   ├── css/                # CSS files
│   ├── js/                 # JavaScript files
│   └── images/             # Image files
├── docs/                   # Documentation
├── .env.example            # Example environment variables
├── config.py               # Application configuration
├── db.py                   # Database setup
├── app.py                  # Application entry point
├── create_sample_data.py   # Basic sample data generator
├── create_enhanced_sample_data.py # Enhanced sample data generator
├── PLANNING.md             # Project planning document
├── TASK.md                 # Task tracker
├── EVALUATION.md           # Project evaluation
├── pytest.ini              # Pytest configuration
└── requirements.txt        # Project dependencies
```

## Contribution Guidelines

This is an educational project for an IB Computer Science Internal Assessment. Contributions should follow these guidelines:

- Follow PEP 8 style guidelines for Python code
- Include type hints for all functions and methods
- Write docstrings for all functions, classes, and modules
- Include tests for all new functionality
- Update documentation as needed

## License

This project is developed for educational purposes as part of an IB Computer Science course. 