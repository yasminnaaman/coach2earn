"""PayPal and payments module for Coach2Earn.

Brian owns this module. Exports the three shared functions Hope and Yasmin call:
  - create_booked_sessions(db, order_id)  ← called by capture endpoint after payment
  - get_confirmed_unpaid_sessions(db)     ← called by payouts run
  - release_bonus(db, prize_id)           ← called by prizes/{id}/received
"""
from payments.shared import create_booked_sessions, get_confirmed_unpaid_sessions, release_bonus

__all__ = ["create_booked_sessions", "get_confirmed_unpaid_sessions", "release_bonus"]
