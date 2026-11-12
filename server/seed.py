#!/usr/bin/env python3
"""
Full platform seed — idempotent, safe to re-run on every deploy.

Sections
────────
1.  Specialisation catalog  (Rocket League)
2.  Coach accounts          (5 approved coaches with packages)
3.  Player accounts         (6 adult players with profiles & game prefs)
4.  Rewards catalog         (4 redeemable reward items)
5.  Teams                   (2 teams with memberships)
6.  Orders → Bookings → Sessions  (completed history for 2 players)
7.  Points transactions     (earned points from completed sessions)
8.  Coach earnings          (net earnings from completed orders)

Idempotency
───────────
Every entity is keyed on a natural unique field (email, slug, name,
order_reference, etc.).  Re-running skips anything that already exists —
nothing is updated or deleted.

Usage
─────
  cd server/
  python seed.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from sqlalchemy import func, select                          # noqa: E402
from sqlalchemy.orm import Session                           # noqa: E402

from app.core.security import hash_password                  # noqa: E402
from app.db.session import SessionLocal                      # noqa: E402
from app.models.commerce import (                            # noqa: E402
    Booking,
    CoachingPackage,
    CoachingSession,
    Order,
    Quotation,
)
from app.models.enums import (                               # noqa: E402
    AccountStatus,
    BookingStatus,
    EarningStatus,
    OrderStatus,
    PointsSourceType,
    PointsTransactionType,
    QuotationStatus,
    SessionStatus,
    SpecialisationCategory,
    TeamMemberRole,
    UserRole,
    VerificationStatus,
)
from app.models.finance import CoachEarning                  # noqa: E402
from app.models.identity import (                            # noqa: E402
    CoachProfile,
    CoachSpecialisation,
    CoachVerification,
    PlayerGame,
    PlayerProfile,
    Specialisation,
    Team,
    TeamMembership,
    User,
)
from app.models.rewards import PointsTransaction, Reward     # noqa: E402
from app.seed_specialisations import (                       # noqa: E402
    INITIAL_SPECIALISATIONS,
    seed_specialisations,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _exists(db: Session, model, **kwargs) -> bool:
    """Return True when a row matching every kwarg filter already exists."""
    stmt = select(model)
    for attr, val in kwargs.items():
        col = getattr(model, attr)
        if isinstance(val, str):
            stmt = stmt.where(func.lower(col) == val.lower())
        else:
            stmt = stmt.where(col == val)
    return db.scalar(stmt) is not None


def _get_user(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )


def _get_coach_profile(db: Session, email: str) -> CoachProfile | None:
    user = _get_user(db, email)
    if user is None:
        return None
    return db.scalar(select(CoachProfile).where(CoachProfile.user_id == user.id))


def _get_player_profile(db: Session, email: str) -> PlayerProfile | None:
    user = _get_user(db, email)
    if user is None:
        return None
    return db.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user.id))


def _ago(days: int = 0, hours: int = 0) -> datetime:
    return datetime.now(UTC) - timedelta(days=days, hours=hours)


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Coaches
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PackageSeed:
    title: str
    description: str
    price_amount: Decimal
    currency: str
    session_limit: int
    duration_days: int
    terms: str = (
        "Sessions are 60 minutes each via Discord or custom platform. "
        "24-hour cancellation notice required."
    )


@dataclass
class CoachSeed:
    email: str
    password: str
    display_name: str
    professional_bio: str
    coaching_goals: str
    experience_years: int
    availability: dict
    packages: list[PackageSeed] = field(default_factory=list)


COACHES: list[CoachSeed] = [
    # ── TEST COACH — known credentials for full-flow QA ──────────────────────
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
            "Help every student build the mechanical skills and game sense needed for "
            "at least one full rank tier improvement within their first package. "
            "Fundamentals first, flourishes second."
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
            "Transform inconsistent players into reliable team assets by sharpening "
            "decision-making skills and mechanical consistency. Master the controllable, "
            "adapt to the rest."
        ),
        experience_years=5,
        availability={
            "timezone": "America/New_York",
            "weekly": [
                {"day": "Tuesday",  "start": "17:00", "end": "21:00"},
                {"day": "Thursday", "start": "17:00", "end": "21:00"},
                {"day": "Saturday", "start": "09:00", "end": "15:00"},
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
            "Build communication skills and mechanical consistency in a safe, supportive "
            "environment where players can fail, learn, and grow. "
            "Confidence on the pitch is half the battle."
        ),
        experience_years=3,
        availability={
            "timezone": "Europe/London",
            "weekly": [
                {"day": "Monday", "start": "19:00", "end": "22:00"},
                {"day": "Friday", "start": "19:00", "end": "23:00"},
                {"day": "Sunday", "start": "14:00", "end": "20:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Duo Chemistry — 2 Sessions",
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
            "Turn replay data into actionable habits that sharpen positioning skills "
            "and decision-making. Every session ends with a written summary and "
            "a set of drills you can do in free play."
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
                title="Replay Deep-Dive — 1 Session",
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

    CoachSeed(
        email="mia.townsend@coach2earn.io",
        password="MiaT!coach2024",
        display_name="Mia Townsend",
        professional_bio=(
            "Diamond 3 Rocket League player with a background in youth gaming "
            "education. I've run Rocket League after-school programmes at three "
            "secondary schools and coached over 40 young players aged 13–18. "
            "Patience and positivity are at the core of my coaching style — "
            "I make technical concepts accessible and celebrate every improvement."
        ),
        coaching_goals=(
            "Build foundational skills and nurture the next generation of competitive "
            "Rocket League players — teaching resilience, teamwork, and healthy "
            "gaming habits along the way."
        ),
        experience_years=2,
        availability={
            "timezone": "Australia/Sydney",
            "weekly": [
                {"day": "Tuesday",  "start": "16:00", "end": "19:00"},
                {"day": "Thursday", "start": "16:00", "end": "19:00"},
                {"day": "Saturday", "start": "10:00", "end": "14:00"},
            ],
        },
        packages=[
            PackageSeed(
                title="Youth Intro Package — 3 Sessions",
                description=(
                    "Three friendly, structured sessions for players new to competitive "
                    "Rocket League. Covers core mechanics, rotation basics, and "
                    "building good in-game habits from day one."
                ),
                price_amount=Decimal("45.00"),
                currency="AUD",
                session_limit=3,
                duration_days=21,
                terms=(
                    "48-hour cancellation notice required. Sessions are recorded "
                    "for post-session review at the player's request."
                ),
            ),
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Players
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlayerSeed:
    email: str
    password: str
    display_name: str
    date_of_birth: date
    skill_level: str
    gaming_experience_years: int
    interests: list[str]
    training_goals: str
    coaching_requirements: str
    budget_amount: Decimal
    budget_currency: str


PLAYERS: list[PlayerSeed] = [
    PlayerSeed(
        email="liam.foster@coach2earn.io",
        password="LiamF!player24",
        display_name="Liam Foster",
        date_of_birth=date(1999, 3, 14),
        skill_level="Diamond 2",
        gaming_experience_years=4,
        interests=["aerial mechanics", "1v1", "ranked grind"],
        training_goals=(
            "Hit Grand Champion before the end of the current RLCS season. "
            "My main weakness is aerial car control and inconsistent 50/50s."
        ),
        coaching_requirements=(
            "Looking for a coach who can break down replays and give me a clear "
            "drill plan. Available evenings on weekdays and all day Saturday."
        ),
        budget_amount=Decimal("100.00"),
        budget_currency="USD",
    ),
    PlayerSeed(
        email="sofia.nguyen@coach2earn.io",
        password="SofiaN!RL2024",
        display_name="Sofia Nguyen",
        date_of_birth=date(2001, 7, 22),
        skill_level="Platinum 3",
        gaming_experience_years=2,
        interests=["team play", "rotation", "duos"],
        training_goals=(
            "Reach Diamond 1 with a consistent teammate. Want to understand "
            "rotation and positioning at a deeper level."
        ),
        coaching_requirements=(
            "Prefer a patient coach who explains concepts clearly. "
            "Happy to play training packs between sessions."
        ),
        budget_amount=Decimal("60.00"),
        budget_currency="USD",
    ),
    PlayerSeed(
        email="ethan.brooks@coach2earn.io",
        password="EthanB!2024rl",
        display_name="Ethan Brooks",
        date_of_birth=date(1997, 11, 5),
        skill_level="Gold 3",
        gaming_experience_years=1,
        interests=["basics", "dribbling", "kickoffs"],
        training_goals=(
            "Escape Gold and understand why I keep losing games where I feel "
            "like I'm playing well. Need help spotting my own mistakes."
        ),
        coaching_requirements=(
            "Want replay analysis more than live coaching at first. "
            "Budget is tight so value for money matters."
        ),
        budget_amount=Decimal("25.00"),
        budget_currency="EUR",
    ),
    PlayerSeed(
        email="aisha.okonkwo@coach2earn.io",
        password="Aisha!RL2024ok",
        display_name="Aisha Okonkwo",
        date_of_birth=date(2000, 5, 18),
        skill_level="Champion 1",
        gaming_experience_years=5,
        interests=["advanced mechanics", "freestyling", "ranked 2v2"],
        training_goals=(
            "Reach SSL in 2v2 with my duo partner. We plateau at C3 every "
            "season and need someone to fix our rotation overlap."
        ),
        coaching_requirements=(
            "Duo coaching sessions preferred. Coach must be SSL or ex-RLCS. "
            "Evenings and weekends only (GMT+1)."
        ),
        budget_amount=Decimal("80.00"),
        budget_currency="GBP",
    ),
    PlayerSeed(
        email="marcus.riley@coach2earn.io",
        password="MarcusR!rl24",
        display_name="Marcus Riley",
        date_of_birth=date(1995, 9, 30),
        skill_level="Diamond 1",
        gaming_experience_years=3,
        interests=["wall play", "speed mechanics", "solo queue"],
        training_goals=(
            "Clean up my wall-to-aerial transitions and stop over-rotating. "
            "I know what the issues are — I just need structured practice."
        ),
        coaching_requirements=(
            "Data-driven approach preferred. I want measurable progress between "
            "sessions, not just general tips."
        ),
        budget_amount=Decimal("150.00"),
        budget_currency="EUR",
    ),
    PlayerSeed(
        email="chloe.watts@coach2earn.io",
        password="ChloeW!rl2024",
        display_name="Chloe Watts",
        date_of_birth=date(2002, 1, 9),
        skill_level="Silver 2",
        gaming_experience_years=1,
        interests=["casual competitive", "team basics", "game sense"],
        training_goals=(
            "Just started competitive mode and want to actually understand the "
            "game. Happy to start from the very basics."
        ),
        coaching_requirements=(
            "Beginner-friendly coach who won't overwhelm me with jargon. "
            "Short sessions (45–60 min) are ideal."
        ),
        budget_amount=Decimal("50.00"),
        budget_currency="AUD",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Rewards catalog
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RewardSeed:
    name: str
    description: str
    points_cost: int


REWARDS: list[RewardSeed] = [
    RewardSeed(
        name="Free Session Voucher",
        description=(
            "Redeem for one complimentary 60-minute coaching session with any "
            "approved coach on the platform. Valid for 90 days from redemption."
        ),
        points_cost=500,
    ),
    RewardSeed(
        name="10% Package Discount",
        description=(
            "Get 10% off your next coaching package purchase. Applied automatically "
            "at checkout. Single use, valid 30 days."
        ),
        points_cost=200,
    ),
    RewardSeed(
        name="Coach2Earn Branded Merch Bundle",
        description=(
            "Receive a Coach2Earn hoodie, cap, and mouse pad delivered to your "
            "registered address. Sizes subject to availability."
        ),
        points_cost=750,
    ),
    RewardSeed(
        name="Priority Booking Access",
        description=(
            "Jump the queue — get 48-hour early access to newly listed coaching "
            "slots for your chosen coach. Valid for one calendar month."
        ),
        points_cost=300,
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Teams
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TeamMemberEntry:
    email: str
    role: TeamMemberRole


@dataclass
class TeamSeed:
    name: str
    description: str
    created_by_email: str       # must be a seeded user
    members: list[TeamMemberEntry]


TEAMS: list[TeamSeed] = [
    TeamSeed(
        name="Nitro Surge",
        description=(
            "Competitive 3v3 squad aiming for RLCS regional qualification. "
            "Founded by Liam Foster with coaching support from Jordan Blake."
        ),
        created_by_email="liam.foster@coach2earn.io",
        members=[
            TeamMemberEntry(email="liam.foster@coach2earn.io",    role=TeamMemberRole.OWNER),
            TeamMemberEntry(email="aisha.okonkwo@coach2earn.io",  role=TeamMemberRole.PLAYER),
            TeamMemberEntry(email="marcus.riley@coach2earn.io",   role=TeamMemberRole.PLAYER),
            TeamMemberEntry(email="coach.test@coach2earn.io",     role=TeamMemberRole.COACH),
        ],
    ),
    TeamSeed(
        name="Diamond Duos",
        description=(
            "A casual duo team working towards Champion rank. "
            "Coach Priya Sharma helps with rotation and communication."
        ),
        created_by_email="sofia.nguyen@coach2earn.io",
        members=[
            TeamMemberEntry(email="sofia.nguyen@coach2earn.io",   role=TeamMemberRole.OWNER),
            TeamMemberEntry(email="ethan.brooks@coach2earn.io",   role=TeamMemberRole.PLAYER),
            TeamMemberEntry(email="priya.sharma@coach2earn.io",   role=TeamMemberRole.COACH),
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Seeding functions
# ─────────────────────────────────────────────────────────────────────────────

def _seed_coach(db: Session, data: CoachSeed, rl_spec: Specialisation) -> bool:
    if _get_user(db, data.email) is not None:
        print(f"  skip  {data.email}")
        return False

    user = User(
        id=uuid4(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=UserRole.COACH,
        account_status=AccountStatus.ACTIVE,
        date_of_birth=date(1992, 6, 15),  # generic adult DOB for seeded coaches
    )
    db.add(user)
    db.flush()

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
    db.flush()

    db.add(CoachSpecialisation(
        coach_profile_id=profile.id,
        specialisation_id=rl_spec.id,
    ))
    db.add(CoachVerification(
        id=uuid4(),
        coach_profile_id=profile.id,
        status=VerificationStatus.APPROVED,
        submitted_at=_ago(days=30),
        reviewed_at=_ago(days=28),
        review_notes="Auto-approved by seed script for demo purposes.",
    ))
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
    print(f"  ✓  coach   {data.email}  ({data.display_name})")
    return True


def _seed_player(db: Session, data: PlayerSeed, rl_spec: Specialisation) -> bool:
    if _get_user(db, data.email) is not None:
        print(f"  skip  {data.email}")
        return False

    user = User(
        id=uuid4(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=UserRole.PLAYER,
        account_status=AccountStatus.ACTIVE,
        date_of_birth=data.date_of_birth,
    )
    profile = PlayerProfile(
        id=uuid4(),
        skill_level=data.skill_level,
        gaming_experience_years=data.gaming_experience_years,
        interests=data.interests,
        training_goals=data.training_goals,
        coaching_requirements=data.coaching_requirements,
        budget_amount=data.budget_amount,
        budget_currency=data.budget_currency,
        games=[PlayerGame(specialisation=rl_spec)],
    )
    user.player_profile = profile
    db.add(user)
    db.commit()
    print(f"  ✓  player  {data.email}  ({data.display_name})")
    return True


def _seed_reward(db: Session, data: RewardSeed) -> bool:
    if _exists(db, Reward, name=data.name):
        print(f"  skip  reward '{data.name}'")
        return False
    db.add(Reward(
        id=uuid4(),
        name=data.name,
        description=data.description,
        points_cost=data.points_cost,
        is_active=True,
    ))
    db.commit()
    print(f"  ✓  reward  '{data.name}'  ({data.points_cost} pts)")
    return True


def _seed_team(db: Session, data: TeamSeed) -> bool:
    if _exists(db, Team, name=data.name):
        print(f"  skip  team '{data.name}'")
        return False
    creator = _get_user(db, data.created_by_email)
    if creator is None:
        print(f"  ✗  team '{data.name}' — creator {data.created_by_email} not found", file=sys.stderr)
        return False

    team = Team(id=uuid4(), name=data.name, description=data.description, created_by=creator)
    db.add(team)
    db.flush()

    for entry in data.members:
        member_user = _get_user(db, entry.email)
        if member_user is None:
            print(f"  ✗  team member {entry.email} not found — skipping member", file=sys.stderr)
            continue
        db.add(TeamMembership(
            id=uuid4(),
            team_id=team.id,
            user_id=member_user.id,
            role=entry.role,
        ))

    db.commit()
    print(f"  ✓  team   '{data.name}'  ({len(data.members)} member(s))")
    return True


def _seed_order_history(db: Session, rl_spec: Specialisation) -> None:
    """
    Create two completed order→booking→session chains so earnings, points,
    and booking history are populated for demo purposes.

    Chain A: Liam Foster booked Jordan Blake's 'Starter Boost' (3 sessions)
    Chain B: Ethan Brooks booked Carlos Vidal's 'Replay Deep-Dive' (1 session)
    """
    COMMISSION_RATE = Decimal("0.15")   # 15% platform commission

    chains = [
        {
            "player_email":  "liam.foster@coach2earn.io",
            "coach_email":   "coach.test@coach2earn.io",
            "package_title": "Starter Boost — 3 Sessions",
            "order_ref":     "C2E-SEED000000000001",
            "sessions_ago":  [14, 10, 6],    # days ago each session completed
            "points_each":   50,
        },
        {
            "player_email":  "ethan.brooks@coach2earn.io",
            "coach_email":   "carlos.vidal@coach2earn.io",
            "package_title": "Replay Deep-Dive — 1 Session",
            "order_ref":     "C2E-SEED000000000002",
            "sessions_ago":  [7],
            "points_each":   50,
        },
    ]

    for chain in chains:
        # Skip if order already exists
        if _exists(db, Order, order_reference=chain["order_ref"]):
            print(f"  skip  order {chain['order_ref']}")
            continue

        player_profile = _get_player_profile(db, chain["player_email"])
        coach_profile  = _get_coach_profile(db, chain["coach_email"])
        player_user    = _get_user(db, chain["player_email"])

        if not player_profile or not coach_profile or not player_user:
            print(
                f"  ✗  order {chain['order_ref']} — missing player or coach profile",
                file=sys.stderr,
            )
            continue

        pkg = db.scalar(
            select(CoachingPackage).where(
                CoachingPackage.coach_profile_id == coach_profile.id,
                CoachingPackage.title == chain["package_title"],
            )
        )
        if pkg is None:
            print(
                f"  ✗  package '{chain['package_title']}' not found for {chain['coach_email']}",
                file=sys.stderr,
            )
            continue

        # Quotation (already accepted — expires_at must be > created_at per DB
        # constraint, so we set it 1 hour ahead; the quotation was accepted
        # immediately so the historical expiry window is irrelevant)
        quotation = Quotation(
            id=uuid4(),
            package_id=pkg.id,
            player_profile_id=player_profile.id,
            coach_profile_id=coach_profile.id,
            package_title=pkg.title,
            package_description=pkg.description,
            price_amount=pkg.price_amount,
            currency=pkg.currency,
            session_limit=pkg.session_limit,
            duration_days=pkg.duration_days,
            terms=pkg.terms,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            status=QuotationStatus.ACCEPTED,
        )
        db.add(quotation)
        db.flush()

        # Order
        order = Order(
            id=uuid4(),
            order_reference=chain["order_ref"],
            quotation_id=quotation.id,
            package_title=pkg.title,
            package_description=pkg.description,
            price_amount=pkg.price_amount,
            currency=pkg.currency,
            session_limit=pkg.session_limit,
            duration_days=pkg.duration_days,
            terms=pkg.terms,
            status=OrderStatus.COMPLETED,
        )
        db.add(order)
        db.flush()

        # Booking
        booking = Booking(
            id=uuid4(),
            order_id=order.id,
            status=BookingStatus.COMPLETED,
            confirmed_at=_ago(days=max(chain["sessions_ago"]) + 2),
            completed_at=_ago(days=min(chain["sessions_ago"])),
        )
        db.add(booking)
        db.flush()

        # Sessions + points + earnings
        per_session_gross = (pkg.price_amount / pkg.session_limit).quantize(Decimal("0.01"))
        commission        = (per_session_gross * COMMISSION_RATE).quantize(Decimal("0.01"))
        net               = per_session_gross - commission

        for seq, days_ago in enumerate(chain["sessions_ago"], start=1):
            started  = _ago(days=days_ago, hours=2)
            ended    = _ago(days=days_ago, hours=1)

            session = CoachingSession(
                id=uuid4(),
                booking_id=booking.id,
                sequence_number=seq,
                starts_at=started,
                ends_at=ended,
                status=SessionStatus.COMPLETED,
                confirmed_at=started,
                completed_at=ended,
                coach_notes=f"Session {seq} completed. Player showed good progress.",
            )
            db.add(session)
            db.flush()

            # Points transaction (player earns points per completed session)
            pt_ref = f"session:{session.id}"
            if not _exists(db, PointsTransaction, source_reference=pt_ref):
                db.add(PointsTransaction(
                    id=uuid4(),
                    user_id=player_user.id,
                    session_id=session.id,
                    transaction_type=PointsTransactionType.EARNED,
                    source_type=PointsSourceType.SESSION,
                    source_reference=pt_ref,
                    points_delta=chain["points_each"],
                    description=f"Points earned for completing coaching session {seq}.",
                ))

            # Coach earning
            if not _exists(db, CoachEarning, session_id=session.id):
                db.add(CoachEarning(
                    id=uuid4(),
                    coach_profile_id=coach_profile.id,
                    order_id=order.id,
                    session_id=session.id,
                    gross_amount=per_session_gross,
                    commission_amount=commission,
                    net_amount=net,
                    currency=pkg.currency,
                    status=EarningStatus.AVAILABLE,
                ))

        db.commit()
        print(
            f"  ✓  order  {chain['order_ref']}  "
            f"({len(chain['sessions_ago'])} session(s) completed)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    # ── 1. Specialisation catalog ─────────────────────────────────────────────
    print("── 1. Specialisation catalog ────────────────────────────────────────")
    try:
        with SessionLocal() as db:
            count = seed_specialisations(db, INITIAL_SPECIALISATIONS)
        print(f"  ✓  {count} specialisation(s) in catalog")
    except Exception as exc:
        print(f"  ✗  specialisation seed failed: {exc}", file=sys.stderr)
        return 1

    # Fetch Rocket League spec (re-used by every coach and player)
    with SessionLocal() as db:
        rl_spec = db.scalar(
            select(Specialisation).where(
                Specialisation.slug == "rocket-league",
                Specialisation.category == SpecialisationCategory.GAME,
            )
        )
    if rl_spec is None:
        print("  ✗  rocket-league specialisation missing after seed", file=sys.stderr)
        return 1

    # ── 2. Coaches ────────────────────────────────────────────────────────────
    print()
    print("── 2. Coaches ───────────────────────────────────────────────────────")
    for coach_data in COACHES:
        with SessionLocal() as db:
            spec = db.get(Specialisation, rl_spec.id)
            _seed_coach(db, coach_data, spec)

    # ── 3. Players ────────────────────────────────────────────────────────────
    print()
    print("── 3. Players ───────────────────────────────────────────────────────")
    for player_data in PLAYERS:
        with SessionLocal() as db:
            spec = db.get(Specialisation, rl_spec.id)
            _seed_player(db, player_data, spec)

    # ── 4. Rewards catalog ────────────────────────────────────────────────────
    print()
    print("── 4. Rewards catalog ───────────────────────────────────────────────")
    for reward_data in REWARDS:
        with SessionLocal() as db:
            _seed_reward(db, reward_data)

    # ── 5. Teams ──────────────────────────────────────────────────────────────
    print()
    print("── 5. Teams ─────────────────────────────────────────────────────────")
    for team_data in TEAMS:
        with SessionLocal() as db:
            _seed_team(db, team_data)

    # ── 6–8. Orders, sessions, points, earnings ───────────────────────────────
    print()
    print("── 6. Orders / bookings / sessions / earnings / points ──────────────")
    with SessionLocal() as db:
        spec = db.get(Specialisation, rl_spec.id)
        _seed_order_history(db, spec)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("═" * 62)
    print("  Seed complete. Platform is ready with:")
    print(f"    • {len(COACHES)} coaches  (Rocket League, verified & approved)")
    print(f"    • {len(PLAYERS)} players  (adult accounts, profiles & game prefs)")
    print(f"    • {len(REWARDS)} rewards  (points catalog)")
    print(f"    • {len(TEAMS)} teams   (with memberships)")
    print( "    • 2 completed order histories  (sessions, earnings, points)")
    print()
    print("  TEST COACH CREDENTIALS  (full-flow QA)")
    print("─" * 62)
    tc = COACHES[0]
    print(f"  Email    : {tc.email}")
    print(f"  Password : {tc.password}")
    print(f"  Role     : coach | Status: active | Verified: approved")
    print()
    print("  TEST PLAYER CREDENTIALS")
    print("─" * 62)
    tp = PLAYERS[0]
    print(f"  Email    : {tp.email}")
    print(f"  Password : {tp.password}")
    print(f"  Role     : player | Rank: {tp.skill_level}")
    print("═" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
