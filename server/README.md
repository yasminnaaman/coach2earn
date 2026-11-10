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

Public registration always creates a player and rejects extra fields such as a
requested role. Passwords are Argon2 hashed and neither password nor hash is
returned. `GET /api/v1/auth/me` requires an active bearer token. Reusable
`require_roles(...)` dependencies protect future module endpoints. Admins can
approve a player through `POST /api/v1/admin/users/{user_id}/promote-to-coach`;
the role change, coach profile and approved verification record commit in one
transaction.

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
```

Roll back the latest revision with `alembic downgrade -1`; return to an empty
schema with `alembic downgrade base`. Generate a migration after changing a
model with `alembic revision --autogenerate -m "describe the schema change"`,
then review the generated migration before applying it. Alembic reads the
database URL from the same `DATABASE_URL` setting as the application.

The initial migration contains all Phase 2 tables and a PostgreSQL trigger that
rejects updates and deletes from the points ledger. SQLite tests cover portable
model constraints and migration upgrade/downgrade behavior; run migrations
against PostgreSQL before deployment to validate PostgreSQL-specific behavior.

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

## Render start command

Use `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the web service start
command and configure `DATABASE_URL` as a secret environment variable. Render's
health check path should be `/api/v1/health`. Apply migrations with
`alembic upgrade head` as a release/deploy command.
