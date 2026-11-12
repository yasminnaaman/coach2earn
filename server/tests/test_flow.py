"""Prototype flow: simulated payment → scheduling → session lifecycle → messaging/passport."""

from datetime import UTC, date, datetime, timedelta

from app.models.enums import UserRole
from app.models.identity import User
from tests.test_bookings import _headers, _setup_coach_player

API = "/api/v1"


def _future(days: int, hour: int = 18) -> str:
    start = (datetime.now(UTC) + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return start.isoformat()


def _paid_order(api_client, player, pkg) -> str:
    quote = api_client.post(f"{API}/quotes", headers=_headers(player), json={"packageId": str(pkg.id)})
    assert quote.status_code == 201, quote.text
    order = api_client.post(f"{API}/orders", headers=_headers(player), json={"quotation_id": quote.json()["id"]})
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    early = api_client.post(
        f"{API}/orders/{order_id}/sessions", headers=_headers(player), json={"starts_at": [_future(3)]}
    )
    assert early.status_code == 409  # must pay first

    paid = api_client.post(
        f"{API}/orders/{order_id}/pay", headers=_headers(player), json={"payment_method": "mpesa_sim"}
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "confirmed"
    assert paid.json()["remaining_to_schedule"] == pkg.session_limit
    return order_id


def test_pay_schedule_and_session_lifecycle(api_client, db_session):
    coach, player, pkg = _setup_coach_player(db_session)
    order_id = _paid_order(api_client, player, pkg)

    # Coaches cannot pay for orders.
    assert api_client.post(
        f"{API}/orders/{order_id}/pay", headers=_headers(coach), json={"payment_method": "card"}
    ).status_code == 403

    scheduled = api_client.post(
        f"{API}/orders/{order_id}/sessions",
        headers=_headers(player),
        json={"starts_at": [_future(3), _future(5)]},
    )
    assert scheduled.status_code == 201, scheduled.text
    body = scheduled.json()
    assert [s["sequence_number"] for s in body["sessions"]] == [1, 2]
    assert body["remaining_to_schedule"] == pkg.session_limit - 2

    # Same slot again clashes with the coach's calendar; too many sessions is rejected.
    assert api_client.post(
        f"{API}/orders/{order_id}/sessions", headers=_headers(player), json={"starts_at": [_future(3)]}
    ).status_code == 409
    too_many = [_future(10 + i) for i in range(pkg.session_limit)]
    assert api_client.post(
        f"{API}/orders/{order_id}/sessions", headers=_headers(player), json={"starts_at": too_many}
    ).status_code == 409

    first, second = body["sessions"]
    sid = first["id"]

    # Player cannot run the coach steps.
    assert api_client.post(f"{API}/sessions/{sid}/start", headers=_headers(player)).status_code == 403
    started = api_client.post(f"{API}/sessions/{sid}/start", headers=_headers(coach))
    assert started.json()["status"] == "confirmed"
    done = api_client.post(
        f"{API}/sessions/{sid}/complete",
        headers=_headers(coach),
        json={"coach_notes": "+ Fast kickoffs\n- Rotation\n> Daily drills"},
    )
    assert done.json()["status"] == "completed"
    assert done.json()["player_confirmed"] is False

    dash = api_client.get(f"{API}/coaches/me/dashboard", headers=_headers(coach)).json()
    assert dash["balance"] == 0  # earning pending until the player confirms
    assert dash["hoursLogged"] == 1

    confirmed = api_client.post(f"{API}/sessions/{sid}/confirm", headers=_headers(player))
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["player_confirmed"] is True
    assert api_client.post(f"{API}/sessions/{sid}/confirm", headers=_headers(player)).status_code == 409

    dash = api_client.get(f"{API}/coaches/me/dashboard", headers=_headers(coach)).json()
    assert dash["balance"] == 8.5  # 50/5 = 10 gross − 15% commission
    assert dash["points"] == 10

    # Dispute flow: completed → disputed (coach gets a message) → confirm resolves it.
    sid2 = second["id"]
    api_client.post(f"{API}/sessions/{sid2}/complete", headers=_headers(coach), json={})
    disputed = api_client.post(
        f"{API}/sessions/{sid2}/dispute", headers=_headers(player), json={"reason": "Ended early"}
    )
    assert disputed.json()["status"] == "disputed"
    threads = api_client.get(f"{API}/messages/threads", headers=_headers(coach)).json()
    assert threads[0]["unread"] == 1 and "Ended early" in threads[0]["last_message"]
    assert api_client.post(f"{API}/sessions/{sid2}/confirm", headers=_headers(player)).json()["status"] == "completed"

    # Cancel frees the slot for rescheduling.
    third = api_client.post(
        f"{API}/orders/{order_id}/sessions", headers=_headers(player), json={"starts_at": [_future(7)]}
    ).json()["sessions"][-1]
    cancelled = api_client.post(f"{API}/sessions/{third['id']}/cancel", headers=_headers(coach))
    assert cancelled.json()["status"] == "cancelled"

    for who in (player, coach):
        orders = api_client.get(f"{API}/me/orders", headers=_headers(who)).json()
        assert orders[0]["order_id"] == order_id
        assert orders[0]["remaining_to_schedule"] == pkg.session_limit - 2


def test_strangers_cannot_see_sessions(api_client, db_session):
    coach, player, pkg = _setup_coach_player(db_session)
    order_id = _paid_order(api_client, player, pkg)
    sid = api_client.post(
        f"{API}/orders/{order_id}/sessions", headers=_headers(player), json={"starts_at": [_future(4)]}
    ).json()["sessions"][0]["id"]
    stranger = User(email="stranger@test.local", password_hash="x", role=UserRole.PLAYER,
                    date_of_birth=date(1990, 1, 1))
    db_session.add(stranger)
    db_session.commit()
    assert api_client.get(f"{API}/sessions/{sid}", headers=_headers(stranger)).status_code == 404
    assert api_client.get(f"{API}/me/orders/{order_id}", headers=_headers(stranger)).status_code == 404


def test_messages_threads_and_read_receipts(api_client, db_session):
    coach, player, _pkg = _setup_coach_player(db_session)
    sent = api_client.post(
        f"{API}/messages", headers=_headers(player),
        json={"coach_profile_id": str(coach.coach_profile.id), "body": "Hi coach"},
    )
    assert sent.status_code == 201 and sent.json()["mine"] is True
    assert api_client.post(
        f"{API}/messages", headers=_headers(player), json={"recipient_user_id": str(player.id), "body": "me"}
    ).status_code == 422

    threads = api_client.get(f"{API}/messages/threads", headers=_headers(coach)).json()
    assert threads[0]["counterpart"]["user_id"] == str(player.id)
    assert threads[0]["unread"] == 1
    msgs = api_client.get(f"{API}/messages/with/{player.id}", headers=_headers(coach)).json()
    assert [m["body"] for m in msgs] == ["Hi coach"]
    assert api_client.get(f"{API}/messages/threads", headers=_headers(coach)).json()[0]["unread"] == 0


def test_passport_uses_player_and_persists_evidence(api_client, db_session):
    coach, player, _pkg = _setup_coach_player(db_session)
    added = api_client.post(
        f"{API}/players/{player.id}/evidence", headers=_headers(player),
        json={"type": "video", "url": "https://youtu.be/demo"},
    )
    assert added.status_code == 201, added.text
    assert [e["url"] for e in added.json()] == ["https://youtu.be/demo"]

    other = api_client.post(
        f"{API}/players/{coach.id}/evidence", headers=_headers(player),
        json={"type": "video", "url": "https://youtu.be/x"},
    )
    assert other.status_code == 403

    passport = api_client.get(f"{API}/players/{player.id}/passport").json()
    assert passport["player"]["name"] == "Avail Player"
    assert len(passport["evidence"]) == 1
