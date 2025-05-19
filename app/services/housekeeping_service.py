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
        Assign a housekeeping task to a staff member.
        
        Args:
            task_id: ID of the housekeeping task to assign
            staff_id: ID of the staff member to assign
            
        Returns:
            Updated housekeeping task
        """
        return self.update_housekeeping_task(task_id, {
            'assigned_to': staff_id
        })
    
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
        Mark a housekeeping task as completed.
        
        Args:
            task_id: ID of the housekeeping task
            notes: Completion notes (optional)
            
        Returns:
            Updated housekeeping task
        """
        task = self.get_housekeeping_task(task_id)
        if not task:
            return None
        
        # Update room status if this was a room cleaning task
        if task.task_type in ['regular_cleaning', 'deep_cleaning', 'turnover']:
            room = self.db_session.query(Room).get(task.room_id)
            if room and room.status in ['dirty', 'checkout']:
                # Save the old status for the log
                old_status = room.status
                
                # Update room status
                room.status = 'clean'
                
                # Log the status change
                status_log = RoomStatusLog(
                    room_id=room.id,
                    old_status=old_status,
                    new_status='clean',
                    changed_by=task.assigned_to
                )
                self.db_session.add(status_log)
        
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