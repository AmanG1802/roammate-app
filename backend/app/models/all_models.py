from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, Float, UniqueConstraint, JSON, Index
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
    group_id = Column(Integer, ForeignKey("group.id"), nullable=True, index=True)

    members = relationship("TripMember", back_populates="trip")
    events = relationship("Event", back_populates="trip")
    idea_bin_items = relationship("IdeaBinItem", back_populates="trip")
    days = relationship("TripDay", back_populates="trip", order_by="TripDay.date")
    group = relationship("Group", back_populates="trips")


class Group(Base):
    __tablename__ = "group"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("GroupMember", back_populates="group")
    trips = relationship("Trip", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_member"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    role = Column(String, default="admin")       # admin, member
    status = Column(String, default="accepted")  # accepted, invited

    group = relationship("Group", back_populates="members")
    user = relationship("User")


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
    origin_idea_id = Column(Integer, ForeignKey("idea_bin_item.id"), nullable=True, index=True)

    trip = relationship("Trip", back_populates="idea_bin_items")


class IdeaVote(Base):
    __tablename__ = "idea_vote"
    __table_args__ = (UniqueConstraint("idea_id", "user_id", name="uq_idea_vote"),)

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("idea_bin_item.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    value = Column(Integer, nullable=False)  # +1 or -1
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EventVote(Base):
    __tablename__ = "event_vote"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_vote"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("event.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IdeaTag(Base):
    __tablename__ = "idea_tag"
    __table_args__ = (UniqueConstraint("idea_id", "tag", name="uq_idea_tag"),)

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("idea_bin_item.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_user_created", "user_id", "created_at"),
        Index("ix_notification_user_unread", "user_id", "read_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    trip_id = Column(Integer, ForeignKey("trip.id"), nullable=True, index=True)
    group_id = Column(Integer, nullable=True, index=True)
    actor_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
