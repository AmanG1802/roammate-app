from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean, Float, UniqueConstraint, JSON, Index, Numeric
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=True)
    personas = Column(JSON, nullable=True, default=None)
    avatar_url = Column(String, nullable=True)
    home_city = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    currency = Column(String(8), nullable=True)
    travel_blurb = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
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
    brainstorm_bin_items = relationship("BrainstormBinItem", back_populates="trip", cascade="all, delete-orphan")
    brainstorm_messages = relationship("BrainstormMessage", back_populates="trip", cascade="all, delete-orphan")


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
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    place_id = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    address = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    price_level = Column(Integer, nullable=True)
    types = Column(JSON, nullable=True)
    opening_hours = Column(JSON, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    url_source = Column(String)
    time_hint = Column(String, nullable=True)
    time_category = Column(String, nullable=True)
    added_by = Column(String, nullable=True)
    origin_idea_id = Column(Integer, ForeignKey("idea_bin_item.id"), nullable=True, index=True)

    trip = relationship("Trip", back_populates="idea_bin_items")


class BrainstormBinItem(Base):
    __tablename__ = "brainstorm_bin_item"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    place_id = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    price_level = Column(Integer, nullable=True)
    types = Column(JSON, nullable=True)
    opening_hours = Column(JSON, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    time_hint = Column(String, nullable=True)
    time_category = Column(String, nullable=True)
    url_source = Column(String, nullable=True)
    added_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trip = relationship("Trip", back_populates="brainstorm_bin_items")
    user = relationship("User")


class BrainstormMessage(Base):
    __tablename__ = "brainstorm_message"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    trip = relationship("Trip", back_populates="brainstorm_messages")
    user = relationship("User")


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
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    address = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    price_level = Column(Integer, nullable=True)
    types = Column(JSON, nullable=True)
    opening_hours = Column(JSON, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    time_category = Column(String, nullable=True)

    trip = relationship("Trip", back_populates="events")


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="SET NULL"), nullable=True)
    op = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    tokens_in = Column(Integer, nullable=False)
    tokens_out = Column(Integer, nullable=False)
    tokens_total = Column(Integer, nullable=False)
    source = Column(String, nullable=True)
    cost_usd = Column(Numeric(10, 6), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class GoogleMapsApiUsage(Base):
    __tablename__ = "google_maps_api_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="SET NULL"), nullable=True)
    op = Column(String, nullable=False)
    status = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=True)
    attempts = Column(Integer, nullable=True)
    cache_state = Column(String, nullable=True)
    breaker_state = Column(String, nullable=True)
    http_status = Column(Integer, nullable=True)
    error_class = Column(String, nullable=True)
    batch_size = Column(Integer, nullable=True)
    enriched_count = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 6), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
