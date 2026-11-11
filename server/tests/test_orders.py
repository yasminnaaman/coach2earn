"""Package, quotation and order authorization tests."""

from datetime import date
from decimal import Decimal

from app.core.security import create_access_token
from app.models.commerce import CoachingPackage
from app.models.enums import UserRole, VerificationStatus
from app.models.identity import CoachProfile, PlayerProfile, User
from app.seed_specialisations import seed_specialisations
from sqlalchemy import select
from app.models.identity import Specialisation, CoachSpecialisation


def user(db, role, email, **kwargs):
    obj = User(email=email, password_hash="x", role=role, date_of_birth=date(1990, 1, 1), **kwargs)
    db.add(obj)
    db.commit()
    return obj


def headers(obj):
    return {"Authorization": f"Bearer {create_access_token(obj.id)}"}


def setup_pair(db, suffix="standard"):
    seed_specialisations(db)
    spec = db.scalar(select(Specialisation).where(Specialisation.slug == "rocket-league"))
    coach = User(email=f"orders-coach-{suffix}@test.local", password_hash="x", role=UserRole.COACH,
        date_of_birth=date(1990, 1, 1), coach_profile=CoachProfile(
            professional_bio="Experienced coach", experience_years=5,
            verification_status=VerificationStatus.APPROVED,
            specialisations=[CoachSpecialisation(specialisation=spec)]))
    player = User(email=f"orders-player-{suffix}@test.local", password_hash="x", role=UserRole.PLAYER,
        date_of_birth=date(1990, 1, 1), player_profile=PlayerProfile())
    db.add_all([coach, player]); db.commit()
    pkg = CoachingPackage(coach_profile_id=coach.coach_profile.id, title="Five sessions",
        description="Details", price_amount=Decimal("125.00"), currency="USD",
        session_limit=5, duration_days=30, terms="Terms")
    db.add(pkg); db.commit()
    return coach, player, pkg


def test_package_discovery_and_owner_management(api_client, db_session):
    coach, player, pkg = setup_pair(db_session)
    found = api_client.get("/api/v1/packages")
    assert found.status_code == 200 and found.json()[0]["id"] == str(pkg.id)
    assert api_client.get(f"/api/v1/packages/{pkg.id}").status_code == 200
    assert api_client.put(f"/api/v1/coaches/me/packages/{pkg.id}", headers=headers(player), json={}).status_code == 403
    body = {"title":"Updated", "description":"Details", "price_amount":"125.00", "currency":"USD",
            "session_limit":5,"duration_days":30,"terms":"Terms","is_active":True}
    changed = api_client.put(f"/api/v1/coaches/me/packages/{pkg.id}", headers=headers(coach), json=body)
    assert changed.status_code == 200 and changed.json()["title"] == "Updated"


def test_order_quote_snapshot_access_and_duplicate_acceptance(api_client, db_session):
    coach, player, pkg = setup_pair(db_session)
    quote = api_client.post("/api/v1/quotations", headers=headers(player), json={"package_id":str(pkg.id), "price_amount":"0"})
    assert quote.status_code == 422
    quote = api_client.post("/api/v1/quotations", headers=headers(player), json={"package_id":str(pkg.id)})
    assert quote.status_code == 201 and quote.json()["price_amount"] == "125.00"
    order = api_client.post("/api/v1/orders", headers=headers(player), json={"quotation_id":quote.json()["id"]})
    assert order.status_code == 201, order.text
    data = order.json()
    assert data["order_reference"].startswith("C2E-") and data["status"] == "pending_payment"
    assert data["price_amount"] == "125.00" and data["coach_profile_id"] == str(coach.coach_profile.id)
    client_marked_paid = api_client.post(
        "/api/v1/orders",
        headers=headers(player),
        json={"quotation_id":quote.json()["id"], "status":"confirmed"},
    )
    assert client_marked_paid.status_code == 422
    assert api_client.post("/api/v1/orders", headers=headers(player), json={"quotation_id":quote.json()["id"]}).status_code == 409
    assert api_client.get("/api/v1/orders", headers=headers(player)).json()[0]["id"] == data["id"]
    assert api_client.get(f"/api/v1/orders/{data['id']}", headers=headers(coach)).status_code == 200
    stranger = user(db_session, UserRole.PLAYER, "stranger-orders@test.local", player_profile=PlayerProfile())
    assert api_client.get(f"/api/v1/orders/{data['id']}", headers=headers(stranger)).status_code == 404


def test_unavailable_package_and_anonymous_order_rejected(api_client, db_session):
    _, player, pkg = setup_pair(db_session)
    pkg.is_active = False; db_session.commit()
    assert api_client.get(f"/api/v1/packages/{pkg.id}").status_code == 404
    assert api_client.post("/api/v1/quotations", headers=headers(player), json={"package_id":str(pkg.id)}).status_code == 404
    assert api_client.get("/api/v1/orders").status_code == 401
