"""Package discovery and order endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_coach, require_player
from app.db.session import get_db
from app.models.identity import User
from app.schemas.orders import OrderAccept, OrderRead, PackageRead, PackageWrite, QuotationCreate, QuotationRead
from app.services.orders import (CommerceError, accept_quotation, create_package, list_packages,
                                 list_user_orders, order_for_user, package_by_id, player_quotation,
                                 update_package)

router = APIRouter()


def _order_read(order):
    q = order.quotation
    return OrderRead(
        id=order.id, order_reference=order.order_reference, quotation_id=order.quotation_id,
        player_profile_id=q.player_profile_id, coach_profile_id=q.coach_profile_id,
        package_title=order.package_title, package_description=order.package_description,
        price_amount=order.price_amount, currency=order.currency, session_limit=order.session_limit,
        duration_days=order.duration_days, terms=order.terms, status=order.status.value,
        created_at=order.created_at, updated_at=order.updated_at,
    )


def _fail(exc: CommerceError):
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/packages", response_model=list[PackageRead], tags=["packages"])
def packages(db: Session = Depends(get_db)):
    return list_packages(db)


@router.get("/packages/{package_id}", response_model=PackageRead, tags=["packages"])
def package_detail(package_id: UUID, db: Session = Depends(get_db)):
    try:
        return package_by_id(db, package_id)
    except CommerceError as exc:
        _fail(exc)


@router.post("/coaches/me/packages", response_model=PackageRead, status_code=201, tags=["packages"])
def package_create(payload: PackageWrite, user: User = Depends(require_coach), db: Session = Depends(get_db)):
    try:
        return create_package(db, user, payload.model_dump())
    except CommerceError as exc:
        _fail(exc)


@router.put("/coaches/me/packages/{package_id}", response_model=PackageRead, tags=["packages"])
def package_update(package_id: UUID, payload: PackageWrite, user: User = Depends(require_coach), db: Session = Depends(get_db)):
    try:
        return update_package(db, user, package_id, payload.model_dump())
    except CommerceError as exc:
        _fail(exc)


@router.post("/quotations", response_model=QuotationRead, status_code=201, tags=["orders"])
def quotation_create(payload: QuotationCreate, user: User = Depends(require_player), db: Session = Depends(get_db)):
    try:
        return player_quotation(db, user, payload.package_id)
    except CommerceError as exc:
        _fail(exc)


@router.post("/orders", response_model=OrderRead, status_code=201, tags=["orders"])
def order_create(payload: OrderAccept, user: User = Depends(require_player), db: Session = Depends(get_db)):
    try:
        return _order_read(accept_quotation(db, user, payload.quotation_id))
    except CommerceError as exc:
        _fail(exc)


@router.get("/orders", response_model=list[OrderRead], tags=["orders"])
def orders(user: CurrentUser, db: Session = Depends(get_db)):
    if user.role.value not in {"player", "coach"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    try:
        return [_order_read(item) for item in list_user_orders(db, user)]
    except CommerceError as exc:
        _fail(exc)


@router.get("/orders/{order_id}", response_model=OrderRead, tags=["orders"])
def order_detail(order_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    try:
        return _order_read(order_for_user(db, user, order_id))
    except CommerceError as exc:
        _fail(exc)
