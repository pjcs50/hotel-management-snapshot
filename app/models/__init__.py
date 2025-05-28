"""
Database models package.

This package contains all SQLAlchemy models for the Hotel Management System.
"""

from datetime import datetime
from db import db


class BaseModel(db.Model):
    """
    Base model class that includes common columns for all models.
    
    This abstract class provides created_at and updated_at columns
    for all models that inherit from it, plus common CRUD methods.
    """

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def save(self):
        """Save this model instance to the database."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """Delete this model instance from the database."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, id):
        """Get a model instance by ID."""
        return cls.query.get(id)

    @classmethod
    def get_all(cls):
        """Get all model instances."""
        return cls.query.all()

    @classmethod
    def create(cls, **kwargs):
        """Create a new model instance with the given attributes."""
        instance = cls(**kwargs)
        instance.save()
        return instance

# Import all models to make them available when importing from app.models
# Uncomment models as needed, avoiding circular imports
from app.models.user import User
from app.models.staff_request import StaffRequest
from app.models.customer import Customer
from app.models.room_type import RoomType
from app.models.room import Room
from app.models.room_status_log import RoomStatusLog
from app.models.booking import Booking
from app.models.seasonal_rate import SeasonalRate
from app.models.payment import Payment
from app.models.booking_log import BookingLog
from app.models.loyalty_ledger import LoyaltyLedger
from app.models.notification import Notification
from app.models.folio_item import FolioItem
from app.models.revenue_forecast import RevenueForecast, ForecastAggregation