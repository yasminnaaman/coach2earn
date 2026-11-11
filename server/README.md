# Coach2Earn backend

The backend provides the FastAPI foundation, environment-based settings, a
synchronous SQLAlchemy connection to PostgreSQL, and a database-aware health
endpoint. SQLAlchemy models and Alembic migrations define the user, coaching,
booking, points, rewards and financial-record schemas.

## Local setup

From the `server` directory, create and activate a virtual environment, then
install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` in `.env` to a PostgreSQL database you can access. The
default is for a local PostgreSQL instance. Do not commit `.env` or production
credentials.

Start the API from the `server` directory:

```bash
uvicorn app.main:app --reload
```

To start it from the repository root, add `server` to Uvicorn's application
search path:

```bash
uvicorn --app-dir server --env-file server/.env app.main:app --reload
```

This keeps the backend's `app`, `ai` and `passport` imports consistent. Running
`uvicorn server.app.main:app` from the repository root is not supported because
backend modules import one another through the top-level `app` package.

The OpenAPI interface is available at `/docs`; the deployment health check is
`GET /api/v1/health`. It returns HTTP 200 when PostgreSQL responds to `SELECT 1`
and HTTP 503 when the database is unavailable.

## Authentication

Configure `JWT_SECRET_KEY` in `.env` or the deployment environment. Generate a
random value with `openssl rand -hex 32`; the application rejects missing,
short, and obvious placeholder secrets when token operations are requested.
`ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 30 and accepts values from 1 to 1440.
The signing algorithm is fixed to HS256. Tokens contain only the user ID and
standard issue, issuer and expiry claims; current role and account status are
loaded from PostgreSQL on each authenticated request.

Public registration always creates a player account and rejects extra fields
such as a requested role. Passwords are Argon2 hashed and neither password nor hash is
returned. `GET /api/v1/auth/me` requires an active bearer token. Reusable
`require_roles(...)` dependencies protect future module endpoints. Admins can
approve a player through `POST /api/v1/admin/users/{user_id}/promote-to-coach`;
the role change, coach profile and approved verification record commit in one
transaction.

Registration requires a date of birth. Adult players receive a player profile
at registration. For players under 18, registration stores guardian contact in
a private consent record with `pending` status and does not create a player
profile. Such players can authenticate and see the consent status through
`GET /api/v1/auth/me`, but player-only dependencies deny access until an active
administrator records a `verified` decision. Administrators review consent at
`POST /api/v1/admin/users/{user_id}/guardian-consent`, supplying an evidence
reference; every decision records the reviewer and UTC timestamp. Rejected
consent can be resubmitted by its account owner using
`PUT /api/v1/auth/guardian-consent`; the earlier decision remains in the audit
history. Guardian contact and date of birth are never returned by user APIs.
Legacy player accounts without a recorded date of birth can set it once via
`POST /api/v1/auth/age-verification`; affected minors are held from player
access until consent is verified. Existing profile and history records are
preserved, but protected player-role dependencies remain unavailable.

Existing coach profiles can have their verification reviewed through
`POST /api/v1/admin/users/{user_id}/coach-verification` with status
`approved`, `rejected` or `needs_more_evidence`. Decisions append verification
records with the reviewer and UTC review time; administrators cannot review
their own coach profile. Initial coach promotion continues to create an
approved profile and verification record atomically.

Guardian verification currently represents a manual trusted-administrator
review against an evidence reference; it does not verify guardian identity or
consent through an external provider. Product and legal owners must define the
acceptable evidence, guardian consent language/versioning, retention policy,
withdrawal workflow and any verification provider before launch. Until then,
the backend fails closed with pending consent and does not activate a minor's
player profile.

### One-time initial admin bootstrap

The first admin is provisioned by a trusted operator, not through public
registration. From `server/`, run:

```bash
python -m app.cli bootstrap-admin
```

The command requires PostgreSQL, prompts for the email if `--email` is omitted,
and reads the password twice through hidden terminal prompts. It never accepts a
password argument or prints password/hash values. A PostgreSQL transaction-level
advisory lock ensures only one concurrent bootstrap can succeed; the command
refuses to run if an admin already exists or the email is already registered.
After bootstrap, admin role assignment remains restricted to trusted operator
workflows; public registration cannot create admins.

## Database migrations

From `server/`, configure `DATABASE_URL` in the environment or in the ignored
local `.env` file, then apply the schema:

```bash
alembic upgrade head
alembic current
python -m app.seed_specialisations
```

The idempotent specialisation seeder adds the documented initial game,
Rocket League (`game`, `rocket-league`). It does not overwrite conflicting
catalog data and can be safely rerun. Other games mentioned as product examples
are not seeded until the catalog is confirmed.

Roll back the latest revision with `alembic downgrade -1`; return to an empty
schema with `alembic downgrade base`. Generate a migration after changing a
model with `alembic revision --autogenerate -m "describe the schema change"`,
then review the generated migration before applying it. Alembic reads the
database URL from the same `DATABASE_URL` setting as the application.

The initial migration contains all Phase 2 tables and a PostgreSQL trigger that
rejects updates and deletes from the points ledger. A follow-up migration adds
canonical specialisation checks and equivalent SQLite ledger triggers for
supplementary tests. SQLite tests cover portable model constraints and
migration upgrade/downgrade behavior; run migrations against PostgreSQL before
deployment to validate PostgreSQL-specific behavior.

## Phase 2 data model

- A user has one platform role. Player and coach profiles are one-to-one user
  extensions; a user may belong to many teams through `TeamMembership`.
- A coach owns many packages, qualifications, verification records and
  specialisations. Package edits do not change quotations: each quotation
  stores the quoted package terms and price, and each order stores a second
  snapshot of those accepted terms.
- An order has zero or one booking. A booking has zero or many coaching
  sessions, each identified by its sequence number within the booking.
- A player points balance is derived from signed `PointsTransaction` rows.
  Every row has a typed source/reference, source references are unique, and a
  session can have at most one points row. Corrections are compensating rows.
- Coach earnings record gross value, commission and net value. Payout records
  are separate and connect to earnings through `PayoutAllocation`, so a payout
  never duplicates an earning. These tables only record financial state; they
  do not initiate or process payments.

## Phase 4 profile API

Authenticated profile routes use the Phase 3 bearer-token authentication and
derive the owner from the token. They do not accept user IDs in profile request
bodies. Player routes are `/api/v1/profiles/player`; coach routes are
`/api/v1/profiles/coach`. Both support `POST` for profile creation, `GET` for
the authenticated profile and `PATCH` for updates. Profile creation returns
`409` when registration or coach promotion already created that profile.

Player game preferences and coach specialisations reference the seeded
`specialisations` table. Coach discovery is public at `/api/v1/coaches` and
`/api/v1/coaches/{coach_profile_id}`. Results require an active coach account,
an approved coach profile, a non-empty biography, at least one game
specialisation and at least one active package. Filters include
`specialisation_id`, `experience_years_min`, free-text `goal`,
`budget_amount`/`budget_currency`, `offset` and `limit`. Budget matching uses
the package total divided by its session limit, compares only the stated
currency, and performs no exchange-rate conversion.

Coaches submit private qualification evidence at
`/api/v1/profiles/coach/qualifications`; only the owning coach and admins can
read it. Admins review pending submissions through
`/api/v1/admin/qualifications` and
`/api/v1/admin/qualifications/{qualification_id}/review`. Each decision stores
reviewer identity, timestamp, status and notes. Public coach responses omit
qualification details, credential references and evidence URLs. Existing
coach verification decisions remain on the Phase 3
`/api/v1/admin/users/{user_id}/coach-verification` route.

## Render start command

Use `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the web service start
command and configure `DATABASE_URL` as a secret environment variable. Render's
health check path should be `/api/v1/health`. Apply migrations with
`alembic upgrade head` as a release/deploy command.

## Phase 5 packages and orders

Authenticated package discovery is public at `GET /api/v1/packages` and
`GET /api/v1/packages/{package_id}`. Coaches manage their packages at
`POST /api/v1/coaches/me/packages` and `PUT /api/v1/coaches/me/packages/{id}`.

Players create a 15-minute price snapshot at `POST /api/v1/quotations`, then
accept it at `POST /api/v1/orders` which creates an immutable order record. The
order includes a stable public reference (`C2E-<16 hex chars>`). Orders are
listed at `GET /api/v1/orders` and retrieved individually at
`GET /api/v1/orders/{id}`. Players see their own orders; coaches see orders
linked to their profile; admins see all.

Order creation generates `status: pending_payment`. Payment confirmation (status
transition to `confirmed`) is handled by the payment integration owner; clients
cannot self-promote an order to `confirmed` status.

## Phase 6 bookings and scheduling

### Coach availability

Coaches publish recurring or one-off availability windows:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/coaches/me/availability` | Create an availability window |
| `PUT` | `/api/v1/coaches/me/availability/{id}` | Update an availability window |
| `DELETE` | `/api/v1/coaches/me/availability/{id}` | Soft-delete an availability window |
| `GET` | `/api/v1/coaches/{coach_profile_id}/availability` | List a coach's active windows |
| `GET` | `/api/v1/coaches/{coach_profile_id}/slots` | Enumerate open slots (query: `from_dt`, `to_dt`) |

A window is either **recurring** (`weekday`: 1=Mon … 7=Sun) or **one-off**
(`specific_date`). Exactly one must be provided. `starts_at_utc` and
`ends_at_utc` are HH:MM UTC strings. The maximum slot query range is 60 days.

### Booking management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/bookings` | Create a booking for a confirmed order |
| `GET` | `/api/v1/bookings` | List the authenticated user's bookings |
| `GET` | `/api/v1/bookings/{id}` | Retrieve a booking |
| `PATCH` | `/api/v1/bookings/{id}/status` | Transition: `confirmed` → `completed` / `cancelled` |
| `PATCH` | `/api/v1/bookings/{id}/sessions/{sid}/status` | Transition session status |

**Booking rules:**
- A booking can only be created for an order with status `confirmed` (paid).
- One booking per order (enforced at DB level).
- Overlapping session times are rejected.
- State transitions follow a strict directed graph: `pending → confirmed → completed`.
- Cancellation is allowed from `pending` or `confirmed`.

**Booking status graph:**
```
pending → confirmed → completed
pending → cancelled
confirmed → cancelled
```

**Session status graph:**
```
scheduled → confirmed → completed
scheduled → cancelled
confirmed → cancelled
```

### Scheduling integrity

- Concurrent booking requests for the same coach/time slot are protected by
  `SELECT … FOR UPDATE` row-level locking on PostgreSQL.
- Cancelled sessions are excluded from overlap checks so rescheduling is possible.
- Double-booking at DB level is prevented by the unique constraint on `(order_id)`.

## CORS configuration

The `CORS_ORIGINS` environment variable accepts a comma-separated list of
allowed frontend origins. The application defaults to
`http://localhost:5173,http://localhost:3000` for local development. For
production, set it to the deployed frontend URL:

```
CORS_ORIGINS=https://your-frontend.onrender.com
```

## Frontend integration

The frontend must send `Authorization: Bearer <token>` on all authenticated
requests. Tokens are obtained from `POST /api/v1/auth/login` and expire in
`ACCESS_TOKEN_EXPIRE_MINUTES` minutes (default 30). Use the `expires_in` field
in the token response to manage refresh timing.

Logout is client-side only: discard the stored token. The backend does not
maintain a token revocation list.

### Coach listing response structure

`GET /api/v1/coaches` returns:

```json
{
  "id": "uuid",
  "professional_bio": "string",
  "coaching_goals": "string | null",
  "experience_years": 0,
  "verified": true,
  "specialisations": [{"id": "uuid", "category": "game", "name": "string", "slug": "string"}],
  "packages": [{"title": "string", "price_per_session": "12.50", "currency": "USD", "session_limit": 5}]
}
```

**Outstanding external dependencies (AI/matching owner — Yasmin):**
- `endorsementCount` — not currently persisted in the backend schema. The backend
  exposes no endorsement table. The AI/matching owner must define the data source,
  supply the API contract and implement storage before this field can be served.
- `score` / `reason` — AI ranking and recommendation reasoning. Owned by the
  AI/matching team. The backend will add a computed or stored field once the
  contract is confirmed.

**Do not invent these values on the frontend.** Omit them until the owning team
delivers the agreed data source.

## Payment integration contract

PayPal integration is owned by a separate teammate. The backend exposes:

- Orders are created with `status: pending_payment`.
- The payment callback or webhook must transition the order to `status: confirmed`
  by calling a trusted server-side payment verification flow.
- **Clients must never be allowed to set order status directly.**
- Booking creation is blocked until `status: confirmed` to prevent booking
  without payment.

**Outstanding dependencies (payment integration owner):**
1. Implement the PayPal webhook endpoint that verifies the payment and updates
   order status to `confirmed`.
2. Ensure the webhook validates the PayPal signature before updating state.
3. Do not add another payment provider.

## Required environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `JWT_SECRET_KEY` | Yes | Random 32+ byte hex secret (`openssl rand -hex 32`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token TTL in minutes (default: 30, max: 1440) |
| `JWT_ISSUER` | No | JWT issuer claim (default: `coach2earn`) |
| `CORS_ORIGINS` | No | Comma-separated frontend origins (default: localhost dev ports) |

## PostgreSQL setup

```bash
createdb coach2earn
cd server
alembic upgrade head   # applies all migrations
python -m app.seed_specialisations
```

### PostgreSQL verification tests

Set `TEST_DATABASE_URL` to a disposable PostgreSQL database and run:

```bash
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost/coach2earn_test \
  python -m pytest tests/ -v
```

This activates the PostgreSQL-only test markers that verify:
- Case-insensitive email uniqueness via expression-based index
- `order_reference` unique constraint
- `coach_availability` table existence and type-exclusivity constraint
- Concurrent booking protection via row-level locking

The `uq_users_email_lower` index is expression-based and SQLite does not support
it; the SQLite test suite emits a reflection warning but still enforces the
constraint through the ORM validator.

## Render deployment

### Service configuration

| Setting | Value |
|---------|-------|
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Deploy/release command | `alembic upgrade head` |
| Health check path | `/api/v1/health` |

### Required secret environment variables on Render

```
DATABASE_URL=<Render PostgreSQL internal URL>
JWT_SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://<your-frontend-service>.onrender.com
```

### Frontend environment variable

Set in the frontend's Render environment or `.env.production`:

```
VITE_API_URL=https://<your-backend-service>.onrender.com
```

The frontend API client must read `import.meta.env.VITE_API_URL` and must not
target `localhost` in production builds. Verify no production code contains
hardcoded `localhost` URLs.

**Deployment status: NOT YET VERIFIED.** The backend has not been confirmed
deployed to Render in this environment. The configuration above is complete and
correct; the deployment owner must apply it and verify the live URL.

