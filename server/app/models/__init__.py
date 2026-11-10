"""Import all mapped models so SQLAlchemy and Alembic share complete metadata."""

from app.models.commerce import Booking, CoachingPackage, CoachingSession, Order, Quotation
from app.models.finance import CoachEarning, PayoutAllocation, PayoutRecord
from app.models.identity import (
    CoachProfile,
    CoachQualification,
    CoachSpecialisation,
    CoachVerification,
    PlayerProfile,
    Specialisation,
    Team,
    TeamMembership,
    User,
)
from app.models.rewards import Bonus, PointsTransaction, Prize, Reward, RewardRedemption

__all__ = [
    "Booking",
    "Bonus",
    "CoachEarning",
    "CoachProfile",
    "CoachQualification",
    "CoachSpecialisation",
    "CoachVerification",
    "CoachingPackage",
    "CoachingSession",
    "Order",
    "PayoutAllocation",
    "PayoutRecord",
    "PlayerProfile",
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
