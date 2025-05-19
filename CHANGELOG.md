# Changelog

All notable changes to the Hotel Management System will be documented in this file.

## [Unreleased]

### Added
- Project scaffold and directory structure
- Planning documentation (PLANNING.md)
- Task tracking system (TASK.md)
- Project README with setup instructions
- Evaluation framework (EVALUATION.md)
- Configuration system with environment support
- Database initialization module
- Flask application factory pattern
- Base model class with common functionality
- Test configuration with pytest
- Frontend setup with Bootstrap 5 and responsive design
- Dashboard UI with mock data
- Base template with navigation
- Custom CSS and JS utilities
- Role-based blueprints for Customer, Receptionist, Manager, Housekeeping, and Admin
- Custom authentication decorators for role-based access control
- User registration with role selection and approval workflow
- Dashboard services structure for role-specific metrics
- Unit tests for role-based access control
- Functional tests for dashboard routes
- Complete DashboardService implementation with role-specific metrics
- Dashboard templates for each role with proper UI components
- Updated functional tests for dashboard routes with HTML content verification
- Service mocking in tests to verify dashboard integration
- Room management system with CRUD operations
- Room forms with validation
- Room management templates (list, view, create, edit)
- Unit tests for RoomService
- Functional tests for room routes
- Customer profile management system
- Customer profile forms with validation
- Customer profile template with responsive design
- CustomerService implementation with CRUD operations
- Unit tests for CustomerService
- Functional tests for customer profile routes
- Reservation system with availability checking algorithm
- BookingService implementation with create, update, and cancel operations
- BookingForm with date validation and room selection
- Booking management templates (list, create, view)
- Customer booking routes for creating and managing reservations
- Double-booking prevention logic for overlapping date ranges
- Room status tracking for booking lifecycle
- Unit tests for booking validation and availability checking
- Functional tests for booking creation and cancellation workflows
- Room availability calendar with visual representation of availability
- Availability calendar service with date range filtering
- Room occupancy statistics and availability metrics
- Customer and receptionist calendar views with role-specific features
- Calendar date range filtering and room type filtering
- Enhanced dashboard visualizations with interactive charts
- Historical occupancy data tracking and visualization
- Room status visualization with toggleable table/chart views
- Cleaning history charts for housekeeping dashboard
- User registration history tracking and visualization
- Interactive revenue analytics for manager dashboard
- Real-time check-in/check-out management in receptionist dashboard
- Missing endpoint implementation for housekeeping (checkout_rooms, cleaning_schedule, inventory)
- Missing endpoint implementation for receptionist (new_booking, search_guest, room_availability, guest_list)
- Comprehensive unit tests for all new endpoints with authentication and role verification
- Admin guest management with listing and detailed view
- Admin reservation management with filtering and detailed view
- Comprehensive monthly reporting system with KPIs
- PDF, Excel, and CSV export capabilities for reports
- Interactive charts for occupancy and revenue visualization
- ReportService for generating hotel performance metrics
- Admin action endpoints for check-in, check-out, and cancel reservation
- Print and email reservation functionality placeholders
- Admin navigation submenu with quick access cards for dashboard, guests, reservations, and reports
- Consistent navigation across all admin pages
- Comprehensive test suite for admin features and report functionality
- Unit tests for check-in, check-out, and cancel reservation operations
- Unit tests for report service and report generation
- Functional tests for admin navigation structure and permissions
- Functional tests for admin reservation management actions
- Functional tests for report export in different formats
- All tests for new admin functionality are now passing (17 tests in total)

### Fixed
- Dashboard URL routing errors in housekeeping dashboard template (housekeeping.checkout_rooms)
- Dashboard URL routing errors in receptionist dashboard template (receptionist.new_booking, etc.)
- Added functional tests to verify all route endpoints work correctly
- Fixed missing action routes in admin reservation management
- Fixed JavaScript errors in reports chart rendering
- Updated reservation details template to use proper form submissions for actions
- Fixed missing navigation links for admin section (guests, reservations, reports)
- Fixed test compatibility issues with room number uniqueness constraint
- Improved test resilience to handle missing dependencies gracefully
- Fixed PDF export functionality with proper dependency checks and user-friendly error messages

## [0.1.1] - 2024-06-01

### Added
- Enhanced reports visualization with modern chart designs
- Dual-axis chart for room type revenue and percentage comparison
- Improved color schemes and visual hierarchy in dashboards
- Responsive chart containers for better mobile display
- Improved tooltip formatting for better data readability
- Enhanced booking service validations for check-in, check-out and cancellation
- Improved error handling with specific error messages for each operation
- Added detailed state validation for booking operations
- Enhanced PDF reports with better formatting, consistency, and visual hierarchy
- Added title page and generation timestamp to Excel reports

### Fixed
- Conditional PDF export warnings to only appear when relevant
- JavaScript errors in chart generation with template code
- Table formatting and alignment for better data presentation
- Form input styling and responsive behavior
- Improved error handling for all export formats with detailed error messages
- Admin dashboard actions with proper validation and error handling
- Consistent styling across all export formats
- Better Excel formatting with consistent headers and column widths

## [0.1.0] - 2024-05-22

### Added
- Initial project setup
- Basic project documentation
- Core configuration files 