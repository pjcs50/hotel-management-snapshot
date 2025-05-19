"""
Notification service module.

This module provides services for managing and retrieving notifications.
"""
from sqlalchemy import desc
from app.models.notification import Notification
from app.models.user import User # For type hinting or fetching user if needed
from db import db # Assuming db.py has SQLAlchemy session

class NotificationService:
    def __init__(self, db_session):
        self.db_session = db_session

    def create_notification(self, user_id, message, type=None, link_url=None):
        """
        Create a new notification for a user.

        Args:
            user_id (int): The ID of the user to notify.
            message (str): The notification message.
            type (str, optional): The type of notification (e.g., 'booking_update').
            link_url (str, optional): A URL for the notification to link to.

        Returns:
            Notification: The created Notification object or None if user not found.
        """
        user = self.db_session.get(User, user_id)
        if not user:
            # Or raise an error, or log: print(f"User with ID {user_id} not found. Cannot create notification.")
            return None 

        notification = Notification(
            user_id=user_id,
            message=message,
            type=type,
            link_url=link_url
        )
        self.db_session.add(notification)
        self.db_session.commit()
        return notification

    def get_user_notifications(self, user_id, limit=10, include_read=False):
        """
        Get notifications for a specific user, most recent first.

        Args:
            user_id (int): The ID of the user.
            limit (int, optional): Maximum number of notifications to return. Defaults to 10.
            include_read (bool, optional): Whether to include already read notifications. Defaults to False.

        Returns:
            list[Notification]: A list of Notification objects.
        """
        query = self.db_session.query(Notification).filter_by(user_id=user_id)
        if not include_read:
            query = query.filter_by(is_read=False)
        
        return query.order_by(desc(Notification.created_at)).limit(limit).all()

    def get_unread_notification_count(self, user_id):
        """
        Get the count of unread notifications for a user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            int: The number of unread notifications.
        """
        return self.db_session.query(Notification)\
            .filter_by(user_id=user_id, is_read=False)\
            .count()

    def mark_notification_as_read(self, notification_id, user_id=None):
        """
        Mark a specific notification as read.
        Optionally verifies that the notification belongs to the user_id if provided.

        Args:
            notification_id (int): The ID of the notification to mark as read.
            user_id (int, optional): The ID of the user. If provided, verifies ownership.

        Returns:
            Notification: The updated Notification object or None if not found/not authorized.
        """
        notification = self.db_session.get(Notification, notification_id)
        if not notification:
            return None
        
        if user_id is not None and notification.user_id != user_id:
            # Log attempt to mark notification not belonging to user: print(f"User {user_id} attempted to mark notification {notification_id} not owned by them.")
            return None # Or raise an Unauthorized error

        notification.is_read = True
        self.db_session.commit()
        return notification

    def mark_all_notifications_as_read(self, user_id):
        """
        Mark all unread notifications for a user as read.

        Args:
            user_id (int): The ID of the user.

        Returns:
            int: The number of notifications marked as read.
        """
        notifications_to_update = self.db_session.query(Notification)\
            .filter_by(user_id=user_id, is_read=False)\
            .all()
        
        if not notifications_to_update:
            return 0

        for notification in notifications_to_update:
            notification.is_read = True
        
        self.db_session.commit()
        return len(notifications_to_update) 