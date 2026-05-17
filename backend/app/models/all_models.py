from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean, Float, UniqueConstraint, JSON, Index, Numeric
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func
from app.db.base_class import Base


# ── Shared place/enrichment columns ──────────────────────────────────────────

class PlaceColumnsMixin:
    """Canonical enrichment fields shared by BrainstormBinItem, IdeaBinItem, TimelineItem."""
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
    time_category = Column(String, nullable=True)
    added_by = Column(String, nullable=True)


PLACE_FIELDS: tuple[str, ...] = (
    "title", "description", "category", "place_id", "lat", "lng",
    "address", "photo_url", "rating", "price_level", "types",
    "time_category", "added_by",
)

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Auth state
    email_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    # Bumping this invalidates every outstanding access token + refresh token
    # for this user (used on password change and "log out everywhere").
    auth_version = Column(Integer, nullable=False, default=1, server_default="1")

    # Subscription (Roammate Plus)
    subscription_tier = Column(String(16), nullable=False, default="free", server_default="free")
    subscription_status = Column(String(24), nullable=False, default="none", server_default="none")
    subscription_provider = Column(String(16), nullable=True)         # "razorpay" | "apple" | "internal_grant"
    subscription_current_period_end = Column(DateTime(timezone=True), nullable=True)
    subscription_external_id = Column(String, nullable=True, index=True)
    # One-time (₹200 / 30d) plan tracking
    last_one_time_purchase_at = Column(DateTime(timezone=True), nullable=True)
    last_one_time_external_id = Column(String, nullable=True)

    trips = relationship("TripMember", back_populates="user")

class Trip(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    timezone = Column(String, default="UTC", server_default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("user.id"))
    group_id = Column(Integer, ForeignKey("group.id"), nullable=True, index=True)

    members = relationship("TripMember", back_populates="trip")
    timeline_items = relationship("TimelineItem", back_populates="trip")
    idea_bin_items = relationship("IdeaBinItem", back_populates="trip")
    days = relationship("TripDay", back_populates="trip", order_by="TripDay.date")
    group = relationship("Group", back_populates="trips")
    brainstorm_bin_items = relationship("BrainstormBinItem", back_populates="trip", cascade="all, delete-orphan")
    brainstorm_messages = relationship("BrainstormMessage", back_populates="trip", cascade="all, delete-orphan")
    concierge_messages = relationship("ConciergeMessage", back_populates="trip", cascade="all, delete-orphan")


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

class IdeaBinItem(PlaceColumnsMixin, Base):
    __tablename__ = "idea_bin_item"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    origin_idea_id = Column(Integer, ForeignKey("idea_bin_item.id"), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    trip = relationship("Trip", back_populates="idea_bin_items")


class BrainstormBinItem(PlaceColumnsMixin, Base):
    __tablename__ = "brainstorm_bin_item"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trip = relationship("Trip", back_populates="brainstorm_bin_items")
    user = relationship("User")


class BrainstormMessage(Base):
    __tablename__ = "brainstorm_message"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    trip = relationship("Trip", back_populates="brainstorm_messages")
    user = relationship("User")


class ConciergeMessage(Base):
    __tablename__ = "concierge_message"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String, nullable=False)          # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")  # "text" | "action_card" | "place_card" | "error"
    metadata_ = Column("metadata", JSON, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    trip = relationship("Trip", back_populates="concierge_messages")
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
    event_id = Column(Integer, ForeignKey("timeline_item.id", ondelete="CASCADE"), nullable=False, index=True)
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


class TimelineItem(PlaceColumnsMixin, Base):
    __tablename__ = "timeline_item"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trip.id"))
    location_name = Column(String, nullable=True)
    day_date = Column(String, nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_locked = Column(Boolean, default=False)
    event_type = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    is_skipped = Column(Boolean, default=False, server_default="false", nullable=False)

    trip = relationship("Trip", back_populates="timeline_items")


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


class SubscriptionEvent(Base):
    """Audit log of every billing webhook / IAP transaction received."""
    __tablename__ = "subscription_event"
    __table_args__ = (
        Index("ix_subscription_event_user_created", "user_id", "created_at"),
        UniqueConstraint("provider", "event_id", name="uq_subscription_event_provider_event"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String(16), nullable=False)        # "razorpay" | "apple"
    event_id = Column(String, nullable=False)            # external event id for idempotency
    event_type = Column(String(64), nullable=False)
    raw_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UsageCounter(Base):
    """Per-user monthly usage counters for free-tier quota enforcement."""
    __tablename__ = "usage_counter"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_usage_counter_user_period"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(String(7), nullable=False)           # "YYYY-MM"
    brainstorm_messages = Column(Integer, nullable=False, default=0, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Coupon(Base):
    """Discount / promo codes redeemable against one-time or subscription purchases."""
    __tablename__ = "coupon"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True, index=True)  # uppercase
    description = Column(String, nullable=True)
    discount_type = Column(String(16), nullable=False)   # "flat_off" | "percent_off" | "fixed_price"
    discount_value = Column(Integer, nullable=False)     # paise for flat_off/fixed_price; basis-points for percent_off
    applies_to = Column(String(32), nullable=False)      # "one_time" | "subscription_first_cycle" | "any"
    valid_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=False)
    max_redemptions_per_user = Column(Integer, nullable=False, default=1, server_default="1")
    razorpay_offer_id = Column(String, nullable=True)
    apple_offer_id = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CouponRedemption(Base):
    __tablename__ = "coupon_redemption"
    __table_args__ = (
        UniqueConstraint("coupon_id", "user_id", name="uq_coupon_redemption_coupon_user"),
        Index("ix_coupon_redemption_user", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    coupon_id = Column(Integer, ForeignKey("coupon.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(24), nullable=False)        # "razorpay" | "apple" | "internal_grant"
    payment_external_id = Column(String, nullable=True)  # razorpay payment_id / apple transaction_id / None
    amount_paid_paise = Column(Integer, nullable=False, default=0, server_default="0")
    applied_at_period_start = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserIdentity(Base):
    """OAuth identity linked to a user (provider+subject is unique)."""
    __tablename__ = "user_identity"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_user_identity_provider_subject"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(16), nullable=False)        # 'google' | 'apple'
    subject = Column(String(255), nullable=False)        # provider's stable sub
    email_at_link = Column(String(320), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailVerification(Base):
    """Single-use token emailed to a user to verify ownership of an email address."""
    __tablename__ = "email_verification"

    token_hash = Column(String(64), primary_key=True)    # sha256 hex of raw token
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(320), nullable=False)
    purpose = Column(String(24), nullable=False)         # 'signup' | 'change_email'
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PasswordReset(Base):
    __tablename__ = "password_reset"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    device_label = Column(String(128), nullable=True)
    parent_id = Column(Integer, ForeignKey("refresh_token.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DayRoute(Base):
    __tablename__ = "day_route"
    __table_args__ = (UniqueConstraint("trip_id", "day_date", name="uq_day_route"),)

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trip.id", ondelete="CASCADE"), nullable=False, index=True)
    day_date = Column(String, nullable=False)
    encoded_polyline = Column(Text, nullable=True)
    legs = Column(JSON, nullable=False, default=list)
    total_duration_s = Column(Integer, default=0)
    total_distance_m = Column(Integer, default=0)
    ordered_event_ids = Column(JSON, nullable=False, default=list)
    unroutable = Column(JSON, nullable=False, default=list)
    waypoint_fingerprint = Column(String, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
