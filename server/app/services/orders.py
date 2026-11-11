"""Package discovery, quotation and order operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.commerce import CoachingPackage, Order, Quotation
from app.models.enums import OrderStatus, QuotationStatus, VerificationStatus
from app.models.identity import CoachProfile, PlayerProfile, User


class CommerceError(Exception):
    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message)
        self.status_code = status_code


def eligible_coach(db: Session, coach_id):
    coach = db.scalar(
        select(CoachProfile).options(joinedload(CoachProfile.user)).where(CoachProfile.id == coach_id)
    )
    if (coach is None or coach.user.account_status.value != "active"
            or coach.verification_status != VerificationStatus.APPROVED
            or not coach.professional_bio or not coach.specialisations):
        return False
    return True


def list_packages(db: Session):
    return [p for p in db.scalars(select(CoachingPackage).where(CoachingPackage.is_active.is_(True)).order_by(CoachingPackage.created_at.desc()))
            if eligible_coach(db, p.coach_profile_id)]


def package_by_id(db: Session, package_id):
    package = db.get(CoachingPackage, package_id)
    if package is None or not package.is_active or not eligible_coach(db, package.coach_profile_id):
        raise CommerceError("Package was not found", 404)
    return package


def create_package(db: Session, user: User, data: dict):
    coach = user.coach_profile
    if coach is None:
        raise CommerceError("Coach profile was not found", 404)
    package = CoachingPackage(coach_profile_id=coach.id, **data)
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def update_package(db: Session, user: User, package_id, data: dict):
    package = db.get(CoachingPackage, package_id)
    if package is None:
        raise CommerceError("Package was not found", 404)
    if user.coach_profile is None or package.coach_profile_id != user.coach_profile.id:
        raise CommerceError("Package does not belong to this coach", 404)
    for key, value in data.items():
        setattr(package, key, value)
    db.commit()
    db.refresh(package)
    return package


def player_quotation(db: Session, user: User, package_id):
    player: PlayerProfile | None = user.player_profile
    if player is None:
        raise CommerceError("Player profile was not found", 404)
    package = package_by_id(db, package_id)
    quotation = Quotation(
        package_id=package.id,
        player_profile_id=player.id,
        coach_profile_id=package.coach_profile_id,
        package_title=package.title,
        package_description=package.description,
        price_amount=package.price_amount,
        currency=package.currency,
        session_limit=package.session_limit,
        duration_days=package.duration_days,
        terms=package.terms,
    )
    db.add(quotation)
    db.commit()
    db.refresh(quotation)
    return quotation


def accept_quotation(db: Session, user: User, quotation_id):
    player = user.player_profile
    if player is None:
        raise CommerceError("Player profile was not found", 404)
    quotation = db.scalar(select(Quotation).where(Quotation.id == quotation_id).with_for_update())
    if quotation is None or quotation.player_profile_id != player.id:
        raise CommerceError("Quotation was not found", 404)
    if quotation.order is not None:
        raise CommerceError("Quotation has already been accepted", 409)
    if quotation.status != QuotationStatus.OPEN:
        raise CommerceError("Quotation is not open", 409)
    expires = quotation.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        quotation.status = QuotationStatus.EXPIRED
        db.commit()
        raise CommerceError("Quotation has expired", 409)
    if quotation.package_id is None:
        raise CommerceError("Package is unavailable", 409)
    order = Order(
        quotation=quotation,
        package_title=quotation.package_title,
        package_description=quotation.package_description,
        price_amount=quotation.price_amount,
        currency=quotation.currency,
        session_limit=quotation.session_limit,
        duration_days=quotation.duration_days,
        terms=quotation.terms,
        status=OrderStatus.PENDING_PAYMENT,
    )
    quotation.status = QuotationStatus.ACCEPTED
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CommerceError("Quotation has already been accepted", 409) from None
    db.refresh(order)
    return order


def order_for_user(db: Session, user: User, order_id):
    order = db.scalar(select(Order).options(joinedload(Order.quotation)).where(Order.id == order_id))
    if order is None:
        raise CommerceError("Order was not found", 404)
    quote = order.quotation
    if user.role.value == "admin":
        return order
    if user.player_profile and quote.player_profile_id == user.player_profile.id:
        return order
    if user.coach_profile and quote.coach_profile_id == user.coach_profile.id:
        return order
    raise CommerceError("Order was not found", 404)


def list_user_orders(db: Session, user: User):
    if user.role.value == "player" and user.player_profile:
        return list(db.scalars(select(Order).join(Quotation).where(Quotation.player_profile_id == user.player_profile.id).order_by(Order.created_at.desc())))
    if user.role.value == "coach" and user.coach_profile:
        return list(db.scalars(select(Order).join(Quotation).where(Quotation.coach_profile_id == user.coach_profile.id).order_by(Order.created_at.desc())))
    raise CommerceError("Profile was not found", 404)
