# GateTix: Event Ticketing API

GateTix is the backend API for an event ticketing platform. Organisers create events with ticket tiers, attendees reserve and buy tickets, and staff check tickets in at the venue.

It is built around three hard problems: **never selling more tickets than exist** (even when buyers click at the same instant), **reservations that expire** and give their tickets back, and **single-use, unguessable ticket codes**. How each one is solved is explained below and proven by tests.

| | |
|---|---|
| **Live API** | `<LIVE_URL>` |
| **Swagger docs** | `<LIVE_URL>/docs` |
| **Health check** | `<LIVE_URL>/api/v1/health` |
| **Repository** | https://github.com/Duke-James-teky/GateTix |

## Tech stack

Python 3.11+ (developed on 3.14), FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT (PyJWT), Argon2 password hashing, pytest.

SQLAlchemy is pinned to `>=2.0,<2.1` (see `requirements.txt`).

## Roles

| Role | How you get it | What you can do |
|---|---|---|
| **Visitor** | Not logged in | Browse events, register, log in |
| **Attendee** | Register (automatic) | Everything a visitor can, plus apply to become an organiser, reserve and buy tickets, view orders and tickets, request refunds |
| **Organiser** | Apply as an attendee, then an admin approves | Everything an attendee can, plus create, edit, publish and cancel their own events and tiers, check tickets in, view sales reports |
| **Admin** | Promoted directly in the database | Approve or reject organiser applications, suspend or restore events, view platform statistics |

A new account is always an attendee. There is no way to register as an organiser or admin.

## Demo logins

These accounts exist on the live demo database. Use **Authorize** in Swagger after logging in.

| Role | Email | Password |
|---|---|---|
| Attendee | `demo.attendee@example.com` | `DemoPass123` |
| Organiser | `demo.organiser@example.com` | `DemoPass123` |
| Admin | `demo.admin@example.com` | `DemoPass123` |

These are demo-only credentials for a demo database.

## Running it locally

**1. Get the code and a virtual environment**

```bash
git clone https://github.com/Duke-James-teky/GateTix.git
cd GateTix
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash. On Mac/Linux: source venv/bin/activate
python -m pip install -r requirements.txt
```

**2. Create two PostgreSQL databases** (one for the app, one for tests)

```bash
psql -U postgres -c "CREATE DATABASE gatetix;"
psql -U postgres -c "CREATE DATABASE gatetix_test;"
```

**3. Configure the environment**

```bash
cp .env.example .env
```

Open `.env` and fill in your real database password (in both URLs) and a secret key (`python -c "import secrets; print(secrets.token_hex(32))"`). If your password has special characters such as `@` or `#`, URL-encode them (`@` becomes `%40`). If PostgreSQL does not run on port 5432 on your machine, change the port in both URLs too.

**4. Build the database tables**

```bash
python -m alembic upgrade head
```

**5. Start the server**

```bash
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

**6. Make an admin (local only)**

Register a normal account, then promote it in the database:

```bash
psql -U postgres -d gatetix -c "UPDATE users SET role = 'admin' WHERE email = 'you@example.com';"
```

## Environment variables

Listed in `.env.example`. Nothing secret is committed to Git.

| Variable | Meaning | Example |
|---|---|---|
| `APP_NAME` | Name shown by the app | `GateTix` |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `DATABASE_URL` | PostgreSQL connection string for the app | `postgresql+psycopg2://postgres:pw@localhost:5432/gatetix` |
| `TEST_DATABASE_URL` | A separate PostgreSQL database used only by the tests | `postgresql+psycopg2://postgres:pw@localhost:5432/gatetix_test` |
| `SECRET_KEY` | Private value used to sign JWTs. Keep it secret | 64 random hex characters |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login token lasts | `60` |
| `RESERVATION_HOLD_MINUTES` | How long a reservation holds tickets | `10` |

## Running the tests

```bash
python -m pytest -v
```

The suite has **103 tests**. It uses a real PostgreSQL database named by `TEST_DATABASE_URL`, rebuilt from the Alembic migrations at the start of every run (so it also proves the migrations build the whole schema from empty). Every table is emptied before each test. The test setup refuses to run if the test database is the same as the real one, or if its name does not contain `test`.

| File | What it covers |
|---|---|
| `test_concurrency.py` | Core challenge: 12 buyers racing for 5 tickets, two buyers for the last ticket, double payment, five scanners on one ticket |
| `test_expiry.py` | Core challenge: expired holds are released, late payment is refused |
| `test_reservations.py` | Sales window, max per order, one pending reservation per event, free tiers |
| `test_checkin.py` | Check-in rules, double scan, refunded tickets, sales report |
| `test_payments.py`, `test_refunds.py` | Payment, refunds, event cancellation |
| `test_events.py`, `test_tiers.py` | Events, publishing, browsing and filters, tier rules |
| `test_organisers.py`, `test_admin.py`, `test_auth.py`, `test_tickets.py` | Applications, admin tools, login, own-data lists |

## API overview

Every path is under `/api/v1`. Full details, examples and error responses are in Swagger at `/docs`.

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/health` | Anyone | API and database health |
| POST | `/auth/register` | Anyone | Create an attendee account |
| POST | `/auth/login` | Anyone | Get a JWT access token |
| GET | `/auth/me` | Logged in | Show the current account *(added)* |
| POST | `/organisers/apply` | Attendee | Apply to become an organiser |
| GET | `/events` | Anyone | Browse upcoming published events (paginated, filters) |
| GET | `/events/{event_id}` | Anyone | Event with its tiers and remaining tickets |
| POST | `/events` | Organiser | Create a draft event |
| PATCH | `/events/{event_id}` | Owning organiser | Update an event |
| POST | `/events/{event_id}/publish` | Owning organiser | Publish an event |
| POST | `/events/{event_id}/cancel` | Owning organiser | Cancel and refund every paid order |
| POST | `/events/{event_id}/tiers` | Owning organiser | Add a ticket tier |
| PATCH | `/tiers/{tier_id}` | Owning organiser | Update a tier within the rules |
| GET | `/events/{event_id}/report` | Owning organiser | Sales per tier |
| POST | `/events/{event_id}/check-in` | Owning organiser | Check in a ticket by code |
| POST | `/orders` | Attendee, organiser | Reserve tickets for 10 minutes |
| GET | `/orders` | Attendee, organiser | Own orders (paginated) |
| POST | `/orders/{order_id}/pay` | Order's owner | Simulated payment, issues tickets |
| POST | `/orders/{order_id}/refund` | Order's owner | Refund a paid order |
| GET | `/tickets` | Attendee, organiser | Own tickets with codes (paginated) |
| GET | `/admin/organisers` | Admin | List organiser applications (paginated) *(added)* |
| PATCH | `/admin/organisers/{application_id}` | Admin | Approve or reject an application |
| PATCH | `/admin/events/{event_id}` | Admin | Suspend or restore an event |
| GET | `/admin/stats` | Admin | Platform statistics |

Errors are JSON with a clear message, for example `{"detail": "Sold out"}`. Status codes used: 400 (a business rule is broken), 401 (not logged in), 403 (not allowed), 404 (not found), 409 (conflicts with the current state), 422 (invalid input).

## Project structure

```
app/
  main.py              app entrypoint, router registration
  core/                config, security (hashing + JWT), dependencies, exceptions
  database/            engine, session, declarative base
  models/              SQLAlchemy models and enums
  schemas/             Pydantic request and response shapes
  services/            business logic (auth, events, tiers, reservations, payments,
                       refunds, tickets, check-in, reports, organisers, admin)
  routes/              thin HTTP layer
  utils/               ticket codes, pagination
alembic/               database migrations
tests/                 pytest suite
```

Routes only receive requests and call services. Services hold every business rule. Access rules (login, role, ownership) are FastAPI dependencies in `app/core/dependencies.py`.

## Data model

| Table | Key fields |
|---|---|
| `users` | id, name, email (unique), hashed_password, role, is_active |
| `organiser_applications` | id, user_id, organisation_name, status, reviewed_by |
| `events` | id, organiser_id, title, description, venue, city, category, starts_at, ends_at, status |
| `ticket_tiers` | id, event_id, name, price_kobo, quantity, sold, reserved, sales_start, sales_end, max_per_order |
| `orders` | id, attendee_id, tier_id, **event_id**, quantity, total_kobo, status, expires_at, created_at |
| `tickets` | id, order_id, code (unique), status, checked_in_at |

Prices are whole **kobo** stored as `BIGINT`, never floats. Statuses and roles are stored as short text with a `CHECK` constraint. Every table change is an Alembic migration.

**Database constraints**

- `ticket_tiers`: `sold + reserved <= quantity`; no negative counters or price; positive quantity and max per order; `sales_end > sales_start`; unique tier name per event
- `events`: `ends_at > starts_at`
- `orders`: positive quantity; no negative total; a pending order always has an `expires_at`
- `tickets`: unique `code`; a `used` ticket always has `checked_in_at`
- Partial unique indexes: one pending application per user, and one pending order per attendee per event

### Changes and additions beyond the brief

- **`orders.event_id`** was added. The brief's rule "one pending reservation per attendee per event" cannot be enforced by the database without it. A partial unique index on `(attendee_id, event_id) WHERE status = 'pending'` makes the rule hold even when two requests race.
- Added endpoints: `GET /auth/me` and `GET /admin/organisers` (admins need a way to find application ids).
- Path parameters are named `{event_id}`, `{tier_id}`, `{order_id}` and `{application_id}`.
- Extra constraints listed above (unique tier name per event, one pending application per user).

## How the core challenges are solved

### 1. No overselling, even under simultaneous requests

Reserving locks the ticket tier's row with `SELECT ... FOR UPDATE` inside a transaction (`reservation_service.reserve_tickets`). Buyers of the same tier queue behind the lock, then read the up-to-date `sold` and `reserved` counts, check there is room, and only then reserve. Exactly one of two simultaneous buyers can take the last ticket, because the second one waits, then reads the new count and is refused.

A database `CHECK (sold + reserved <= quantity)` is a second safety net: even a bug in the code could not make the database store an oversold tier.

Other services that change tier counters (payment, refunds, event cancellation, tier updates) follow the same rule: lock first, then check, then write. Locks are always taken in the same order (tiers in id order, then orders) so two requests can never wait on each other forever.

**Proven by:** `test_two_buyers_racing_for_the_last_ticket_get_exactly_one` and `test_many_buyers_racing_never_sell_more_than_exists` (12 threads, 5 tickets, exactly 5 sold).

### 2. Reservations that expire

A reservation holds tickets for 10 minutes (`RESERVATION_HOLD_MINUTES`). If payment is not confirmed in time, the order becomes `expired` and its tickets return to the tier. Expiry is handled by **cleaning up expired orders before every new reservation** (`release_expired_reservations`), not by a background job.

I chose cleanup-on-reserve because it needs no scheduler or worker process, works on any hosting plan, and means an expired reservation can never block a buyer: it is released at the moment someone would be blocked by it. The event report also releases expired reservations first, so "remaining" counts are exact. Payment re-checks the expiry itself under the lock, so a late payment is refused and its seats are freed immediately.

**Proven by:** `test_expiry.py` (an expired hold is released for the next buyer, does not block the same attendee, and a late payment is refused and frees the seats).

### 3. Single-use, unguessable ticket codes

Codes are generated with Python's `secrets.token_urlsafe(16)` (128 random bits), never `random`, and the `code` column has a unique constraint. Check-in is one conditional statement:

```sql
UPDATE tickets SET status = 'used', checked_in_at = now()
WHERE code = :code AND status = 'valid' AND <ticket belongs to this event>
RETURNING id
```

If two gate staff scan the same ticket at the same instant, the database lets one statement change the row, and the other then finds the status is no longer `valid`, matches no row, and is rejected. There is no gap between the check and the change.

**Proven by:** `test_two_gate_staff_scanning_the_same_ticket_cannot_both_get_valid` (five scanners, one success), plus `test_checkin.py`.

## Business rules and decisions

- A free tier (price 0) skips payment: the order is created already paid, with its tickets.
- Tickets can be reserved only during the tier's sales window and before the event starts. An order cannot exceed the tier's max per order.
- Once a tier has sold a ticket, its price is frozen, and its quantity cannot drop below the tickets sold or currently held.
- An event cannot be published without a tier. Only published events are visible to the public.
- Refunds are allowed up to 48 hours before the event starts. A refund voids the order's tickets and returns the seats to the tier.
- Cancelling an event refunds every paid order and releases unpaid reservations, in a single transaction.
- Check-in is open only to the event's own organiser, only on the day of the event (a calendar day in Nigerian time, UTC+1), and only for published events. Refunded and used tickets never check in.
- Organisers can also reserve and buy tickets like attendees. A role is stored in the database and read on every request, so an approval takes effect immediately without logging in again.
- Suspending an event hides it and blocks new reservations and payments. Refunds are still allowed.

## Known limitations

- Payment is simulated (the pay endpoint always succeeds). No real payment provider is connected.
- Emails are not verified, so anyone can register with any unused address.
- Stretch goals (QR codes, Paystack or Flutterwave test payments, waitlist, emailed tickets) are not implemented.
- Pagination uses offset and limit, which is fine at this scale.
- The check-in "event day" uses a fixed UTC+1 offset.

## Deployment

Deployed on `<HOSTING_PLATFORM>` with a hosted PostgreSQL database. The start command is:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Tables are created by running `python -m alembic upgrade head` against the production database.