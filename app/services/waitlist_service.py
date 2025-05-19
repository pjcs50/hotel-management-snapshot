"""
Waitlist service module.

This module provides service layer functionality for managing the waitlist.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app.models.waitlist import Waitlist
from app.models.room_type import RoomType
from app.models.user import User
from app.models.booking import Booking
from db import db


class WaitlistService:
    """Service class for managing the waitlist system."""

    def __init__(self, db_session):
        """Initialize with a database session."""
        self.db_session = db_session

    def get_all_waitlist_entries(self, status=None, page=1, per_page=10):
        """
        Get all waitlist entries with optional filtering and pagination.
        
        Args:
            status: Filter by status (optional)
            page: Page number (starting from 1)
            per_page: Number of items per page
            
        Returns:
            Paginated waitlist entries
        """
        query = self.db_session.query(Waitlist)
        
        if status:
            query = query.filter(Waitlist.status == status)
            
        # Create a subquery to count total items
        count_subquery = query.with_entities(db.func.count()).scalar()
        
        # Apply ordering
        query = query.order_by(
            Waitlist.status,
            Waitlist.created_at.desc()
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
    
    def get_waitlist_entry(self, entry_id):
        """
        Get a waitlist entry by ID.
        
        Args:
            entry_id: ID of the waitlist entry
            
        Returns:
            Waitlist entry or None if not found
        """
        return self.db_session.query(Waitlist).get(entry_id)
    
    def add_to_waitlist(self, customer_id, room_type_id, start_date, end_date, notes=None):
        """
        Add a customer to the waitlist.
        
        Args:
            customer_id: ID of the customer
            room_type_id: ID of the room type
            start_date: Requested check-in date
            end_date: Requested check-out date
            notes: Additional notes (optional)
            
        Returns:
            Newly created waitlist entry
            
        Raises:
            ValueError: If the customer is already on the waitlist for the same dates and room type
        """
        # Check if customer already has a waiting request for these dates and room type
        existing_entry = self.db_session.query(Waitlist).filter(
            Waitlist.customer_id == customer_id,
            Waitlist.room_type_id == room_type_id,
            Waitlist.requested_date_start == start_date,
            Waitlist.requested_date_end == end_date,
            Waitlist.status == 'waiting'
        ).first()
        
        if existing_entry:
            raise ValueError("Customer is already on the waitlist for these dates and room type")
        
        # Create new waitlist entry
        waitlist_entry = Waitlist(
            customer_id=customer_id,
            room_type_id=room_type_id,
            requested_date_start=start_date,
            requested_date_end=end_date,
            status='waiting',
            notes=notes
        )
        
        # Save to database
        self.db_session.add(waitlist_entry)
        self.db_session.commit()
        
        return waitlist_entry
    
    def update_waitlist_entry(self, entry_id, data):
        """
        Update a waitlist entry.
        
        Args:
            entry_id: ID of the waitlist entry to update
            data: Dictionary with updated waitlist entry data
            
        Returns:
            Updated waitlist entry
        """
        waitlist_entry = self.get_waitlist_entry(entry_id)
        if not waitlist_entry:
            return None
        
        # Update fields
        if 'status' in data:
            waitlist_entry.status = data['status']
        if 'notes' in data:
            waitlist_entry.notes = data['notes']
        if 'notification_sent' in data:
            waitlist_entry.notification_sent = data['notification_sent']
            if data['notification_sent']:
                waitlist_entry.notification_sent_at = datetime.now()
        
        # Save to database
        self.db_session.commit()
        
        return waitlist_entry
    
    def delete_waitlist_entry(self, entry_id):
        """
        Delete a waitlist entry.
        
        Args:
            entry_id: ID of the waitlist entry to delete
            
        Returns:
            True if deleted, False if not found
        """
        waitlist_entry = self.get_waitlist_entry(entry_id)
        if not waitlist_entry:
            return False
        
        # Delete from database
        self.db_session.delete(waitlist_entry)
        self.db_session.commit()
        
        return True
    
    def find_matching_waitlist_entries(self, room_type_id, available_date_start, available_date_end):
        """
        Find waitlist entries that match an available date range.
        
        Args:
            room_type_id: ID of the room type
            available_date_start: Available check-in date
            available_date_end: Available check-out date
            
        Returns:
            List of matching waitlist entries, ordered by creation date (oldest first)
        """
        return self.db_session.query(Waitlist).filter(
            Waitlist.room_type_id == room_type_id,
            Waitlist.status == 'waiting',
            # Check if the waitlist request can fit within the available date range
            Waitlist.requested_date_start >= available_date_start,
            Waitlist.requested_date_end <= available_date_end
        ).order_by(Waitlist.created_at).all()
    
    def process_cancellation(self, booking_id):
        """
        Process a booking cancellation and notify waitlisted customers.
        
        Args:
            booking_id: ID of the cancelled booking
            
        Returns:
            List of waitlist entries that were notified
        """
        # Get cancelled booking details
        booking = self.db_session.query(Booking).get(booking_id)
        if not booking:
            return []
        
        # Find matching waitlist entries
        matching_entries = self.find_matching_waitlist_entries(
            booking.room.room_type_id,
            booking.check_in_date,
            booking.check_out_date
        )
        
        notified_entries = []
        for entry in matching_entries:
            # Update entry to mark as notified
            self.update_waitlist_entry(entry.id, {
                'notification_sent': True
            })
            notified_entries.append(entry)
            
            # In a real application, you would send an email notification here
            
        return notified_entries
    
    def promote_waitlist_entry(self, entry_id, booking_data=None):
        """
        Promote a waitlist entry to a booking.
        
        Args:
            entry_id: ID of the waitlist entry to promote
            booking_data: Additional booking data (optional)
            
        Returns:
            Tuple of (updated waitlist entry, new booking)
        """
        entry = self.get_waitlist_entry(entry_id)
        if not entry or entry.status != 'waiting':
            return (None, None)
        
        # In a real application, you would create a booking here
        # For this example, we'll just update the waitlist entry
        entry = self.update_waitlist_entry(entry_id, {
            'status': 'promoted',
            'notes': f"{entry.notes or ''}\nPromoted to booking at {datetime.now()}"
        })
        
        # Placeholder for actual booking creation
        booking = None
        
        return (entry, booking)
    
    def expire_waitlist_entry(self, entry_id, reason=None):
        """
        Mark a waitlist entry as expired.
        
        Args:
            entry_id: ID of the waitlist entry to expire
            reason: Reason for expiration (optional)
            
        Returns:
            Updated waitlist entry
        """
        entry = self.get_waitlist_entry(entry_id)
        if not entry or entry.status != 'waiting':
            return None
        
        notes = f"{entry.notes or ''}\nExpired at {datetime.now()}"
        if reason:
            notes += f": {reason}"
            
        return self.update_waitlist_entry(entry_id, {
            'status': 'expired',
            'notes': notes
        })
    
    def get_waitlist_counts_by_room_type(self):
        """
        Get counts of waiting entries grouped by room type.
        
        Returns:
            Dictionary mapping room type names to counts
        """
        result = self.db_session.query(
            RoomType.name, 
            func.count(Waitlist.id)
        ).join(
            Waitlist, 
            and_(
                RoomType.id == Waitlist.room_type_id,
                Waitlist.status == 'waiting'
            )
        ).group_by(RoomType.name).all()
        
        return {row[0]: row[1] for row in result} 