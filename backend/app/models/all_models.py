from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=True)
    trips = relationship("TripMember", back_populates="user")

class Trip(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("user.id"))
    
    members = relationship("TripMember", back_populates="trip")
    events = relationship("Event", back_populates="trip")
    idea_bin_items = relationship("IdeaBinItem", back_populates="trip")
    days = relationship("TripDay", back_populates="trip", order_by="TripDay.date")


class TripDay(Base):
    __tablename__ = "trip_day"
    __table_args__ = (UniqueConstraint("trip_id", "date", name="uq_trip_day"),)

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"), nullable=False)
    date = Column(Date, nullable=False)
    day_number = Column(Integer, nullable=False)

    trip = relationship("Trip", back_populates="days")

class TripMember(Base):
    __tablename__ = "trip_member"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    role = Column(String, default="admin")  # admin, view_only, view_with_vote
    status = Column(String, default="accepted")  # accepted, invited

    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="trips")

class IdeaBinItem(Base):
    __tablename__ = "idea_bin_item"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    title = Column(String, nullable=False)
    place_id = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    url_source = Column(String)
    time_hint = Column(String, nullable=True)
    added_by = Column(String, nullable=True)
    
    trip = relationship("Trip", back_populates="idea_bin_items")

class Event(Base):
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    title = Column(String, nullable=False)
    place_id = Column(String)
    location_name = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    day_date = Column(Date, nullable=True, index=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    is_locked = Column(Boolean, default=False)
    event_type = Column(String)
    sort_order = Column(Integer, default=0)
    added_by = Column(String, nullable=True)

    trip = relationship("Trip", back_populates="events")
