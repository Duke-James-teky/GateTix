import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.enums import OrderStatus, TicketStatus, UserRole
from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.checkin_service import check_in_ticket
from app.services.payment_service import pay_order
from app.services.reservation_service import reserve_tickets
from app.utils.ticket_codes import generate_ticket_code


def run_concurrently(tasks):
    """Run every task in its own thread and its own database session, all released at
    the same instant. Returns ("ok", value), ("error", message) or ("crash", detail)."""
    barrier = threading.Barrier(len(tasks))
    results = [None] * len(tasks)

    def runner(index, task):
        session = SessionLocal()
        try:
            barrier.wait()
            results[index] = ("ok", task(session))
        except AppError as error:
            results[index] = ("error", error.message)
        except Exception as error:  # a crash is a bug, and the test will show it
            results[index] = ("crash", repr(error))
        finally:
            session.close()

    threads = [threading.Thread(target=runner, args=(i, t)) for i, t in enumerate(tasks)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def reserve_task(tier_id, buyer_id):
    def task(session):
        buyer = session.get(User, buyer_id)
        return reserve_tickets(session, buyer, OrderCreate(tier_id=tier_id, quantity=1))

    return task


def kinds(results):
    return [kind for kind, _ in results]


def messages(results):
    return [value for kind, value in results if kind == "error"]


def test_two_buyers_racing_for_the_last_ticket_get_exactly_one(
    db, make_user, make_event, make_tier
):
    tier = make_tier(make_event(make_user(UserRole.ORGANISER)), quantity=1)
    buyers = [make_user(), make_user()]

    results = run_concurrently([reserve_task(tier.id, buyer.id) for buyer in buyers])

    assert "crash" not in kinds(results)
    assert kinds(results).count("ok") == 1
    assert messages(results) == ["Sold out"]
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (0, 1)


def test_many_buyers_racing_never_sell_more_than_exists(
    db, make_user, make_event, make_tier
):
    tier = make_tier(make_event(make_user(UserRole.ORGANISER)), quantity=5)
    buyers = [make_user() for _ in range(12)]

    results = run_concurrently([reserve_task(tier.id, buyer.id) for buyer in buyers])

    assert "crash" not in kinds(results)
    assert kinds(results).count("ok") == 5
    assert set(messages(results)) == {"Sold out"}
    db.refresh(tier)
    assert tier.sold + tier.reserved == 5
    pending = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.tier_id == tier.id, Order.status == OrderStatus.PENDING)
    )
    assert pending == 5


def test_paying_the_same_order_twice_at_once_issues_the_tickets_once(
    db, make_user, make_event, make_tier
):
    tier = make_tier(make_event(make_user(UserRole.ORGANISER)), quantity=10)
    buyer = make_user()
    order = reserve_tickets(db, buyer, OrderCreate(tier_id=tier.id, quantity=3))

    def pay(session):
        return pay_order(session, session.get(Order, order.id)).status

    results = run_concurrently([pay, pay])

    assert "crash" not in kinds(results)
    assert kinds(results).count("ok") == 1
    assert messages(results) == ["This order has already been paid"]
    ticket_count = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.order_id == order.id)
    )
    assert ticket_count == 3
    db.refresh(tier)
    assert (tier.sold, tier.reserved) == (3, 0)


def test_two_gate_staff_scanning_the_same_ticket_cannot_both_get_valid(
    db, make_user, make_event, make_tier
):
    organiser, attendee = make_user(UserRole.ORGANISER), make_user()
    now = datetime.now(timezone.utc)
    # The event is under way, so today's check-in window is open whatever the clock says.
    event = make_event(
        organiser, starts_at=now - timedelta(hours=1), ends_at=now + timedelta(hours=2)
    )
    tier = make_tier(event)
    order = Order(
        attendee_id=attendee.id,
        tier_id=tier.id,
        event_id=event.id,
        quantity=1,
        total_kobo=tier.price_kobo,
        status=OrderStatus.PAID,
    )
    db.add(order)
    db.flush()
    ticket = Ticket(order_id=order.id, code=generate_ticket_code())
    db.add(ticket)
    db.commit()

    def scan(session):
        return check_in_ticket(session, session.get(Event, event.id), ticket.code).status

    results = run_concurrently([scan] * 5)

    assert "crash" not in kinds(results)
    assert kinds(results).count("ok") == 1
    assert set(messages(results)) == {"This ticket has already been used"}
    db.refresh(ticket)
    assert ticket.status == TicketStatus.USED
    assert ticket.checked_in_at is not None