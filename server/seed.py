#!/usr/bin/env python3
"""
Comprehensive seed script — idempotent, safe to re-run on every deploy.

What it does
────────────
1. Seeds the game-specialisation catalog  (Rocket League — already in
   seed_specialisations.py, called here for a single entry point).
2. Creates 5 realistic approved coach accounts with full profiles,
   Rocket League specialisation, and at least one coaching package each.
3. Creates one **known test coach** account whose credentials are printed
   at the end so the team can exercise the full booking flow immediately.

Idempotency
───────────
All coach users are keyed on their email address.  On repeated runs the
script skips any record that already exists — it never updates or deletes.

Usage
─────
  # from the server/ directory:
  python seed.py

  # or as a module:
  python -m seed
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# ── make sure the server package is importable regardless of cwd ──────────────
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from sqlalchemy import func, select                    # noqa: E402
from sqlalchemy.orm import Session                     # noqa: E402

from app.core.security import hash_password            # noqa: E402
from app.db.session import SessionLocal                # noqa: E402
from app.models.commerce import CoachingPackage        # noqa: E402
from app.models.enums import (                         # noqa: E402
    AccountStatus,
    SpecialisationCategory,
    UserRole,
    VerificationStatus,
)
from app.models.identity import (                      # noqa: E402
    CoachProfile,
    CoachSpecialisation,
    CoachVerification,
    Specialisation,
    User,
)
from app.seed_specialisations import (                 # noqa: E402
    INITIAL_SPECIALISATIONS,
    seed_specialisations,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data shapes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PackageSeed:
    title: str
    description: str
    price_amount: Decimal
    currency: str
    session_limit: int
    duration_days: int
    terms: str = "Sessions are 60 minutes each via Discord or custom platform. 24-hour cancellation notice required."


@dataclass
class CoachSeed:
    email: str
    password: str
    display_name: str          # used only for logging
    professional_bio: str
    coaching_goals: str
    experience_years: int
    availability: dict
    packages: list[PackageSeed] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Realistic seed data
# ─────────────────────────────────────────────────────────────────────────────

COACHES: list[CoachSeed] = [
    # ── 1. TEST COACH — known credentials for QA / full-flow testing ─────────
    CoachSeed(
        email="coach.test@coach2earn.io",
        password="TestCoach123!",
        display_name="Jordan Blake (TEST COACH)",
        professional_bio=(
            "I'm a Grand Champion Rocket League player with 4 years of competitive "
            "experience in RLCS qualifiers and regional tournaments. I specialise in "
            "aerial mechanics, rotation discipline, and mental resilience under pressure. "
            "I've coached over 80 players from Diamond to Grand Champion and enjoy "
            "breaking down replays to identify the exact habits holding each player back."
        ),
        coaching_goals=(
            "Help every student achieve at least one full rank tier improvement within "
            "their first package. Focus on fundamentals first, mechanical flourishes second."
        ),
        experience_years=4,
        availability={
            "timezone": "UTC",
            "weekly": [
                {"day": "Monday",    "start": "18:00", "end": "22:00"},
                {"day": "Wednesday", "start": "18:00", "end": "22:00"},
                {"day": "Saturday",  "start": "10:00", "end": "18:00"},
                {"day": "Sunday",    "start": "12:00", "end": "17:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Starter Boost — 3 Sessions",
                description=(
                    "Ideal for players new to coaching. Includes one replay review, "
                    "one live training session targeting your biggest mechanical weakness, "
                    "and one strategy session on rotation and positioning."
                ),
                price_amount=Decimal("45.00"),
                currency="USD",
                session_limit=3,
                duration_days=30,
            ),
            PackageSeed(
                title="Rank-Up Accelerator — 8 Sessions",
                description=(
                    "Eight focused sessions over six weeks. We track your stats every "
                    "session, refine your playstyle for your target rank, and finish "
                    "with a full retrospective and personalised drill plan."
                ),
                price_amount=Decimal("96.00"),
                currency="USD",
                session_limit=8,
                duration_days=45,
            ),
        ],
    ),

    # ── 2. Experienced RLCS coach ────────────────────────────────────────────
    CoachSeed(
        email="alex.mercer@coach2earn.io",
        password="AlexM!rlcs2024",
        display_name="Alex Mercer",
        professional_bio=(
            "Former RLCS Season X participant (North America, Diamond tier) and "
            "full-time Rocket League coach since 2022. I focus on aerial training, "
            "speed-reading opponents, and building consistent 50/50 contest habits. "
            "More than 120 students coached — many now competing at Diamond 3 and above."
        ),
        coaching_goals=(
            "Transform inconsistent players into reliable team assets. My coaching "
            "philosophy: master the controllable, adapt to the rest."
        ),
        experience_years=5,
        availability={
            "timezone": "America/New_York",
            "weekly": [
                {"day": "Tuesday",   "start": "17:00", "end": "21:00"},
                {"day": "Thursday",  "start": "17:00", "end": "21:00"},
                {"day": "Saturday",  "start": "09:00", "end": "15:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Fundamentals Package — 4 Sessions",
                description=(
                    "Deep-dive into rotations, boost management, and positioning. "
                    "Perfect for Gold–Plat players plateauing before Diamond."
                ),
                price_amount=Decimal("60.00"),
                currency="USD",
                session_limit=4,
                duration_days=21,
            ),
            PackageSeed(
                title="Elite Prep — 12 Sessions",
                description=(
                    "Intensive monthly programme. Replay analysis, custom drill packs, "
                    "and weekly live coaching to compete at high Diamond / Champ level."
                ),
                price_amount=Decimal("156.00"),
                currency="USD",
                session_limit=12,
                duration_days=30,
            ),
        ],
    ),

    # ── 3. Female pro player turned coach ────────────────────────────────────
    CoachSeed(
        email="priya.sharma@coach2earn.io",
        password="Priya$RL2024",
        display_name="Priya Sharma",
        professional_bio=(
            "Champion-rank Rocket League player (Peak: Supersonic Legend) with "
            "over 6,000 hours in-game. I represented my university team for three "
            "seasons and have coached over 60 players, focusing on mental game "
            "improvement, mechanical consistency, and team communication for duos. "
            "I particularly enjoy working with newer players who want a structured "
            "learning path."
        ),
        coaching_goals=(
            "Create a safe, supportive environment where players can fail, learn, "
            "and grow without fear. Confidence on the pitch is half the battle."
        ),
        experience_years=3,
        availability={
            "timezone": "Europe/London",
            "weekly": [
                {"day": "Monday",    "start": "19:00", "end": "22:00"},
                {"day": "Friday",    "start": "19:00", "end": "23:00"},
                {"day": "Sunday",    "start": "14:00", "end": "20:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Duo Chemistry Session — 2 Players",
                description=(
                    "Bring a teammate and we work on duo synergy, callouts, rotation "
                    "timing, and reading each other's positioning. Price is per pair."
                ),
                price_amount=Decimal("35.00"),
                currency="GBP",
                session_limit=2,
                duration_days=14,
            ),
            PackageSeed(
                title="Solo Growth Plan — 6 Sessions",
                description=(
                    "Six tailored sessions over three weeks. Focus areas are chosen "
                    "based on a full in-take replay review in session one."
                ),
                price_amount=Decimal("75.00"),
                currency="GBP",
                session_limit=6,
                duration_days=21,
            ),
        ],
    ),

    # ── 4. High-volume replay analyst ────────────────────────────────────────
    CoachSeed(
        email="carlos.vidal@coach2earn.io",
        password="CarlosV!2024rl",
        display_name="Carlos Vidal",
        professional_bio=(
            "I've reviewed over 500 Rocket League replays across all rank tiers and "
            "specialise in data-driven coaching using Ballchasing analytics. "
            "Grand Champion 2 (peaked SSL in 3v3) with a background in sports "
            "performance analysis. My sessions are structured, measurable, and "
            "designed to produce lasting rank improvements rather than quick fixes."
        ),
        coaching_goals=(
            "Turn replay data into actionable habits. Every session ends with a "
            "written summary and a set of drills you can do in free play."
        ),
        experience_years=6,
        availability={
            "timezone": "Europe/Madrid",
            "weekly": [
                {"day": "Wednesday", "start": "20:00", "end": "23:00"},
                {"day": "Thursday",  "start": "20:00", "end": "23:00"},
                {"day": "Saturday",  "start": "11:00", "end": "17:00"},
                {"day": "Sunday",    "start": "11:00", "end": "17:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Replay Deep-Dive — Single Session",
                description=(
                    "One 90-minute replay analysis session. I'll annotate your last "
                    "three ranked games and provide a written improvement report."
                ),
                price_amount=Decimal("20.00"),
                currency="EUR",
                session_limit=1,
                duration_days=7,
            ),
            PackageSeed(
                title="Monthly Analytics Coaching — 10 Sessions",
                description=(
                    "Ten sessions combining live coaching and weekly analytics reviews. "
                    "Progress tracked via Ballchasing stats each week."
                ),
                price_amount=Decimal("140.00"),
                currency="EUR",
                session_limit=10,
                duration_days=30,
            ),
        ],
    ),

    # ── 5. Youth-focused coach ───────────────────────────────────────────────
    CoachSeed(
        email="mia.townsend@coach2earn.io",
        password="MiaT!coach2024",
        display_name="Mia Townsend",
        professional_bio=(
            "Diamond 3 Rocket League player with a background in youth gaming "
            "education. I've run Rocket League after-school programmes at three "
            "secondary schools and coached over 40 young players aged 13–18. "
            "Patience and positivity are at the core of my coaching style — "
            "I make technical concepts accessible, track every student's progress, "
            "and celebrate small wins as much as rank-ups."
        ),
        coaching_goals=(
            "Build the next generation of competitive Rocket League players while "
            "teaching resilience, teamwork, and healthy gaming habits along the way."
        ),
        experience_years=2,
        availability={
            "timezone": "Australia/Sydney",
            "weekly": [
                {"day": "Tuesday",   "start": "16:00", "end": "19:00"},
                {"day": "Thursday",  "start": "16:00", "end": "19:00"},
                {"day": "Saturday",  "start": "10:00", "end": "14:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Youth Intro Package — 3 Sessions",
                description=(
                    "Three friendly, structured sessions for young players (13–18). "
                    "Covers the basics of competitive Rocket League with a positive, "
                    "supportive coaching environment."
                ),
                price_amount=Decimal("45.00"),
                currency="AUD",
                session_limit=3,
                duration_days=21,
                terms=(
                    "For players under 18, a parent or guardian must consent and be "
                    "available to contact during all sessions. 48-hour cancellation notice required."
                ),
            ),
        ],
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_none(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )


def _seed_coach(db: Session, data: CoachSeed, specialisation: Specialisation) -> bool:
    """Insert a complete coach record; return True if created, False if skipped."""
    if _get_or_none(db, data.email) is not None:
        print(f"  skip  {data.email} (already exists)")
        return False

    user = User(
        id=uuid4(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=UserRole.COACH,
        account_status=AccountStatus.ACTIVE,
        date_of_birth=None,   # adult coaches — no DOB required for seeding
    )
    db.add(user)
    db.flush()   # need user.id for coach_profile FK

    profile = CoachProfile(
        id=uuid4(),
        user_id=user.id,
        professional_bio=data.professional_bio,
        coaching_goals=data.coaching_goals,
        experience_years=data.experience_years,
        availability=data.availability,
        verification_status=VerificationStatus.APPROVED,
    )
    db.add(profile)
    db.flush()   # need profile.id for FK references below

    # Attach the Rocket League specialisation
    db.add(CoachSpecialisation(
        coach_profile_id=profile.id,
        specialisation_id=specialisation.id,
    ))

    # Create an APPROVED verification record (no human reviewer needed for seed)
    db.add(CoachVerification(
        id=uuid4(),
        coach_profile_id=profile.id,
        status=VerificationStatus.APPROVED,
        submitted_at=datetime.now(UTC),
        reviewed_at=datetime.now(UTC),
        review_notes="Seeded and auto-approved for demo purposes.",
    ))

    # Attach coaching packages
    for pkg in data.packages:
        db.add(CoachingPackage(
            id=uuid4(),
            coach_profile_id=profile.id,
            title=pkg.title,
            description=pkg.description,
            price_amount=pkg.price_amount,
            currency=pkg.currency,
            session_limit=pkg.session_limit,
            duration_days=pkg.duration_days,
            terms=pkg.terms,
            is_active=True,
        ))

    db.commit()
    print(f"  ✓  created  {data.email}  ({data.display_name})")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("── Step 1: seed specialisation catalog ─────────────────────────────")
    try:
        with SessionLocal() as db:
            count = seed_specialisations(db, INITIAL_SPECIALISATIONS)
        print(f"  ✓  {count} specialisation(s) verified in catalog")
    except Exception as exc:
        print(f"  ✗  specialisation seed failed: {exc}", file=sys.stderr)
        return 1

    print()
    print("── Step 2: fetch Rocket League specialisation ──────────────────────")
    with SessionLocal() as db:
        rl_spec = db.scalar(
            select(Specialisation).where(
                Specialisation.slug == "rocket-league",
                Specialisation.category == SpecialisationCategory.GAME,
            )
        )
    if rl_spec is None:
        print("  ✗  rocket-league specialisation not found after seeding", file=sys.stderr)
        return 1
    print(f"  ✓  found: {rl_spec.name}  (id={rl_spec.id})")

    print()
    print("── Step 3: seed coach accounts ─────────────────────────────────────")
    created = 0
    skipped = 0
    for coach_data in COACHES:
        with SessionLocal() as db:
            # Re-fetch the specialisation inside each new session to keep it attached
            spec = db.get(Specialisation, rl_spec.id)
            if spec is None:
                print("  ✗  could not re-fetch specialisation", file=sys.stderr)
                return 1
            if _seed_coach(db, coach_data, spec):
                created += 1
            else:
                skipped += 1

    print()
    print(f"  Summary: {created} coach(es) created, {skipped} skipped (already exist).")

    # ── Print test-coach credentials ──────────────────────────────────────────
    test_coach = COACHES[0]
    print()
    print("═" * 60)
    print("  TEST COACH CREDENTIALS  (full-flow QA)")
    print("═" * 60)
    print(f"  Email    : {test_coach.email}")
    print(f"  Password : {test_coach.password}")
    print(f"  Role     : coach  |  Status: active  |  Verified: approved")
    print("═" * 60)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
