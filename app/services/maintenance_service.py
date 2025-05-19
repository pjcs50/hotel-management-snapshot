"""
Maintenance service module.

This module provides service layer functionality for managing maintenance requests.
"""

from datetime import datetime
from sqlalchemy import func, or_, and_
from app.models.maintenance_request import MaintenanceRequest
from app.models.room import Room
from app.models.user import User
from app.models.room_status_log import RoomStatusLog


class MaintenanceService:
    """Service class for managing maintenance requests."""

    def __init__(self, db_session):
        """Initialize with a database session."""
        self.db_session = db_session

    def get_all_maintenance_requests(self, filters=None, page=1, per_page=10):
        """
        Get all maintenance requests with optional filtering and pagination.
        
        Args:
            filters: Dictionary of filters to apply
            page: Page number (starting from 1)
            per_page: Number of items per page
            
        Returns:
            Paginated maintenance requests
        """
        query = self.db_session.query(MaintenanceRequest)
        
        if filters:
            if 'status' in filters and filters['status']:
                query = query.filter(MaintenanceRequest.status == filters['status'])
            if 'room_id' in filters and filters['room_id']:
                query = query.filter(MaintenanceRequest.room_id == filters['room_id'])
            if 'assigned_to' in filters and filters['assigned_to']:
                query = query.filter(MaintenanceRequest.assigned_to == filters['assigned_to'])
            if 'priority' in filters and filters['priority']:
                query = query.filter(MaintenanceRequest.priority == filters['priority'])
            if 'issue_type' in filters and filters['issue_type']:
                query = query.filter(MaintenanceRequest.issue_type == filters['issue_type'])
            if 'q' in filters and filters['q']:
                search_term = f"%{filters['q']}%"
                query = query.filter(
                    or_(
                        MaintenanceRequest.description.ilike(search_term),
                        MaintenanceRequest.notes.ilike(search_term)
                    )
                )
        
        # Create a subquery to count total items (without ORDER BY)
        count_subquery = query.with_entities(func.count()).scalar()
        
        # Apply ordering
        query = query.order_by(
            MaintenanceRequest.status,
            MaintenanceRequest.priority.desc(),
            MaintenanceRequest.created_at.desc()
        )
        
        # Calculate offset and limit
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        # Create a pagination-like object
        class PaginationObject:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = max(1, (total + per_page - 1) // per_page)
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
                
            def iter_pages(self):
                for i in range(1, self.pages + 1):
                    yield i
                
            def prev(self):
                return self.__class__(self.items, self.page - 1, self.per_page, self.total) if self.has_prev else None
                
            def next(self):
                return self.__class__(self.items, self.page + 1, self.per_page, self.total) if self.has_next else None
        
        return PaginationObject(items, page, per_page, count_subquery)
    
    def get_maintenance_request(self, request_id):
        """
        Get a maintenance request by ID.
        
        Args:
            request_id: ID of the maintenance request
            
        Returns:
            Maintenance request or None if not found
        """
        return self.db_session.query(MaintenanceRequest).get(request_id)
    
    def create_maintenance_request(self, data):
        """
        Create a new maintenance request.
        
        Args:
            data: Dictionary with maintenance request data
            
        Returns:
            Newly created maintenance request
        """
        maintenance_request = MaintenanceRequest(
            room_id=data['room_id'],
            reported_by=data['reported_by'],
            issue_type=data['issue_type'],
            description=data['description'],
            priority=data.get('priority', 'medium'),
            status='open',
            notes=data.get('notes')
        )
        
        # If assigned_to is provided, update status to assigned
        if 'assigned_to' in data and data['assigned_to']:
            maintenance_request.assigned_to = data['assigned_to']
            maintenance_request.status = 'assigned'
        
        # Save to database
        self.db_session.add(maintenance_request)
        self.db_session.commit()
        
        return maintenance_request
    
    def update_maintenance_request(self, request_id, data):
        """
        Update an existing maintenance request.
        
        Args:
            request_id: ID of the maintenance request to update
            data: Dictionary with updated maintenance request data
            
        Returns:
            Updated maintenance request
        """
        maintenance_request = self.get_maintenance_request(request_id)
        if not maintenance_request:
            return None
        
        # Update fields
        if 'issue_type' in data:
            maintenance_request.issue_type = data['issue_type']
        if 'description' in data:
            maintenance_request.description = data['description']
        if 'priority' in data:
            maintenance_request.priority = data['priority']
        if 'status' in data:
            maintenance_request.status = data['status']
        if 'notes' in data:
            maintenance_request.notes = data['notes']
        
        # Handle assignment
        old_assigned_to = maintenance_request.assigned_to
        if 'assigned_to' in data:
            maintenance_request.assigned_to = data['assigned_to']
            
            # If newly assigned, update status if still open
            if maintenance_request.assigned_to and not old_assigned_to and maintenance_request.status == 'open':
                maintenance_request.status = 'assigned'
        
        # Handle resolution
        if data.get('status') == 'resolved' and not maintenance_request.resolved_at:
            maintenance_request.resolved_at = datetime.now()
        
        # Save to database
        self.db_session.commit()
        
        return maintenance_request
    
    def delete_maintenance_request(self, request_id):
        """
        Delete a maintenance request.
        
        Args:
            request_id: ID of the maintenance request to delete
            
        Returns:
            True if deleted, False if not found
        """
        maintenance_request = self.get_maintenance_request(request_id)
        if not maintenance_request:
            return False
        
        # Delete from database
        self.db_session.delete(maintenance_request)
        self.db_session.commit()
        
        return True
    
    def assign_maintenance_request(self, request_id, staff_id):
        """
        Assign a maintenance request to a staff member.
        
        Args:
            request_id: ID of the maintenance request to assign
            staff_id: ID of the staff member to assign
            
        Returns:
            Updated maintenance request
        """
        return self.update_maintenance_request(request_id, {
            'assigned_to': staff_id,
            'status': 'assigned'
        })
    
    def mark_in_progress(self, request_id, notes=None):
        """
        Mark a maintenance request as in progress.
        
        Args:
            request_id: ID of the maintenance request
            notes: Additional notes (optional)
            
        Returns:
            Updated maintenance request
        """
        data = {
            'status': 'in_progress'
        }
        
        if notes:
            data['notes'] = notes
            
        return self.update_maintenance_request(request_id, data)
    
    def resolve_maintenance_request(self, request_id, notes=None):
        """
        Mark a maintenance request as resolved.
        
        Args:
            request_id: ID of the maintenance request
            notes: Resolution notes (optional)
            
        Returns:
            Updated maintenance request
        """
        data = {
            'status': 'resolved',
            'resolved_at': datetime.now()
        }
        
        if notes:
            # Prepend resolution note to existing notes
            maintenance_request = self.get_maintenance_request(request_id)
            current_notes = maintenance_request.notes or ""
            resolution_note = f"[RESOLVED: {datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
            
            if current_notes:
                data['notes'] = f"{resolution_note}\n\n{current_notes}"
            else:
                data['notes'] = resolution_note
        
        request = self.update_maintenance_request(request_id, data)
        
        # Update room status if necessary
        if request:
            room = self.db_session.query(Room).get(request.room_id)
            if room and room.status == 'maintenance':
                room.status = 'clean'
                
                # Log the status change
                status_log = RoomStatusLog(
                    room_id=room.id,
                    old_status='maintenance',
                    new_status='clean',
                    changed_by=request.assigned_to or request.reported_by
                )
                self.db_session.add(status_log)
                self.db_session.commit()
        
        return request
    
    def close_maintenance_request(self, request_id, verified_by, notes=None):
        """
        Mark a maintenance request as closed after verification.
        
        Args:
            request_id: ID of the maintenance request
            verified_by: ID of the user verifying the resolution
            notes: Verification notes (optional)
            
        Returns:
            Updated maintenance request
        """
        data = {
            'status': 'closed'
        }
        
        if notes:
            # Prepend verification note to existing notes
            maintenance_request = self.get_maintenance_request(request_id)
            current_notes = maintenance_request.notes or ""
            verification_note = f"[VERIFIED: {datetime.now().strftime('%Y-%m-%d %H:%M')}] Verified by user #{verified_by}: {notes}"
            
            if current_notes:
                data['notes'] = f"{verification_note}\n\n{current_notes}"
            else:
                data['notes'] = verification_note
        
        return self.update_maintenance_request(request_id, data)
    
    def get_maintenance_stats(self):
        """
        Get statistics about maintenance requests.
        
        Returns:
            Dictionary with maintenance statistics
        """
        # Get counts by status
        status_counts = dict(
            self.db_session.query(
                MaintenanceRequest.status,
                func.count(MaintenanceRequest.id)
            ).group_by(
                MaintenanceRequest.status
            ).all()
        )
        
        # Get counts by priority
        priority_counts = dict(
            self.db_session.query(
                MaintenanceRequest.priority,
                func.count(MaintenanceRequest.id)
            ).group_by(
                MaintenanceRequest.priority
            ).all()
        )
        
        # Get counts by issue type
        issue_type_counts = dict(
            self.db_session.query(
                MaintenanceRequest.issue_type,
                func.count(MaintenanceRequest.id)
            ).group_by(
                MaintenanceRequest.issue_type
            ).all()
        )
        
        # Calculate average resolution time
        avg_resolution = self.db_session.query(
            func.avg(
                func.julianday(MaintenanceRequest.resolved_at) - 
                func.julianday(MaintenanceRequest.created_at)
            ) * 24  # Convert days to hours
        ).filter(
            MaintenanceRequest.resolved_at.isnot(None)
        ).scalar()
        
        return {
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'issue_type_counts': issue_type_counts,
            'avg_resolution_hours': float(avg_resolution) if avg_resolution else None,
            'total': sum(status_counts.values())
        } 