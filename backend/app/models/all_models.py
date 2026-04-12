from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=True) # For manual auth
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

class TripMember(Base):
    __tablename__ = "trip_member"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    role = Column(String, default="owner") # owner, editor, viewer

    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="trips")

class IdeaBinItem(Base):
    __tablename__ = "idea_bin_item"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    title = Column(String, nullable=False)
    place_id = Column(String) # Google Place ID
    lat = Column(Float)
    lng = Column(Float)
    url_source = Column(String)
    
    trip = relationship("Trip", back_populates="idea_bin_items")

class Event(Base):
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    title = Column(String, nullable=False)
    place_id = Column(String)
    location_name = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_locked = Column(Boolean, default=False)
    event_type = Column(String) # activity, transport, lodging
    
    trip = relationship("Trip", back_populates="events")
