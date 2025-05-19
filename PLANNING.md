# Hotel Management System - Planning Document
*Last Updated: May 23, 2024*  
*Version: 1.0.1*

## Problem Definition (Criterion A – 6 marks)
**Problem Statement:** 
The local hotel chain "Horizon Hotels" currently manages reservations, guest information, and room inventory using a combination of spreadsheets and paper-based systems. This leads to several critical operational issues:

1. **Booking Conflicts**: Double-booking of rooms occurs due to lack of real-time availability tracking, causing guest dissatisfaction and potential revenue loss.
2. **Revenue Leakage**: Late check-ins, early check-outs, and extended stays are not properly tracked or billed, resulting in lost revenue opportunities.
3. **Housekeeping Coordination**: Poor handoff between front desk and housekeeping creates delays in room readiness, affecting guest satisfaction and check-in experience.
4. **Reporting Inefficiency**: Generating occupancy and revenue reports requires manual data compilation from multiple sources, consuming staff time and introducing errors.
5. **Staff Communication**: Lack of centralized notification system leads to communication breakdowns between departments, impacting service quality.

The hotel needs a digital solution that centralizes operations, prevents booking conflicts, optimizes revenue capture, streamlines interdepartmental communication, and provides real-time insights.

**Client Needs:**
- Centralized management of room inventory and reservations
- Guest profile management with history tracking
- Staff assignment and scheduling
- Reporting on occupancy rates and revenue
- Integration with existing payment processing

## Success Criteria (Criterion A – 6 marks)
1. **Reservation Management**: Staff can create, view, update, and delete room reservations with 100% accuracy of room availability
   - *Verified by unit tests in `tests/unit/test_booking_service.py` and functional tests in `tests/functional/test_booking_routes.py`*
2. **Double-Booking Prevention**: System prevents double-booking of rooms through availability checks with zero reservation conflicts
   - *Verified by unit tests in `tests/unit/test_booking_validation.py`*
3. **Guest Registration**: Guests can be registered with profile information and linked to reservations, with at least 95% of guest profiles having complete required information
   - *Verified by unit tests in `tests/unit/test_customer_model.py` and functional tests in `tests/functional/test_customer_routes.py`*
4. **Room Categorization**: Room categories (standard, deluxe, suite) can be defined with different rates, including at least 3 distinct room types
   - *Verified by unit tests in `tests/unit/test_room_model.py` and functional tests in `tests/functional/test_room_routes.py`*
5. **Reporting**: Reports can be generated for occupancy rates by date range with data export options (PDF, Excel)
   - *Verified by unit tests in `tests/unit/test_reporting_service.py` and manual verification of generated reports.*
6. **Role-Based Access**: Staff accounts have appropriate role-based access (admin, receptionist, housekeeping, manager) with role-based redirect latency < 200 ms
   - *Verified by unit tests in `tests/unit/test_auth_decorators.py` and functional tests in `tests/functional/test_role_access.py`*
7. **Notifications**: Reservation confirmations can be printed or emailed automatically within 1 minute of booking creation
   - *Verified by integration tests in `tests/integration/test_notification_system.py`*
8. **Search Functionality**: Search functionality for finding guests and reservations returns results in < 2 seconds
   - *Verified by functional tests in `tests/functional/test_search_features.py` and performance tests.*
9. **Dashboard Metrics**: Dashboard shows key metrics (rooms occupied, arriving today, departing today) with real-time updates
   - *Verified by functional tests in `tests/functional/test_dashboard_routes.py`*
10. **Seasonal Pricing**: System handles seasonal pricing adjustments with support for at least 4 different rate periods
    - *Verified by unit tests in `tests/unit/test_pricing_service.py`*
11. **Customer Self-Service**: Customers can create and manage their own bookings through a dedicated portal
    - *Verified by functional tests in `tests/functional/test_customer_portal.py`*
12. **Staff Approval Workflow**: New staff accounts require manager approval before activation
    - *Verified by unit tests in `tests/unit/test_staff_service.py` and functional tests in `tests/functional/test_admin_routes.py`*
13. **Test Coverage**: Achieve ≥ 80% automated test coverage across all modules
    - *Verified by `pytest --cov` reports.*
14. **Form Validation**: 90% of UI forms pass validation on first entry
    - *Verified by manual testing and UI automation tests (e.g., Selenium).*
15. **Housekeeping Integration**: Room status transitions from "Needs Cleaning" to "Available" with electronic housekeeping confirmations
    - *Verified by unit tests in `tests/unit/test_room_service.py` and functional tests in `tests/functional/test_housekeeping_routes.py`*

## Data Model Overview (Criterion B – 6 marks)

### Core Tables
| Table | Key Columns & Purpose | Indexes | Diagram Ref. |
| ----- | --------------------- | ------- | ------------ |
| **users** | `id, username, email, pw_hash, role, role_requested, is_active, created_at` | `idx_users_email`, `idx_users_role` | Fig. 1 |
| **customers** | `id, user_id ↔ users.id, name, phone, address, emergency_contact, profile_complete` | `idx_customers_user_id` | Fig. 1 |
| **rooms** | `id, number, type, base_rate, status (Available/Booked/Occupied/Needs Cleaning), last_cleaned` | `idx_rooms_status`, `idx_rooms_type` | Fig. 1 |
| **room_types** | `id, name, description, amenities, base_rate, capacity` | `idx_room_types_name` | Fig. 1 |
| **bookings** | `id, room_id, customer_id, check_in_date, check_out_date, status, early_hours, late_hours, created_at, last_modified` | `idx_bookings_dates` (room_id, check_in_date, check_out_date), `idx_bookings_customer` | Fig. 1 |
| **folio_items** | `id, booking_id, date, description, charge_amount` | `idx_folio_booking_id` | Fig. 1 |
| **payments** | `id, booking_id, amount, method, recorded_at, status` | `idx_payments_booking_id` | Fig. 1 |
| **loyalty_ledgers** | `id, customer_id, points, reason, txn_dt` | `idx_loyalty_customer_id` | Fig. 1 |
| **notifications** | `id, user_id, message, entity_type, entity_id, is_read, created_at` | `idx_notifications_user`, `idx_notifications_unread` | Fig. 1 |
| **room_status_log** | `id, room_id, old_status, new_status, changed_at, changed_by` | `idx_status_log_room_id` | Fig. 1 |
| **staff_requests** | `id, user_id, role_requested, status (Pending/Approved/Denied), requested_at, handled_at` | `idx_staff_requests_status` | Fig. 1 |
| **waitlist** | `id, customer_id, room_type_id, requested_dates, status, created_at` | `idx_waitlist_dates` | Fig. 1 |
| **special_requests** | `id, booking_id, request_type, description, status, created_at` | `idx_special_requests_booking` | Fig. 1 |
| **reviews** | `id, booking_id, rating, comments, submitted_at` | `idx_reviews_booking` | Fig. 1 |
| **maintenance_requests** | `id, room_id, issue_type, description, status, reported_at, resolved_at` | `idx_maintenance_room_id`, `idx_maintenance_status` | Fig. 1 |
| **seasonal_rates** | `id, room_type_id, start_date, end_date, rate_multiplier, name` | `idx_seasonal_rates_dates` | Fig. 1 |

### Entity Relationships
- Users can be Customers or Staff members (one-to-one)
- Customers can have multiple Bookings (one-to-many)
- Rooms belong to one Booking at a time (one-to-many)
- Bookings can have multiple Folio Items and Payments (one-to-many)
- Customers can have multiple Loyalty Ledger entries (one-to-many)
- Users receive Notifications (one-to-many)
- Rooms have Status Log entries (one-to-many)
- Rooms belong to a Room Type (many-to-one)
- Bookings can have Special Requests (one-to-many)
- Bookings can have Reviews (one-to-one)
- Rooms can have Maintenance Requests (one-to-many)
- Room Types can have Seasonal Rates (one-to-many)

<!-- ER Diagram will be created in Phase 1 and inserted here -->
<img src="docs/er_diagram.png" alt="ER Diagram (Fig. 1) - To be created in Phase 1">

## Technical Approach (Criterion B – 6 marks)
- **Backend:** Python 3.11+ with Flask framework
- **Database:** 
  - SQLite for development and testing (for simplicity and portability)
  - PostgreSQL for production (for scalability and transaction support)
- **ORM:** 
  - SQLAlchemy with Flask-SQLAlchemy (preferred over raw SQLAlchemy Core for its Flask integration)
  - Query optimization through appropriate indexing and lazy-loading relationships
- **UI:** 
  - HTML/CSS/JavaScript with Bootstrap 5
  - Responsive design for mobile compatibility
- **JavaScript Libraries:**
  - FullCalendar for booking visualization and date selection
  - Chart.js for dashboard metrics visualization
  - jQuery for DOM manipulation and AJAX calls
- **Authentication:** 
  - Flask-Login for session management
  - Token-based password reset
- **Form Handling:** 
  - Flask-WTF and WTForms for server-side validation
  - Client-side validation with HTML5 and custom JS
- **Testing:** 
  - Pytest with coverage reports
  - Mocking external dependencies
  - Integration tests with selenium for critical user flows
- **Security:** 
  - JWT auth for API endpoints (if future API development is planned)
  - Input validation
  - CSRF protection
  - Password hashing with bcrypt
- **Document Generation:** 
  - WeasyPrint/flask-weasyprint for PDF invoices and reports (conditional import)
  - openpyxl for Excel report generation (conditional import)
- **Calendar Component:** 
  - FullCalendar for booking visualization
- **CI/CD:**
  - GitHub Actions for automated testing on each push
  - Linting with flake8 and black
  - Automated documentation generation (e.g., Sphinx for API docs)

## Implementation Phases (Criterion C – 12 marks)

### Phase 1: Foundation & Authentication (Weeks 1-2)
1. **System Architecture**
   - Set up Flask application factory structure
   - Configure development and production environments
   - Implement error handling and logging
   - Write pytest fixture for temporary SQLite DB

2. **Database Schema**
   - Create core tables: users, customers, rooms, bookings
   - Set up migrations framework with Flask-Migrate
   - Implement base model class with CRUD operations
   - Create indexes for key query patterns
   - Generate initial ER Diagram (docs/er_diagram.png)

3. **Authentication System**
   - User registration with role selection
   - Login/logout functionality with session management
   - Password reset flow with secure tokens
   - Role-based access control with decorator pattern
   - Staff approval workflow with notifications
   - Unit tests for authentication flows including failures

4. **Basic UI Structure**
   - Base templates with responsive design
   - Role-specific navigation
   - Flash message system
   - Form validation with client and server-side checks

5. **Git Evidence:** Commit messages like "feat(auth): implement user registration", "refactor(db): add base model", and corresponding timestamps in `CHANGELOG.md`.

### Phase 2: Core Functionality (Weeks 3-4)
1. **Room Management**
   - Room CRUD operations
   - Room type configuration
   - Room status tracking
   - Room availability search
   - Unit tests for room status transitions

2. **Customer Management**
   - Customer profile CRUD
   - Customer search functionality
   - Customer history tracking
   - Customer data export (GDPR compliance)
   - Test customer profile completeness validation

3. **Booking System**
   - Booking creation workflow with availability check
   - Booking modification
   - Booking cancellation
   - Double-booking prevention logic with transaction isolation
   - Unit test the double-book check logic with overlapping and touching date ranges

4. **Dashboard Implementation**
   - Role-specific dashboards
   - Key metrics display
   - Upcoming check-ins/check-outs
   - Occupancy visualization
   - Test dashboard data aggregation
   - Create dashboard mockup (docs/dashboard_mockup.png)

5. **Git Evidence:** Commit messages like "feat(rooms): implement room CRUD", "test(booking): add double-booking tests", and corresponding timestamps in `CHANGELOG.md`.


<!-- Dashboard mockup will be created in Phase 2 and inserted here -->
<img src="docs/dashboard_mockup.png" alt="Dashboard Mockup - To be created in Phase 2">

### Phase 3: Operations Workflows (Weeks 5-6)
1. **Check-in/Check-out Process**
   - Check-in workflow with room assignment
   - Check-out process with final billing
   - Early check-in and late check-out handling
   - No-show handling via scheduled job
   - Test room status transitions during check-in/out

2. **Housekeeping Integration**
   - Room cleaning status tracking
   - Housekeeping task management
   - Maintenance request system
   - Test housekeeping workflow completion

3. **Billing and Payments**
   - Folio item generation
   - Payment recording with transaction safety
   - Invoice generation in PDF format
   - Payment history
   - Test billing calculation logic

4. **Notification System**
   - In-app notifications
   - Email notifications
   - Staff alerts
   - System notifications
   - Test notification delivery

5. **Git Evidence:** Commit messages like "feat(checkin): implement check-in workflow", "fix(billing): resolve folio calculation error", and corresponding timestamps in `CHANGELOG.md`.

### Phase 4: Advanced Features (Weeks 7-8)
1. **Reporting Module**
   - Occupancy reports
   - Revenue reports
   - Housekeeping reports
   - Custom report generator
   - Test report data accuracy

2. **Loyalty Program**
   - Points accrual system
   - Redemption functionality
   - Tier management
   - Special offers
   - Test points calculation

3. **Seasonal Pricing**
   - Seasonal rate configuration
   - Special event pricing
   - Discount management
   - Rate calendar
   - Parametrize seasonal pricing test cases across multiple date ranges

4. **Audit and Security**
   - Activity logging
   - Audit trail functionality
   - Data export tools (GDPR)
   - Security enhancements
   - Test audit log completeness

5. **Git Evidence:** Commit messages like "feat(reports): add occupancy report", "feat(loyalty): implement points accrual", and corresponding timestamps in `CHANGELOG.md`.

### Phase 5: Optimization and Refinement (Weeks 9-10)
1. **Performance Optimization**
   - Query optimization
   - Caching strategy
   - Asynchronous tasks
   - Load testing and benchmarking

2. **User Experience Refinement**
   - UI/UX improvements based on initial feedback
   - Mobile responsiveness enhancement
   - Accessibility compliance (WCAG AA where feasible)
   - User feedback implementation

3. **Testing and Quality Assurance**
   - Comprehensive test suite review and expansion
   - Edge case handling refinement
   - Load testing with tools like Locust or k6
   - Security testing (OWASP Top 10 checks)

4. **Documentation and Deployment Preparation**
   - User manual refinement
   - API documentation (if applicable)
   - Deployment guide creation
   - Final report preparation planning

5. **Git Evidence:** Commit messages like "perf(db): optimize booking queries", "style(ui): improve dashboard layout", and corresponding timestamps in `CHANGELOG.md`.

### Phase 6: Deployment & Evaluation (Weeks 11-12) (Criterion D & E)
1. **Containerization**
   - Dockerize the application
   - Create docker-compose setup for development
   - Document container deployment

2. **Cloud Deployment**
   - Provision a Heroku or Azure staging instance
   - Configure production database
   - Set up monitoring and logging

3. **User Testing**
   - Conduct usability testing with 2+ users (receptionist, guest roles)
   - Record and analyze feedback (e.g., in `docs/usability_feedback.md`)
   - Implement critical usability improvements

4. **Final Evaluation**
   - Evaluate each success criterion with concrete evidence
   - Compile test reports and analytics
   - Complete `EVALUATION.md` with screenshots and metrics
   - Finalize IA documentation and appendices

5. **Git Evidence:** Commit messages like "chore(deploy): add Dockerfile", "docs(eval): update success criteria evidence", and corresponding timestamps in `CHANGELOG.md`.

## Key Workflows & DB State Transitions (Criterion B & C)

### Booking & Room Status Flow (Fig. 2)

| Action | DB Reads | DB Writes |
|--------|----------|-----------|
| **Create Booking** | Check `bookings` for date overlap, check `rooms.status` | Insert `bookings` record, update `rooms.status`, insert `room_status_log` |
| **Check-In** | Read `bookings`, `customers`, `rooms` | Update `bookings.status`, update `rooms.status`, insert `room_status_log` |
| **Check-Out** | Read `bookings`, `folio_items` | Update `bookings.status`, update `rooms.status`, insert `loyalty_ledgers`, insert `room_status_log` |
| **Room Cleaning** | Read `rooms` | Update `rooms.status`, update `rooms.last_cleaned`, insert `room_status_log` |

### Early/Late Charges Flow (Fig. 3)

| Action | DB Reads | DB Writes |
|--------|----------|-----------|
| **Early Check-In** | Read `bookings.check_in_date`, `room_types.base_rate` | Update `bookings.early_hours`, insert `folio_items` |
| **Extend Stay** | Read `bookings`, check `bookings` for new date overlap | Update `bookings.check_out_date`, insert `folio_items` |
| **Late Check-Out** | Read `bookings.check_out_date`, `room_types.base_rate` | Update `bookings.late_hours`, insert `folio_items` |

### Staff Onboarding Flow (Fig. 4)

| Action | DB Reads | DB Writes |
|--------|----------|-----------|
| **Registration** | Check `users.username` and `users.email` for uniqueness | Insert `users` with `role_requested` and `is_active=False`, insert `staff_requests` |
| **Approval** | Read `staff_requests`, `users` | Update `users.role` and `users.is_active`, update `staff_requests.status`, insert `notifications` |

## Assumptions & Design Decisions (Criterion A)
- The system will initially be deployed for a single hotel location
- Internet connectivity is reliable at the hotel premises
- Staff have basic computer literacy
- The hotel has standard roles (receptionist, manager, housekeeping)
- The payment processing will integrate with the hotel's existing system
- Data backup will occur daily
- The system will prioritize preventing double-bookings over maximizing occupancy
- Role-based access will strictly control what actions each user type can perform
- All financial transactions will be logged with audit trails
- Seasonal pricing adjustments will be configured by managers, not calculated automatically
- Customer data privacy will follow GDPR guidelines
- The system will handle concurrent users with proper locking mechanisms
- Mobile responsiveness is important but a native mobile app is out of scope

## Technical Edge Case Solutions (Criterion C)

### Double-booking Race Condition
**Problem**: Multiple concurrent booking attempts for the same room and overlapping dates.
**Solution**: Implement database transaction with explicit row locking (SELECT FOR UPDATE on relevant `rooms` rows) on room availability check, with retry decorator for SQLite in development to simulate. For PostgreSQL, rely on its robust transaction isolation levels (e.g., Serializable or Repeatable Read if necessary, though optimistic locking with version numbers might be a better approach for higher concurrency).

### Late Cancellation Fee
**Problem**: Revenue loss when guests cancel too close to check-in date.
**Solution**: Cancellation policy enforcement with time-based fee calculation:
- > 48 hours: No charge
- 24-48 hours: 25% of first night
- < 24 hours: 100% of first night
Transaction wrapped in try-except with explicit commits and rollbacks. Fee added as `folio_item`.

### No-Show Handling
**Problem**: Guests who book but never arrive tie up inventory.
**Solution**: Scheduled job (e.g., APScheduler) runs X hours (configurable) after check-in window closes for expected arrivals:
1. Flag booking as "No-Show"
2. Charge one night's stay (or pre-defined no-show fee) to payment method on file (if applicable and tokenized)
3. Release room for new bookings (update `rooms.status`)
4. Send notification to staff

### Overbooking Management
**Problem**: High-demand periods may benefit from strategic overbooking.
**Solution**: Optional waitlist system (`waitlist` table) with FIFO queue implementation:
1. When all rooms of a type are booked, offer waitlist option
2. On cancellation, automatically check waitlist and offer to first matching customer (notification system)
3. Configurable overbooking threshold by room type and season (admin setting)

### Payment Processing Failures
**Problem**: External payment gateway failures during checkout or pre-authorization.
**Solution**: 
1. Implement retry mechanism with exponential backoff for transient errors
2. Store payment attempts (`payments` table) with detailed status and error information
3. Allow staff to manually process offline payments and update system
4. Notification system for failed payments requiring intervention

### Room Status Discrepancies
**Problem**: Physical room status may not match system status due to manual errors or system glitches.
**Solution**: 
1. Daily automatic audit job that compares expected status (from `bookings`) against current `rooms.status`
2. Reconciliation interface for managers to correct discrepancies with reason logging
3. Log all manual status corrections in `room_status_log` with `changed_by` user ID
4. Regular integrity checks between related tables (`bookings.room_id` and `rooms.id`)

*[Additional design decisions will be documented here as development progresses]*

## Planned Evaluation (Criterion E – 6 marks)
| Aspect Evaluated | Evidence to Collect | Location of Evidence & Analysis |
|------------------|---------------------|-----------------------------------|
| **Functionality** | Success criteria checklist, Video demonstration, Test reports (unit, integration, functional) | `EVALUATION.md` (Sec E1), `docs/video_demo_link.txt`, `htmlcov/index.html` |
| **Usability**    | User feedback survey results (2+ users), Recorded observations from usability testing | `docs/usability_feedback.md`, `EVALUATION.md` (Sec E3) |
| **Maintainability**| Code modularity (module diagram, LOC per module), Adherence to coding standards (linting reports), Code complexity metrics (e.g., cyclomatic complexity) | `docs/module_diagram.png`, `EVALUATION.md` (Sec C1, D3), Linting reports |
| **Performance**  | Load test report (response times, throughput), Key query execution times | `docs/load_test_report.pdf`, `EVALUATION.md` (Sec D3) |
| **Extensibility**| Discussion of how new features (e.g., conference room booking) could be added, API design (if applicable) | `EVALUATION.md` (Sec D3) |
| **Client Satisfaction**| Written feedback from client/stakeholder on meeting original needs | `docs/client_feedback.md`, `EVALUATION.md` (Sec E1, E3) | 

## Manager Dashboard Implementation (2023-10-18)

### Design Decisions

1. **Shared Template Architecture**: 
   - Created a base dashboard template (`dashboard_base.html`) that all role-specific dashboards extend
   - This improves code reuse and ensures consistent UI across all user dashboards
   - Uses named blocks to allow each dashboard to customize specific sections while maintaining overall structure

2. **Staff Management Features**:
   - Implemented comprehensive staff management with viewing, editing, and role management
   - Staff details page shows personal information and activity metrics
   - Staff list includes filtering by role, status, and search capability
   - Form validation ensures proper data format and prevents unauthorized role changes

3. **Staff Request System**:
   - Created a structured approval workflow for staff role change requests
   - Approval/denial process updates both the request status and user role
   - Virtual request handling for users with role_requested but no formal request record
   - Clear UI with request details and action buttons

4. **Room Pricing Management**:
   - Implemented a flexible pricing system with base rates and dynamic multipliers
   - Weekend and peak season rates calculated from base price using configurable multipliers
   - Interface includes automatic calculation buttons to maintain proper price relationships
   - Pricing model designed to be extensible for future pricing rules

5. **Staff Performance Metrics**:
   - Design includes capturing key performance indicators for each staff member
   - Metrics include tasks completed, response time, and customer satisfaction
   - Database schema allows tracking of staff actions and outcomes
   - Visualization dashboard provides managers with clear performance insights
   - Charts and graphs help identify trends and areas for improvement

6. **Unit Testing**:
   - Comprehensive unit tests cover all major manager functionality
   - Test fixtures create the necessary database records for testing
   - Mocking used where appropriate to isolate tests from external dependencies
   - Tests validate both UI rendering and database state changes 