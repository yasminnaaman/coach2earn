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

## Render start command

Use `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the web service start
command and configure `DATABASE_URL` as a secret environment variable. Render's
health check path should be `/api/v1/health`. Apply migrations with
`alembic upgrade head` as a release/deploy command.
