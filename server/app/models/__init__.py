"""Import all mapped models so SQLAlchemy and Alembic share complete metadata."""

from app.models.commerce import Booking, CoachAvailability, CoachingPackage, CoachingSession, Order, Quotation
from app.models.engagement import Message, PlayerEvidence
from app.models.finance import CoachEarning, PayoutAllocation, PayoutRecord
from app.models.identity import (
    CoachProfile,
    CoachQualification,
    CoachQualificationReview,
    CoachSpecialisation,
    CoachVerification,
    PlayerProfile,
    PlayerGame,
    GuardianConsent,
    GuardianConsentDecision,
    Specialisation,
    Team,
    TeamMembership,
    User,
)
from app.models.rewards import Bonus, PointsTransaction, Prize, Reward, RewardRedemption

__all__ = [
    "Booking",
    "Bonus",
    "CoachAvailability",
    "CoachEarning",
    "CoachProfile",
    "CoachQualification",
    "CoachQualificationReview",
    "CoachSpecialisation",
    "CoachVerification",
    "GuardianConsent",
    "GuardianConsentDecision",
    "Message",
    "PlayerEvidence",
    "CoachingPackage",
    "CoachingSession",
    "Order",
    "PayoutAllocation",
    "PayoutRecord",
    "PlayerProfile",
    "PlayerGame",
    "PointsTransaction",
    "Prize",
    "Quotation",
    "Reward",
    "RewardRedemption",
    "Specialisation",
    "Team",
    "TeamMembership",
    "User",
]
