"""String enums stored as portable constrained strings in the database."""

from enum import StrEnum


class UserRole(StrEnum):
    PLAYER = "player"
    COACH = "coach"
    ADMIN = "admin"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class GuardianConsentStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class SpecialisationCategory(StrEnum):
    SPORT = "sport"
    GAME = "game"


class TeamMemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    PLAYER = "player"
    COACH = "coach"


class QuotationStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class PointsTransactionType(StrEnum):
    EARNED = "earned"
    REDEEMED = "redeemed"
    ADJUSTMENT = "adjustment"


class PointsSourceType(StrEnum):
    SESSION = "session"
    REDEMPTION = "redemption"
    ADMIN_ACTION = "admin_action"
    BONUS = "bonus"


class RedemptionStatus(StrEnum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class PrizeStatus(StrEnum):
    PENDING = "pending"
    RECEIVED = "received"
    DISTRIBUTED = "distributed"


class BonusStatus(StrEnum):
    PENDING = "pending"
    EARNED = "earned"
    RELEASED = "released"
    CANCELLED = "cancelled"


class EarningStatus(StrEnum):
    PENDING = "pending"
    AVAILABLE = "available"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PayoutStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
