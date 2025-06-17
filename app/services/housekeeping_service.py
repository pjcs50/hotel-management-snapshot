"""
Housekeeping service module.

This module provides service layer functionality for managing housekeeping tasks.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, or_, and_
from app.models.housekeeping_task import HousekeepingTask
from app.models.room import Room
from app.models.user import User
from app.models.booking import Booking
from app.models.room_status_log import RoomStatusLog
from app.models.maintenance_request import MaintenanceRequest


class HousekeepingError(Exception):
    """Exception raised for housekeeping operation errors."""
    pass


class HousekeepingService:
    """Service class for managing housekeeping tasks."""

    def __init__(self, db_session):
        """Initialize with a database session."""
        self.db_session = db_session

    def get_all_housekeeping_tasks(self, filters=None, page=1, per_page=10):
        """
        Get all housekeeping tasks with optional filtering and pagination.
        
        Args:
            filters: Dictionary of filters to apply
            page: Page number (starting from 1)
            per_page: Number of items per page
            
        Returns:
            Paginated housekeeping tasks
        """
        query = self.db_session.query(HousekeepingTask)
        
        if filters:
            if 'status' in filters and filters['status']:
                query = query.filter(HousekeepingTask.status == filters['status'])
            if 'room_id' in filters and filters['room_id']:
                query = query.filter(HousekeepingTask.room_id == filters['room_id'])
            if 'assigned_to' in filters and filters['assigned_to']:
                query = query.filter(HousekeepingTask.assigned_to == filters['assigned_to'])
            if 'priority' in filters and filters['priority']:
                query = query.filter(HousekeepingTask.priority == filters['priority'])
            if 'task_type' in filters and filters['task_type']:
                query = query.filter(HousekeepingTask.task_type == filters['task_type'])
            if 'due_date_from' in filters and filters['due_date_from']:
                query = query.filter(HousekeepingTask.due_date >= filters['due_date_from'])
            if 'due_date_to' in filters and filters['due_date_to']:
                query = query.filter(HousekeepingTask.due_date <= filters['due_date_to'])
            if 'q' in filters and filters['q']:
                search_term = f"%{filters['q']}%"
                query = query.filter(
                    or_(
                        HousekeepingTask.description.ilike(search_term),
                        HousekeepingTask.notes.ilike(search_term)
                    )
                )
                
        # Create a subquery to count total items (without ORDER BY)
        count_subquery = query.with_entities(func.count()).scalar()
        
        # Apply ordering
        query = query.order_by(
            HousekeepingTask.due_date,
            HousekeepingTask.priority.desc(),
            HousekeepingTask.created_at.desc()
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
    
    def get_housekeeping_task(self, task_id):
        """
        Get a housekeeping task by ID.
        
        Args:
            task_id: ID of the housekeeping task
            
        Returns:
            Housekeeping task or None if not found
        """
        return self.db_session.query(HousekeepingTask).get(task_id)
    
    def create_housekeeping_task(self, data):
        """
        Create a new housekeeping task.
        
        Args:
            data: Dictionary with housekeeping task data
            
        Returns:
            Newly created housekeeping task
        """
        housekeeping_task = HousekeepingTask(
            room_id=data['room_id'],
            task_type=data['task_type'],
            description=data.get('description'),
            priority=data.get('priority', 'normal'),
            status='pending',
            due_date=data['due_date'],
            notes=data.get('notes')
        )
        
        # If assigned_to is provided, add assignment
        if 'assigned_to' in data and data['assigned_to']:
            housekeeping_task.assigned_to = data['assigned_to']
        
        # Save to database
        self.db_session.add(housekeeping_task)
        self.db_session.commit()
        
        return housekeeping_task
    
    def update_housekeeping_task(self, task_id, data):
        """
        Update an existing housekeeping task.
        
        Args:
            task_id: ID of the housekeeping task to update
            data: Dictionary with updated housekeeping task data
            
        Returns:
            Updated housekeeping task
        """
        housekeeping_task = self.get_housekeeping_task(task_id)
        if not housekeeping_task:
            return None
        
        # Update fields
        if 'task_type' in data:
            housekeeping_task.task_type = data['task_type']
        if 'description' in data:
            housekeeping_task.description = data['description']
        if 'priority' in data:
            housekeeping_task.priority = data['priority']
        if 'status' in data:
            housekeeping_task.status = data['status']
        if 'due_date' in data:
            housekeeping_task.due_date = data['due_date']
        if 'notes' in data:
            housekeeping_task.notes = data['notes']
        if 'assigned_to' in data:
            housekeeping_task.assigned_to = data['assigned_to']
        
        # Handle completion
        if data.get('status') == 'completed' and not housekeeping_task.completed_at:
            housekeeping_task.completed_at = datetime.now()
        
        # Handle verification
        if data.get('status') == 'verified' and 'verified_by' in data:
            housekeeping_task.verified_by = data['verified_by']
            housekeeping_task.verified_at = datetime.now()
        
        # Save to database
        self.db_session.commit()
        
        return housekeeping_task
    
    def delete_housekeeping_task(self, task_id):
        """
        Delete a housekeeping task.
        
        Args:
            task_id: ID of the housekeeping task to delete
            
        Returns:
            True if deleted, False if not found
        """
        housekeeping_task = self.get_housekeeping_task(task_id)
        if not housekeeping_task:
            return False
        
        # Delete from database
        self.db_session.delete(housekeeping_task)
        self.db_session.commit()
        
        return True
    
    def assign_housekeeping_task(self, task_id, staff_id):
        """
        Assign a housekeeping task to a staff member with proper validation.
        
        Args:
            task_id: ID of the housekeeping task to assign
            staff_id: ID of the staff member to assign
            
        Returns:
            Updated housekeeping task
            
        Raises:
            ValueError: If task or staff member is invalid
            HousekeepingError: If assignment is not allowed
        """
        # Get and validate the task
        task = self.get_housekeeping_task(task_id)
        if not task:
            raise ValueError(f"Housekeeping task with ID {task_id} not found")
        
        # Validate staff member
        staff_member = self.db_session.query(User).get(staff_id)
        if not staff_member:
            raise ValueError(f"Staff member with ID {staff_id} not found")
        
        # Check if staff member is active and has appropriate role
        if not staff_member.is_active:
            raise HousekeepingError(f"Cannot assign task to inactive staff member: {staff_member.username}")
        
        # Validate staff role for housekeeping tasks
        valid_roles = ['housekeeping', 'manager', 'admin']
        if staff_member.role not in valid_roles:
            raise HousekeepingError(
                f"Staff member {staff_member.username} (role: {staff_member.role}) "
                f"cannot be assigned housekeeping tasks. Valid roles: {', '.join(valid_roles)}"
            )
        
        # Check if staff member is available (not overloaded)
        current_tasks = self.db_session.query(HousekeepingTask).filter(
            HousekeepingTask.assigned_to == staff_id,
            HousekeepingTask.status.in_(['pending', 'in_progress'])
        ).count()
        
        max_concurrent_tasks = 10  # Configurable limit
        if current_tasks >= max_concurrent_tasks:
            raise HousekeepingError(
                f"Staff member {staff_member.username} already has {current_tasks} active tasks. "
                f"Maximum allowed: {max_concurrent_tasks}"
            )
        
        # Check for room-specific conflicts
        if task.room_id:
            room = self.db_session.query(Room).get(task.room_id)
            if room:
                # Check if room has conflicting status
                if room.status == Room.STATUS_OCCUPIED:
                    raise HousekeepingError(
                        f"Cannot assign cleaning task for room {room.number} - room is currently occupied"
                    )
                
                # Check for pending maintenance that would conflict
                if self._has_conflicting_maintenance(task.room_id, task.task_type):
                    raise HousekeepingError(
                        f"Cannot assign {task.task_type} task for room {room.number} - "
                        f"conflicting maintenance request exists"
                    )
        
        # Assign the task
        return self.update_housekeeping_task(task_id, {
            'assigned_to': staff_id,
            'status': 'pending',  # Ensure status is set correctly
            'assigned_at': datetime.now()
        })
    
    def _has_conflicting_maintenance(self, room_id, task_type):
        """
        Check if room has maintenance requests that conflict with housekeeping task.
        
        Args:
            room_id: Room ID to check
            task_type: Type of housekeeping task
            
        Returns:
            bool: True if there are conflicting maintenance requests
        """
        # Define which maintenance types conflict with which housekeeping tasks
        conflicts = {
            'regular_cleaning': ['plumbing', 'electrical'],  # Can't clean if major work needed
            'deep_cleaning': ['plumbing', 'electrical', 'furniture'],  # Deep clean conflicts with more
            'turnover': ['plumbing', 'electrical'],  # Turnover needs working utilities
            'maintenance_cleaning': []  # Maintenance cleaning can work around issues
        }
        
        conflicting_types = conflicts.get(task_type, [])
        if not conflicting_types:
            return False
        
        # Check for active maintenance requests of conflicting types
        conflicting_count = self.db_session.query(MaintenanceRequest).filter(
            MaintenanceRequest.room_id == room_id,
            MaintenanceRequest.issue_type.in_(conflicting_types),
            MaintenanceRequest.status.in_(['pending', 'in_progress'])
        ).count()
        
        return conflicting_count > 0
    
    def mark_in_progress(self, task_id, notes=None):
        """
        Mark a housekeeping task as in progress.
        
        Args:
            task_id: ID of the housekeeping task
            notes: Additional notes (optional)
            
        Returns:
            Updated housekeeping task
        """
        data = {
            'status': 'in_progress'
        }
        
        if notes:
            task = self.get_housekeeping_task(task_id)
            current_notes = task.notes or ""
            progress_note = f"[IN PROGRESS: {datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
            
            if current_notes:
                data['notes'] = f"{progress_note}\n\n{current_notes}"
            else:
                data['notes'] = progress_note
            
        return self.update_housekeeping_task(task_id, data)
    
    def complete_housekeeping_task(self, task_id, notes=None):
        """
        Mark a housekeeping task as completed with enhanced validation.
        
        Args:
            task_id: ID of the housekeeping task
            notes: Completion notes (optional)
            
        Returns:
            Updated housekeeping task
            
        Raises:
            HousekeepingError: If completion is not allowed due to conflicts
        """
        task = self.get_housekeeping_task(task_id)
        if not task:
            raise ValueError(f"Housekeeping task with ID {task_id} not found")
        
        # Validate task can be completed
        if task.status not in ['pending', 'in_progress']:
            raise HousekeepingError(f"Task cannot be completed - current status: {task.status}")
        
        # Check for room-specific validation
        if task.room_id:
            room = self.db_session.query(Room).get(task.room_id)
            if not room:
                raise HousekeepingError(f"Room {task.room_id} not found")
            
            # Validate room status allows completion
            if room.status == Room.STATUS_OCCUPIED:
                raise HousekeepingError(
                    f"Cannot complete cleaning task for room {room.number} - room is currently occupied"
                )
            
            # Check for maintenance conflicts before marking as clean
            if task.task_type in ['regular_cleaning', 'deep_cleaning', 'turnover']:
                if self._has_pending_maintenance_blocking_completion(task.room_id):
                    raise HousekeepingError(
                        f"Cannot mark room {room.number} as clean - pending maintenance requests must be resolved first"
                    )
                
                # Validate room state transition
                from app.utils.room_state_machine import RoomStateMachine, RoomTransitionError
                state_machine = RoomStateMachine(self.db_session)
                
                try:
                    # Check if room can transition to available
                    if not state_machine.can_transition(room.status, Room.STATUS_AVAILABLE):
                        raise HousekeepingError(
                            f"Room {room.number} cannot be marked as available from current status: {room.status}"
                        )
                except RoomTransitionError as e:
                    raise HousekeepingError(f"Room status conflict: {str(e)}")
        
        # Update room status if this was a room cleaning task
        if task.room_id and task.task_type in ['regular_cleaning', 'deep_cleaning', 'turnover']:
            room = self.db_session.query(Room).get(task.room_id)
            if room:
                try:
                    # Use state machine for safe status transition
                    from app.utils.room_state_machine import RoomStateMachine
                    state_machine = RoomStateMachine(self.db_session)
                    
                    # Transition room to available with proper validation
                    state_machine.change_room_status(
                        room.id,
                        Room.STATUS_AVAILABLE,
                        user_id=task.assigned_to,
                        notes=f"Completed {task.task_type} task #{task.id}"
                    )
                    
                except Exception as e:
                    raise HousekeepingError(f"Failed to update room status: {str(e)}")
        
        # Prepare task update data
        data = {
            'status': 'completed',
            'completed_at': datetime.now()
        }
        
        if notes:
            current_notes = task.notes or ""
            completion_note = f"[COMPLETED: {datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
            
            if current_notes:
                data['notes'] = f"{completion_note}\n\n{current_notes}"
            else:
                data['notes'] = completion_note
        
        # Update the task
        updated_task = self.update_housekeeping_task(task_id, data)
        
        return updated_task
    
    def _has_pending_maintenance_blocking_completion(self, room_id):
        """
        Check if room has maintenance requests that block cleaning completion.
        
        Args:
            room_id: Room ID to check
            
        Returns:
            bool: True if there are blocking maintenance requests
        """
        try:
            # Critical maintenance types that must be resolved before room can be marked clean
            blocking_types = ['plumbing', 'electrical', 'hvac', 'safety']
            
            # Check for active maintenance requests of blocking types
            blocking_count = self.db_session.query(MaintenanceRequest).filter(
                MaintenanceRequest.room_id == room_id,
                MaintenanceRequest.issue_type.in_(blocking_types),
                MaintenanceRequest.status.in_(['pending', 'in_progress']),
                MaintenanceRequest.priority.in_(['high', 'urgent'])  # Only high priority blocks
            ).count()
            
            return blocking_count > 0
            
        except Exception:
            # If maintenance model doesn't exist, assume no blocking maintenance
            return False
    
    def verify_housekeeping_task(self, task_id, verified_by, notes=None):
        """
        Verify a completed housekeeping task.
        
        Args:
            task_id: ID of the housekeeping task
            verified_by: ID of the user verifying the task
            notes: Verification notes (optional)
            
        Returns:
            Updated housekeeping task
        """
        data = {
            'status': 'verified',
            'verified_by': verified_by,
            'verified_at': datetime.now()
        }
        
        if notes:
            task = self.get_housekeeping_task(task_id)
            current_notes = task.notes or ""
            verification_note = f"[VERIFIED: {datetime.now().strftime('%Y-%m-%d %H:%M')}] Verified by user #{verified_by}: {notes}"
            
            if current_notes:
                data['notes'] = f"{verification_note}\n\n{current_notes}"
            else:
                data['notes'] = verification_note
        
        return self.update_housekeeping_task(task_id, data)
    
    def get_housekeeping_stats(self):
        """
        Get statistics about housekeeping tasks.
        
        Returns:
            Dictionary with housekeeping statistics
        """
        # Get counts by status
        status_counts = dict(
            self.db_session.query(
                HousekeepingTask.status,
                func.count(HousekeepingTask.id)
            ).group_by(
                HousekeepingTask.status
            ).all()
        )
        
        # Get counts by task type
        type_counts = dict(
            self.db_session.query(
                HousekeepingTask.task_type,
                func.count(HousekeepingTask.id)
            ).group_by(
                HousekeepingTask.task_type
            ).all()
        )
        
        # Calculate overdue tasks
        now = datetime.now()
        overdue_count = self.db_session.query(
            func.count(HousekeepingTask.id)
        ).filter(
            HousekeepingTask.due_date < now,
            HousekeepingTask.status.in_(['pending', 'in_progress'])
        ).scalar() or 0
        
        # Calculate today's tasks
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        today_count = self.db_session.query(
            func.count(HousekeepingTask.id)
        ).filter(
            HousekeepingTask.due_date >= today_start,
            HousekeepingTask.due_date < today_end
        ).scalar() or 0
        
        # Calculate average completion time
        avg_completion = self.db_session.query(
            func.avg(
                func.julianday(HousekeepingTask.completed_at) - 
                func.julianday(HousekeepingTask.created_at)
            ) * 24  # Convert days to hours
        ).filter(
            HousekeepingTask.completed_at.isnot(None)
        ).scalar()
        
        return {
            'status_counts': status_counts,
            'type_counts': type_counts,
            'overdue_count': overdue_count,
            'today_count': today_count,
            'avg_completion_hours': float(avg_completion) if avg_completion else None,
            'total': sum(status_counts.values())
        }
    
    def generate_turnover_tasks(self, checkout_date=None):
        """
        Generate turnover tasks for rooms with checkouts.
        
        Args:
            checkout_date: Date to generate tasks for (defaults to today)
            
        Returns:
            Number of tasks created
        """
        if checkout_date is None:
            checkout_date = datetime.now().date()
            
        # Find rooms with checkouts on the given date
        checkouts = self.db_session.query(
            Booking.room_id
        ).filter(
            func.date(Booking.check_out_date) == checkout_date,
            Booking.status.in_(['confirmed', 'checked_in'])
        ).all()
        
        room_ids = [checkout[0] for checkout in checkouts]
        
        # Check if tasks already exist
        existing_tasks = self.db_session.query(
            HousekeepingTask.room_id
        ).filter(
            HousekeepingTask.room_id.in_(room_ids),
            func.date(HousekeepingTask.due_date) == checkout_date,
            HousekeepingTask.task_type == 'turnover'
        ).all()
        
        existing_room_ids = [task[0] for task in existing_tasks]
        
        # Create tasks for rooms without existing turnover tasks
        tasks_created = 0
        for room_id in room_ids:
            if room_id not in existing_room_ids:
                # Create new turnover task
                task = HousekeepingTask(
                    room_id=room_id,
                    task_type='turnover',
                    description='Room turnover after guest checkout',
                    status='pending',
                    priority='high',  # Turnover tasks are high priority
                    due_date=datetime.combine(checkout_date, datetime.now().time())
                )
                
                self.db_session.add(task)
                tasks_created += 1
                
        self.db_session.commit()
        return tasks_created 